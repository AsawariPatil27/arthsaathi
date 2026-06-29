import json
import re
from datetime import datetime

from ai.config.llm import llm
from db import transactions


CATEGORIES = ["food", "travel", "bills", "shopping", "entertainment", "health", "income", "transfer", "other"]


def tracker_agent(user, message):
    data = extract_transaction(message)
    if not data.get("isTransaction"):
        return reply("This does not look like a transaction. Please send a bank SMS.")

    tid = str(user["telegramId"])
    ref = str(data.get("referenceNo") or "")

    if ref and transactions.find_one({"telegramId": tid, "referenceNo": ref}):
        return reply("This transaction is already recorded.")

    merchant = str(data.get("merchant") or "").strip()
    category = data.get("category") if data.get("category") in CATEGORIES else "other"

    txn = {
        "telegramId": tid,
        "amount": float(data.get("amount") or 0),
        "type": data.get("type", "debit"),
        "merchant": merchant,
        "category": category,
        "date": data.get("date") or datetime.utcnow().date().isoformat(),
        "referenceNo": ref,
        "createdAt": datetime.utcnow(),
    }
    transactions.insert_one(txn)
    return reply(f"Recorded Rs {txn['amount']:.2f} {txn['type']} for {merchant or category}.")


def extract_transaction(message):
    try:
        raw = llm([
            {"role": "system", "content": (
                "Extract transaction details from an Indian bank SMS or expense text. Return ONLY valid JSON.\n"
                "Fields: isTransaction, amount, type (debit/credit), merchant, category, date, referenceNo.\n"
                f"category must be one of: {', '.join(CATEGORIES)}.\n"
                "Rules: food=restaurants/delivery, bills=electricity/mobile/internet, travel=fuel/cabs/train, "
                "shopping=ecommerce/grocery, transfer=sending money to a person (not a merchant)."
            )},
            {"role": "user", "content": str(message)},
        ])
        m = re.search(r"\{.*?\}", raw, re.S)
        return json.loads(m.group(0) if m else "{}")
    except Exception as e:
        print(f"[TRACKER FAILED] {e}")
        return {"isTransaction": False}


def reply(text):
    return {"reply": text, "buttons": []}
