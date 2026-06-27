import json
import re

from ai.config.llm import llm
from goals import add_goal_progress, create_goal, user_goals
from users import save_user


GOALS = {
    "lean_season_reserve": "Lean Season Reserve",
    "emergency_fund": "Emergency Fund",
    "healthcare_fund": "Healthcare Fund",
    "education_fund": "Education Fund",
    "other": "Other Goal",
}

BUTTON_LABELS = {
    "hi": {
        "lean_season_reserve": "लीन सीजन आरक्षित",
        "emergency_fund": "आपातकालीन निधि",
        "healthcare_fund": "स्वास्थ्य निधि",
        "education_fund": "शिक्षा निधि",
        "other": "अन्य लक्ष्य",
    },
    "mr": {
        "lean_season_reserve": "लीन सीझन राखीव",
        "emergency_fund": "आपत्कालीन निधी",
        "healthcare_fund": "आरोग्य निधी",
        "education_fund": "शिक्षण निधी",
        "other": "इतर लक्ष्य",
    },
}

TEXT = {
    "en": {
        "intro": "Based on your profile, these saving goals may fit you:",
        "choose": "Choose the goals you want to create.",
        "active": "Your active saving goals:",
        "also": "You can also create these:",
        "progress": "To add progress, type: I saved 500 for emergency fund.",
        "created": "Created",
        "monthly": "Monthly target is",
        "other": "Tell me your goal name and target amount. Example: Buy cow, 50000",
        "again": "Please ask me to create your savings plan again.",
        "not_found": "I could not find that goal. Ask me to create your savings plan first.",
        "saved": "Saved",
        "remaining": "Remaining target is",
    },
    "hi": {
        "intro": "आपकी प्रोफाइल के अनुसार ये बचत लक्ष्य उपयोगी हो सकते हैं:",
        "choose": "जो लक्ष्य बनाना है, उसे चुनें।",
        "active": "आपके सक्रिय बचत लक्ष्य:",
        "also": "आप ये लक्ष्य भी बना सकते हैं:",
        "progress": "प्रगति जोड़ने के लिए लिखें: मैंने आपातकालीन निधि के लिए 500 बचाए।",
        "created": "बना दिया",
        "monthly": "मासिक लक्ष्य है",
        "other": "लक्ष्य का नाम और राशि बताएं। उदाहरण: गाय खरीदना, 50000",
        "again": "कृपया बचत योजना फिर से बनाने के लिए कहें।",
        "not_found": "यह लक्ष्य नहीं मिला। पहले बचत योजना बनवाएं।",
        "saved": "बचाए गए",
        "remaining": "बाकी लक्ष्य है",
    },
    "mr": {
        "intro": "तुमच्या प्रोफाइलनुसार ही बचत लक्ष्ये उपयोगी ठरू शकतात:",
        "choose": "जे लक्ष्य तयार करायचे आहे ते निवडा.",
        "active": "तुमची सक्रिय बचत लक्ष्ये:",
        "also": "तुम्ही ही लक्ष्येही तयार करू शकता:",
        "progress": "प्रगती जोडण्यासाठी लिहा: मी आपत्कालीन निधीसाठी 500 वाचवले.",
        "created": "तयार केले",
        "monthly": "मासिक लक्ष्य आहे",
        "other": "लक्ष्याचे नाव आणि रक्कम सांगा. उदाहरण: गाय खरेदी, 50000",
        "again": "कृपया बचत योजना पुन्हा तयार करायला सांगा.",
        "not_found": "हे लक्ष्य सापडले नाही. आधी बचत योजना तयार करा.",
        "saved": "वाचवले",
        "remaining": "उरलेले लक्ष्य आहे",
    },
}


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

def planner_agent(user, message):
    text = str(message or "").strip()

    if text.startswith("choose_goal:"):
        return choose_goal(user, text.split(":", 1)[1])
    if user.get("pendingAction") == "other_goal_details":
        return create_other_goal(user, text)

    saved = extract_saving(text)
    if saved:
        return save_progress(user, saved)

    active = user_goals(user)
    return show_existing(user, active) if active else start_plan(user)


def start_plan(user):
    goals = suggested_goals(user)
    user["pendingGoals"] = goals
    save_user(user)

    lines = [copy(user, "intro")]
    lines += [f"{i}. {label(user, g)} - target Rs {g['targetAmount']}, monthly Rs {g['monthlySaving']}" for i, g in enumerate(goals, 1)]
    lines.append(copy(user, "choose"))
    return reply("\n".join(lines), goal_buttons(user, goals))


def show_existing(user, active):
    created = {goal["type"] for goal in active}
    remaining = [goal for goal in suggested_goals(user) if goal["type"] not in created]
    user["pendingGoals"] = remaining
    save_user(user)

    lines = [copy(user, "active")]
    lines += [f"{label(user, g)}: Rs {g['currentAmount']} / Rs {g['targetAmount']} monthly Rs {g['monthlySaving']}" for g in active]
    if remaining:
        lines.append("\n" + copy(user, "also"))
        return reply("\n".join(lines), goal_buttons(user, remaining))
    lines.append("\n" + copy(user, "progress"))
    return reply("\n".join(lines))


def choose_goal(user, goal_type):
    if goal_type == "other":
        user["pendingAction"] = "other_goal_details"
        save_user(user)
        return reply(copy(user, "other"))

    goal = next((g for g in user.get("pendingGoals", []) if g["type"] == goal_type), None)
    if not goal:
        return reply(copy(user, "again"))

    create_goal(user, goal)
    return reply(f"{copy(user, 'created')} {label(user, goal)}. {copy(user, 'monthly')} Rs {goal['monthlySaving']}.")


# ---------------------------------------------------------------------------
# LLM-based goal suggestion
# ---------------------------------------------------------------------------

def suggested_goals(user):
    profile = {
        "occupation": user.get("occupation"),
        "incomeType": user.get("incomeType"),
        "monthlyIncome": money(user.get("monthlyIncome")),
        "lowestMonthIncome": money(user.get("lowestMonthIncome")),
        "monthlyExpense": money(user.get("monthlyExpense")),
        "harvestIncome": money(user.get("harvestIncome")),
        "leanDurationMonths": money(user.get("leanDurationMonths")),
        "leanMonthlyExpense": money(user.get("leanMonthlyExpense")),
        "familySize": money(user.get("familySize")),
        "hasInsurance": user.get("hasInsurance", False),
    }

    system_prompt = (
        "You are a financial planner for rural/semi-urban Indian users.\n"
        "Given the user profile below, generate savings goals as a JSON array.\n\n"
        "Rules:\n"
        "1. Calculate monthly savings capacity first:\n"
        "   - Farmer: capacity = (harvestIncome/12) - leanMonthlyExpense. If <=0, use (harvestIncome/12)*0.15\n"
        "   - Fixed income: capacity = monthlyIncome - monthlyExpense. If <=0, use monthlyIncome*0.15\n"
        "   - Variable non-farmer: capacity = ((monthlyIncome+lowestMonthIncome)/2) - monthlyExpense. If <=0, use monthlyIncome*0.15\n\n"
        "2. Generate these goals (skip lean_season_reserve for non-farmers):\n"
        "   - lean_season_reserve (farmers only): target = leanMonthlyExpense * leanDurationMonths, timeframe=6\n"
        "   - emergency_fund: target = leanMonthlyExpense*3 (farmer) or monthlyExpense*3, timeframe=6\n"
        "   - healthcare_fund: target = expense*2 (insured) or expense*3 (not insured), timeframe=12\n"
        "   - education_fund: target = expense*2, timeframe=12\n"
        "   - other: target=0, monthlySaving=0\n\n"
        "3. Allocate capacity by priority order (1 to 5):\n"
        "   monthlySaving = min(remaining_capacity, target/timeframe)\n"
        "   Subtract from remaining_capacity. Lower-priority goals get 0 if capacity runs out.\n\n"
        "4. Return ONLY a valid JSON array. No text or markdown. Format:\n"
        '[{"type":"lean_season_reserve","name":"Lean Season Reserve","targetAmount":100000,"currentAmount":0,"monthlySaving":5000,"priority":1,"status":"active"}]'
    )

    try:
        raw = llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(profile)}
        ])
        match = re.search(r"\[\s*\{.*\}\s*\]", raw, re.S)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"[LLM SUGGESTED GOALS FAILED] {e}")

    # Formula-based fallback if LLM fails
    return _fallback_suggested_goals(user)


# ---------------------------------------------------------------------------
# LLM-based custom goal creation
# ---------------------------------------------------------------------------

def create_other_goal(user, message):
    system_prompt = (
        "The user wants to create a savings goal. Extract the goal name and target amount from their message.\n"
        "Calculate monthlySaving = targetAmount / 12.\n"
        "Return ONLY a valid JSON object. No text or markdown. Format:\n"
        '{"name":"Buy cow","targetAmount":50000,"monthlySaving":4167}'
    )

    try:
        raw = llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ])
        match = re.search(r"\{[^{}]*\}", raw, re.S)
        if match:
            data = json.loads(match.group(0))
            name = data.get("name") or "Other Goal"
            target = float(data.get("targetAmount") or 0)
            monthly = float(data.get("monthlySaving") or round(target / 12))

            if not target:
                return reply(copy(user, "other"))

            goal = {
                "type": "other",
                "name": name,
                "targetAmount": round(target),
                "currentAmount": 0,
                "monthlySaving": round(monthly),
                "priority": 5,
                "status": "active",
            }
            create_goal(user, goal)
            user["pendingAction"] = ""
            save_user(user)
            return reply(f"{copy(user, 'created')} {goal['name']}. {copy(user, 'monthly')} Rs {goal['monthlySaving']}.")
    except Exception as e:
        print(f"[LLM CREATE OTHER GOAL FAILED] {e}")

    return reply(copy(user, "other"))


# ---------------------------------------------------------------------------
# Save progress
# ---------------------------------------------------------------------------

def save_progress(user, saved):
    goal = add_goal_progress(user, saved["goalType"], saved["amount"])
    if not goal:
        return reply(copy(user, "not_found"))

    remaining = max(0, goal["targetAmount"] - goal["currentAmount"])
    return reply(f"{copy(user, 'saved')} Rs {saved['amount']} for {GOALS.get(goal['type'], goal['name'])}. {copy(user, 'remaining')} Rs {remaining}.")


def extract_saving(message):
    data = json_from_llm(
        "If user saved money for a goal, return JSON only: "
        "{\"amount\":0,\"goalType\":\"emergency_fund|lean_season_reserve|healthcare_fund|education_fund|other\"}. "
        "If not a saving update, return {}.",
        message,
    )
    return data if data.get("amount") and data.get("goalType") else {}


# ---------------------------------------------------------------------------
# Formula-based fallback (used only if LLM fails)
# ---------------------------------------------------------------------------

def _fallback_suggested_goals(user):
    expense = money(user.get("monthlyExpense")) or money(user.get("leanMonthlyExpense"))
    goals = []

    if user.get("occupation") == "farmer":
        target = money(user.get("leanMonthlyExpense")) * money(user.get("leanDurationMonths"))
        goals.append(_make_goal("lean_season_reserve", GOALS["lean_season_reserve"], target, 1))

    goals += [
        _make_goal("emergency_fund", GOALS["emergency_fund"], expense * 3, 2),
        _make_goal("healthcare_fund", GOALS["healthcare_fund"], expense * (2 if user.get("hasInsurance") else 3), 3),
        _make_goal("education_fund", GOALS["education_fund"], expense * 2, 4),
        _make_goal("other", GOALS["other"], 0, 5),
    ]

    # Allocate capacity by priority
    harvest_inc = money(user.get("harvestIncome"))
    monthly_income = money(user.get("monthlyIncome"))
    monthly_expense = money(user.get("leanMonthlyExpense") if user.get("occupation") == "farmer" else user.get("monthlyExpense"))
    monthly_equiv = harvest_inc / 12 if harvest_inc else monthly_income
    capacity = max(0, monthly_equiv - monthly_expense) or max(0, monthly_equiv * 0.15)

    remaining = capacity
    for goal in sorted(goals, key=lambda g: g["priority"]):
        if goal["targetAmount"] > 0:
            timeframe = 6 if goal["type"] in ["lean_season_reserve", "emergency_fund"] else 12
            ideal = round(goal["targetAmount"] / timeframe)
            goal["monthlySaving"] = min(remaining, ideal)
            remaining = max(0, remaining - goal["monthlySaving"])
        else:
            goal["monthlySaving"] = 0
    return goals


def _make_goal(goal_type, name, target, priority):
    timeframe = 6 if goal_type in ["lean_season_reserve", "emergency_fund"] else 12
    return {
        "type": goal_type,
        "name": name,
        "targetAmount": round(target),
        "currentAmount": 0,
        "monthlySaving": round(target / timeframe) if target else 0,
        "priority": priority,
        "status": "active",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def json_from_llm(system, message):
    try:
        raw = llm([{"role": "system", "content": system}, {"role": "user", "content": str(message)}])
        match = re.search(r"\{[^{}]*\}", raw, re.S)
        return json.loads(match.group(0) if match else "{}")
    except Exception:
        return {}


def goal_buttons(user, goals):
    return [[{"text": label(user, goal), "data": f"choose_goal:{goal['type']}"}] for goal in goals]


def label(user, goal):
    return BUTTON_LABELS.get(user.get("language"), {}).get(goal["type"], goal["name"])


def copy(user, key):
    return TEXT.get(user.get("language"), TEXT["en"])[key]


def money(value):
    number = re.sub(r"[^0-9.]", "", str(value or "0"))
    return float(number or 0)


def reply(text, buttons=None):
    return {"reply": text, "buttons": buttons or [], "skipTranslation": True}
