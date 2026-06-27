import json
import re
from datetime import datetime

from ai.config.llm import llm
from db import glossary


COMMON_TERMS = {
    "sip": "SIP means investing a fixed amount regularly, usually every month, into a mutual fund.",
    "nav": "NAV is the price of one unit of a mutual fund.",
    "credit score": "A credit score is a number that shows how safely you have handled loans or credit.",
    "interest": "Interest is extra money paid for borrowing money, or earned for saving/investing money.",
    "emi": "EMI is the fixed monthly amount you pay to repay a loan.",
    "deductible": "A deductible is the amount you pay yourself before insurance starts paying.",
}


def jargon_reply(user, message):
    term = extract_term(message)
    if not term:
        return {"reply": "Tell me the financial word you want explained. Example: What is SIP?", "buttons": []}

    saved = glossary.find_one({"term": term.lower()})
    if saved:
        return {"reply": format_reply(saved["term"], saved["meaning"], saved.get("example", "")), "buttons": []}

    meaning = COMMON_TERMS.get(term.lower()) or explain_with_llm(term, message)
    glossary.update_one(
        {"term": term.lower()},
        {"$set": {"term": term.lower(), "meaning": meaning, "example": "", "updatedAt": datetime.utcnow()}},
        upsert=True,
    )
    return {"reply": format_reply(term, meaning), "buttons": []}


def extract_term(message):
    text = str(message or "").strip()
    lower = text.lower()

    for term in COMMON_TERMS:
        if term in lower:
            return term

    match = re.search(r"(?:what is|explain|meaning of|matlab of|kya hota hai)\s+([a-zA-Z ]+)", lower)
    if match:
        return match.group(1).strip(" ?.")

    try:
        raw = llm([
            {"role": "system", "content": "Extract the financial jargon term from the message. Return JSON only: {\"term\":\"\"}."},
            {"role": "user", "content": text},
        ])
        data = json.loads(re.search(r"\{[^{}]*\}", raw, re.S).group(0))
        return str(data.get("term", "")).strip().lower()
    except Exception:
        return ""


def explain_with_llm(term, message):
    try:
        return llm([
            {
                "role": "system",
                "content": (
                    "Explain this financial term for a rural Indian user. "
                    "Use 2 short sentences. No jargon. No markdown. Do not give investment advice."
                ),
            },
            {"role": "user", "content": f"Term: {term}\nUser question: {message}"},
        ]).strip()
    except Exception:
        return "This is a financial term. Please ask again in simpler words and I will explain it."


def format_reply(term, meaning, example=""):
    reply = f"{term.upper()}: {meaning}"
    return reply + (f"\nExample: {example}" if example else "")
