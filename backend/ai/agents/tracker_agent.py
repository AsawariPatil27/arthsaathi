import hashlib
import json
import re
from datetime import datetime

from ai.config.llm import llm
from db import merchant_categories, transactions


CATEGORIES = ["food", "travel", "bills", "shopping", "entertainment", "health", "income", "transfer", "other"]


def tracker_agent(user, message):
    data = extract_transaction(message)
    if not data.get("isTransaction"):
        return reply("This does not look like a completed transaction. Please send a debit or credit SMS.")

    merchant = clean(data.get("merchant"))
    date = data.get("date") or datetime.utcnow().date().isoformat()
    ref_hash, content_hash = make_hashes(data, merchant, date)

    # Duplicate check: prefer reference hash, fall back to content fingerprint
    tid = str(user["telegramId"])
    if ref_hash and transactions.find_one({"telegramId": tid, "refHash": ref_hash}):
        return reply("This transaction is already recorded.")
    if not ref_hash and transactions.find_one({"telegramId": tid, "contentHash": content_hash}):
        return reply("This transaction is already recorded.")

    transaction = clean_transaction(user, data, merchant, ref_hash, content_hash, date)
    transactions.insert_one(transaction)

    if merchant:
        merchant_categories.update_one(
            {"merchant": merchant.lower()},
            {"$setOnInsert": {"merchant": merchant.lower(), "category": transaction["category"]}},
            upsert=True,
        )

    return reply(f"Recorded Rs {transaction['amount']:.2f} {transaction['type']} for {merchant or transaction['category']}.")


def clean_transaction(user, data, merchant, ref_hash, content_hash, date):
    saved_category = merchant_categories.find_one({"merchant": merchant.lower()}) if merchant else None
    return {
        "telegramId": str(user["telegramId"]),
        "amount": money(data.get("amount")),
        "type": data.get("type", "debit"),
        "merchant": merchant,
        "category": clean_category((saved_category or {}).get("category") or data.get("category")),
        "accountLast4": str(data.get("accountLast4") or ""),
        "date": date,
        "source": data.get("source", "sms"),
        "bank": data.get("bank", ""),
        "refHash": ref_hash,
        "contentHash": content_hash,
        "createdAt": datetime.utcnow(),
    }


def extract_transaction(message):
    fallback = {"isTransaction": False}
    try:
        text = llm([
            {
                "role": "system",
                "content": (
                    "Extract transaction fields from Indian bank SMS or manual expense text. "
                    "Return only valid JSON. No markdown. "
                    "Fields: isTransaction, amount, type, merchant, category, "
                    "accountLast4, date, source, bank, referenceNo. "
                    "type must be debit or credit. source must be sms, manual, or voice. "
                    f"category must be one of: {', '.join(CATEGORIES)}. "
                    "If reference number exists, put it in referenceNo.\n"
                    "Categorisation Rules:\n"
                    "- food: Restaurants, food delivery, bakeries (e.g., Swiggy, Zomato, Dominos, Dominospizza, KFC).\n"
                    "- bills: Electricity, mobile recharge, internet, water, DTH.\n"
                    "- travel: Fuel, cabs, train, bus (e.g., Uber, Ola).\n"
                    "- shopping: E-commerce, clothing, grocery store (e.g., Amazon, Flipkart).\n"
                    "- transfer: Sending money to friends/family directly. Do not categorise merchant payments as transfer.\n"
                    "Examples:\n"
                    "1. 'debited by 130.00 ... trf to SWIGGY' -> {\"isTransaction\":true, \"amount\":130.0, \"type\":\"debit\", \"merchant\":\"Swiggy\", \"category\":\"food\"}\n"
                    "2. 'debited by 352.80 ... trf to DOMINOSPIZZA' -> {\"isTransaction\":true, \"amount\":352.8, \"type\":\"debit\", \"merchant\":\"Dominos Pizza\", \"category\":\"food\"}"
                ),
            },
            {"role": "user", "content": str(message)},
        ])
        return json.loads(extract_json(text))
    except Exception as error:
        print(f"[TRACKER EXTRACT FAILED] {error}")
        return fallback


def make_hashes(data, merchant, date):
    """Return (ref_hash, content_hash). ref_hash is empty string if no referenceNo."""
    ref_hash = ""
    if data.get("referenceNo"):
        ref_hash = hashlib.sha256(str(data["referenceNo"]).encode()).hexdigest()

    # Content fingerprint: amount + type + date + merchant (lowercased)
    fingerprint = f"{money(data.get('amount'))}|{data.get('type', '')}|{date}|{(merchant or '').lower()}"
    content_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
    return ref_hash, content_hash


def clean(value):
    return str(value or "").strip()


def money(value):
    number = re.sub(r"[^0-9.]", "", str(value or "0"))
    return float(number or 0)


def clean_category(value):
    category = clean(value).lower().replace(" ", "_")
    return category if category in CATEGORIES else "other"


def extract_json(text):
    match = re.search(r"\{.*?\}", str(text), re.S)
    return match.group(0) if match else "{}"


def reply(text):
    return {"reply": text, "buttons": []}
