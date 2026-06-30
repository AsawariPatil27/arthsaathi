import json
import re

from ai.config.llm import llm
from users import save_user


FIELDS = [
    "interactionMode", "language", "incomeType", "occupation",
    "monthlyIncome", "lowestMonthIncome", "monthlyExpense",
    "state", "district", "harvestIncome",
    "leanDurationMonths", "leanMonthlyExpense",
]


_LANG_CODES = {
    "hindi": "hi", "marathi": "mr", "tamil": "ta", "telugu": "te",
    "kannada": "kn", "bengali": "bn", "gujarati": "gu", "punjabi": "pa",
    "english": "en",
}


def update_profile_from_message(user, message):
    changes = _extract(message)
    if not changes:
        return {"reply": "Tell me what profile detail you want to change.", "buttons": []}
    for field, value in changes.items():
        if field not in FIELDS:
            continue
        if field == "language" and isinstance(value, str):
            value = _LANG_CODES.get(value.lower().strip(), value)
        user[field] = value
    save_user(user)
    return {"reply": "Profile updated.", "buttons": []}


def _extract(message):
    try:
        raw = llm([
            {
                "role": "system",
                "content": (
                    "Extract profile field updates from the user message. "
                    "Return only valid JSON. No markdown. "
                    f"Allowed fields: {', '.join(FIELDS)}. "
                    "Use numbers for money/counts and true/false for yes/no. "
                    "If nothing to update, return {}."
                ),
            },
            {"role": "user", "content": str(message)},
        ])
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0) if m else "{}")
    except Exception as e:
        print(f"[PROFILE UPDATE FAILED] {e}")
        return {}
