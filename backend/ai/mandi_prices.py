import json
import os
import re

import requests
from requests.exceptions import RequestException

from ai.config.llm import llm
from users import save_user


def mandi_price_reply(user, message):
    commodity = extract_commodity(message) or extract_commodity(user.get("originalMessage"))
    if not commodity:
        user["pendingAction"] = "mandi_price"
        save_user(user)
        return {"reply": "Which crop or commodity price do you want?", "buttons": []}

    user["pendingAction"] = ""
    save_user(user)
    try:
        records = fetch_prices(user, commodity)
    except RequestException as error:
        print(f"[MANDI API FAILED] {error}")
        return {"reply": "The mandi price service is slow right now. Please try again in a minute.", "buttons": []}

    if not records:
        return {"reply": f"I could not find {commodity} prices for your district right now.", "buttons": []}

    return {"reply": explain_prices(user, commodity, records), "buttons": []}


def extract_commodity(message):
    if not message:
        return ""
    try:
        raw = llm([
            {
                "role": "system",
                "content": (
                    "Extract the crop/commodity name for an Indian mandi price lookup. "
                    "Return only valid JSON: {\"commodity\":\"Onion\"}. No markdown. "
                    "Commodity must be a single English crop name in title case (not a phrase). "
                    "Strip noise words: market, mandi, price, rate, bhaav, today, in, the, at, is. "
                    "Examples: 'Onions in market' → {\"commodity\":\"Onion\"}; "
                    "'kaande ka bhaav' → {\"commodity\":\"Onion\"}; "
                    "'lal mirchi rate' → {\"commodity\":\"Red Chilli\"}. "
                    "If no crop/vegetable/grain/pulse exists, return {\"commodity\":\"\"}."
                ),
            },
            {"role": "user", "content": str(message)},
        ])
        commodity = json.loads(_json(raw)).get("commodity", "")
        return _normalise(commodity) or _fallback(message)
    except Exception as e:
        print(f"[MANDI COMMODITY FAILED] {e}")
        return _fallback(message)


def _normalise(value):
    stop = {"at", "in", "on", "for", "the", "market", "mandi", "price", "rate", "bhaav", "bhav", "is", "are", "today"}
    words = [w for w in re.findall(r"[A-Za-z]+", str(value or "")) if w.lower() not in stop]
    commodity = " ".join(words).strip().title()
    return {"Onions": "Onion", "Tomatoes": "Tomato", "Potatoes": "Potato", "Chillies": "Chilli"}.get(commodity, commodity)


def _fallback(message):
    text = str(message or "").lower()
    known = {
        ("kaanda", "kanda", "kaande", "kande", "pyaz", "pyaaz", "onion", "onions"): "Onion",
        ("tamatar", "tomato", "tomatoes"): "Tomato",
    }
    for words, commodity in known.items():
        if any(w in text for w in words):
            return commodity
    return ""


def fetch_prices(user, commodity):
    r = requests.get(
        os.getenv("DATA_GOV_MANDI_URL"),
        params={
            "api-key": os.getenv("DATA_GOV_API_KEY"),
            "format": "json",
            "limit": 5,
            "filters[state.keyword]": _title(user.get("state")),
            "filters[district]": _title(user.get("district")),
            "filters[commodity]": _title(commodity),
        },
        headers={"accept": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("records", [])


def explain_prices(user, commodity, records):
    try:
        return llm([
            {
                "role": "system",
                "content": (
                    "You are ArthSaathi. Summarise mandi price data simply for a rural Indian farmer. "
                    "Mention market name, min, max and modal price. Keep it short. No markdown or asterisks. "
                    "End with: These prices are subject to change."
                ),
            },
            {"role": "user", "content": f"Commodity: {commodity}\nState: {user.get('state')}\nDistrict: {user.get('district')}\nRecords: {records}"},
        ]).strip()
    except Exception as e:
        print(f"[MANDI EXPLAIN FAILED] {e}")
        return f"Latest {commodity} mandi records: {records[:3]}"


def _title(value):
    return str(value or "").strip().title()


def _json(text):
    m = re.search(r"\{.*\}", str(text), re.S)
    return m.group(0) if m else "{}"
