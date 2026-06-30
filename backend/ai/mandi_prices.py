import json
import os
import re

import requests
from requests.exceptions import RequestException

from ai.config.llm import llm


def mandi_price_reply(user, message):
    commodity = _commodity(message) or _commodity(user.get("originalMessage"))
    if not commodity:
        return {"reply": "Which crop or commodity price do you want?", "buttons": []}

    try:
        records = _fetch(user, commodity)
    except RequestException as error:
        print(f"[MANDI API FAILED] {error}")
        return {"reply": "The mandi price service is slow right now. Please try again in a minute.", "buttons": []}

    if not records:
        return {"reply": f"I could not find {commodity} prices for your district right now.", "buttons": []}

    return {"reply": _explain(user, commodity, records), "buttons": []}


def _commodity(message):
    if not message:
        return ""
    try:
        raw = llm([
            {"role": "system", "content": (
                "Extract the crop or commodity name for an Indian mandi price lookup. "
                "Return ONLY valid JSON: {\"commodity\": \"English name in title case\"}. "
                "Single crop name, title case. No extra words. "
                "Convert regional names: kaanda/kanda/pyaz/pyaaz → Onion, tamatar → Tomato, "
                "gehu/gehun → Wheat, chawal → Rice, aalu/batata → Potato, "
                "lal mirchi → Red Chilli, lahsun → Garlic, adrak → Ginger. "
                "If no crop found, return {\"commodity\": \"\"}."
            )},
            {"role": "user", "content": str(message)},
        ])
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0) if m else "{}").get("commodity", "").strip()
    except Exception as e:
        print(f"[MANDI COMMODITY FAILED] {e}")
        return ""


def _fetch(user, commodity):
    r = requests.get(
        os.getenv("DATA_GOV_MANDI_URL"),
        params={
            "api-key": os.getenv("DATA_GOV_API_KEY"),
            "format": "json",
            "limit": 5,
            "filters[state.keyword]": _t(user.get("state")),
            "filters[district]": _t(user.get("district")),
            "filters[commodity]": _t(commodity),
        },
        headers={"accept": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("records", [])


def _explain(user, commodity, records):
    try:
        return llm([
            {"role": "system", "content": (
                "You are ArthSaathi. Summarise mandi price data simply for a rural Indian farmer. "
                "Mention market name, min, max and modal price. Keep it short. No markdown or asterisks. "
                "End with: These prices are subject to change."
            )},
            {"role": "user", "content": f"Commodity: {commodity}\nState: {user.get('state')}\nDistrict: {user.get('district')}\nRecords: {records}"},
        ]).strip()
    except Exception as e:
        print(f"[MANDI EXPLAIN FAILED] {e}")
        return f"Latest {commodity} mandi records: {records[:3]}"


def _t(value):
    return str(value or "").strip().title()
