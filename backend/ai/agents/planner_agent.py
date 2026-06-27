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
        "error": "Something went wrong. Please try again.",
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
        "error": "कुछ गलत हुआ। कृपया फिर से प्रयास करें।",
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
        "error": "काहीतरी चुकले. कृपया पुन्हा प्रयत्न करा.",
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
    if not goals:
        return reply(copy(user, "error"))

    user["pendingGoals"] = goals
    save_user(user)

    lines = [copy(user, "intro")]
    lines += [
        f"{i}. {label(user, g)} - target Rs {g['targetAmount']}, monthly Rs {g['monthlySaving']}"
        for i, g in enumerate(goals, 1)
    ]
    lines.append(copy(user, "choose"))
    return reply("\n".join(lines), goal_buttons(user, goals))


def show_existing(user, active):
    created = {goal["type"] for goal in active}
    remaining = [goal for goal in suggested_goals(user) if goal["type"] not in created]
    user["pendingGoals"] = remaining
    save_user(user)

    lines = [copy(user, "active")]
    lines += [
        f"{label(user, g)}: Rs {g['currentAmount']} / Rs {g['targetAmount']} monthly Rs {g['monthlySaving']}"
        for g in active
    ]
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
# LLM goal suggestion — 3 distinct prompts by income type / occupation
# ---------------------------------------------------------------------------

def suggested_goals(user):
    income_type = (user.get("incomeType") or "").lower().strip()
    occupation  = (user.get("occupation")  or "").lower().strip()

    # ── Branch 1: Farmer (seasonal/harvest income) ────────────────────────
    if occupation == "farmer":
        profile = {
            "harvestIncome":      money(user.get("harvestIncome")),
            "leanMonthlyExpense": money(user.get("leanMonthlyExpense")),
            "leanDurationMonths": money(user.get("leanDurationMonths")),
            "hasInsurance":       bool(user.get("hasInsurance", False)),
            "familySize":         money(user.get("familySize")),
        }
        system_prompt = (
            "You are a financial planner for rural Indian farmers with seasonal harvest income.\n\n"
            "USER PROFILE FIELDS:\n"
            "  harvestIncome       - total annual income from harvest (Rs)\n"
            "  leanMonthlyExpense  - monthly expense during lean/off-season months (Rs)\n"
            "  leanDurationMonths  - number of lean months per year\n"
            "  hasInsurance        - true/false, whether user has health insurance\n"
            "  familySize          - number of family members\n\n"
            "STEP 1 - Calculate monthly savings capacity:\n"
            "  monthly_equiv = harvestIncome / 12\n"
            "  capacity = monthly_equiv - leanMonthlyExpense\n"
            "  If capacity <= 0: capacity = monthly_equiv * 0.15\n\n"
            "STEP 2 - Generate goals in this priority order:\n"
            "  1. lean_season_reserve  target = leanMonthlyExpense x leanDurationMonths, timeframe = 6 months\n"
            "  2. emergency_fund       target = leanMonthlyExpense x 3,                  timeframe = 6 months\n"
            "  3. healthcare_fund      target = leanMonthlyExpense x 2 (insured) or x 3, timeframe = 12 months\n"
            "  4. education_fund       target = leanMonthlyExpense x 2,                  timeframe = 12 months\n"
            "  5. other               targetAmount = 0, monthlySaving = 0\n\n"
            "STEP 3 - Allocate capacity greedily by priority:\n"
            "  For each goal (priority 1 to 5):\n"
            "    monthlySaving = min(remaining_capacity, target / timeframe)\n"
            "    remaining_capacity -= monthlySaving\n"
            "  Goals with 0 remaining capacity get monthlySaving = 0.\n\n"
            "OUTPUT: Return ONLY a valid JSON array. No markdown, no explanation, no extra text.\n"
            "Each element must have exactly these keys:\n"
            "  type, name, targetAmount, currentAmount (always 0), monthlySaving, priority, status (always active)\n\n"
            "Valid type values: lean_season_reserve, emergency_fund, healthcare_fund, education_fund, other"
        )

    # ── Branch 2: Variable income, non-farmer ─────────────────────────────
    elif income_type == "variable":
        profile = {
            "monthlyIncome":     money(user.get("monthlyIncome")),
            "lowestMonthIncome": money(user.get("lowestMonthIncome")),
            "monthlyExpense":    money(user.get("monthlyExpense")),
            "hasInsurance":      bool(user.get("hasInsurance", False)),
            "familySize":        money(user.get("familySize")),
        }
        system_prompt = (
            "You are a financial planner for rural/semi-urban Indian users with variable (irregular) income.\n\n"
            "USER PROFILE FIELDS:\n"
            "  monthlyIncome      - average monthly income (Rs)\n"
            "  lowestMonthIncome  - income in the worst/lowest month (Rs)\n"
            "  monthlyExpense     - average monthly household expense (Rs)\n"
            "  hasInsurance       - true/false, whether user has health insurance\n"
            "  familySize         - number of family members\n\n"
            "STEP 1 - Calculate monthly savings capacity:\n"
            "  average_income = (monthlyIncome + lowestMonthIncome) / 2\n"
            "  capacity = average_income - monthlyExpense\n"
            "  If capacity <= 0: capacity = monthlyIncome * 0.15\n\n"
            "STEP 2 - Generate goals in this priority order (NO lean_season_reserve for non-farmers):\n"
            "  1. emergency_fund   target = monthlyExpense x 3,               timeframe = 6 months\n"
            "  2. healthcare_fund  target = monthlyExpense x 2 (insured) or x 3, timeframe = 12 months\n"
            "  3. education_fund   target = monthlyExpense x 2,               timeframe = 12 months\n"
            "  4. other           targetAmount = 0, monthlySaving = 0\n\n"
            "STEP 3 - Allocate capacity greedily by priority:\n"
            "  For each goal (priority 1 to 4):\n"
            "    monthlySaving = min(remaining_capacity, target / timeframe)\n"
            "    remaining_capacity -= monthlySaving\n"
            "  Goals with 0 remaining capacity get monthlySaving = 0.\n\n"
            "OUTPUT: Return ONLY a valid JSON array. No markdown, no explanation, no extra text.\n"
            "Each element must have exactly these keys:\n"
            "  type, name, targetAmount, currentAmount (always 0), monthlySaving, priority, status (always active)\n\n"
            "Valid type values: emergency_fund, healthcare_fund, education_fund, other"
        )

    # ── Branch 3: Fixed / salaried income ─────────────────────────────────
    else:
        profile = {
            "monthlyIncome":  money(user.get("monthlyIncome")),
            "monthlyExpense": money(user.get("monthlyExpense")),
            "hasInsurance":   bool(user.get("hasInsurance", False)),
            "familySize":     money(user.get("familySize")),
        }
        system_prompt = (
            "You are a financial planner for rural/semi-urban Indian users with fixed (salaried) monthly income.\n\n"
            "USER PROFILE FIELDS:\n"
            "  monthlyIncome   - fixed monthly income (Rs)\n"
            "  monthlyExpense  - average monthly household expense (Rs)\n"
            "  hasInsurance    - true/false, whether user has health insurance\n"
            "  familySize      - number of family members\n\n"
            "STEP 1 - Calculate monthly savings capacity:\n"
            "  capacity = monthlyIncome - monthlyExpense\n"
            "  If capacity <= 0: capacity = monthlyIncome * 0.15\n\n"
            "STEP 2 - Generate goals in this priority order (NO lean_season_reserve for salaried users):\n"
            "  1. emergency_fund   target = monthlyExpense x 3,               timeframe = 6 months\n"
            "  2. healthcare_fund  target = monthlyExpense x 2 (insured) or x 3, timeframe = 12 months\n"
            "  3. education_fund   target = monthlyExpense x 2,               timeframe = 12 months\n"
            "  4. other           targetAmount = 0, monthlySaving = 0\n\n"
            "STEP 3 - Allocate capacity greedily by priority:\n"
            "  For each goal (priority 1 to 4):\n"
            "    monthlySaving = min(remaining_capacity, target / timeframe)\n"
            "    remaining_capacity -= monthlySaving\n"
            "  Goals with 0 remaining capacity get monthlySaving = 0.\n\n"
            "OUTPUT: Return ONLY a valid JSON array. No markdown, no explanation, no extra text.\n"
            "Each element must have exactly these keys:\n"
            "  type, name, targetAmount, currentAmount (always 0), monthlySaving, priority, status (always active)\n\n"
            "Valid type values: emergency_fund, healthcare_fund, education_fund, other"
        )

    try:
        raw   = llm([
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": json.dumps(profile)},
        ])
        match = re.search(r"\[\s*\{.*\}\s*\]", raw, re.S)
        if match:
            return json.loads(match.group(0))
        print(f"[LLM SUGGESTED GOALS] No JSON array found in response: {raw[:200]}")
    except Exception as e:
        print(f"[LLM SUGGESTED GOALS FAILED] {e}")

    return []


# ---------------------------------------------------------------------------
# LLM-based custom goal creation -- fully LLM-driven
# User provides goal name + target amount.
# LLM receives those details and decides the monthly saving plan.
# ---------------------------------------------------------------------------

def create_other_goal(user, message):
    system_prompt = (
        "You are a financial planner helping a rural/semi-urban Indian user create a custom savings goal.\n\n"
        "The user will tell you their goal name and target amount (in Rs).\n\n"
        "YOUR JOB:\n"
        "1. Extract the goal name and target amount from their message.\n"
        "2. Decide a realistic monthly saving amount:\n"
        "   - Default: monthlySaving = round(targetAmount / 12)\n"
        "   - Use your judgement if context suggests a shorter or longer timeframe.\n"
        "3. If the goal name OR target amount is missing or unclear, ask a short friendly clarifying question.\n\n"
        "RESPONSE FORMAT -- return ONLY one of these two JSON objects, nothing else:\n\n"
        "If you have enough info:\n"
        "{\"status\":\"ok\",\"name\":\"<goal name>\",\"targetAmount\":<integer>,\"monthlySaving\":<integer>}\n\n"
        "If you need more info:\n"
        "{\"status\":\"ask\",\"message\":\"<short friendly question in the same language the user wrote in>\"}\n\n"
        "Rules:\n"
        "- targetAmount must be a positive integer\n"
        "- monthlySaving must be a positive integer\n"
        "- No markdown, no extra text -- pure JSON only"
    )

    try:
        raw   = llm([
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": message},
        ])
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            data   = json.loads(match.group(0))
            status = data.get("status")

            if status == "ask":
                # LLM needs clarification -- relay its question, stay in pending state
                return reply(data.get("message") or copy(user, "other"))

            if status == "ok":
                name    = (data.get("name") or "").strip() or "Other Goal"
                target  = int(data.get("targetAmount") or 0)
                monthly = int(data.get("monthlySaving") or 0)

                if target > 0 and monthly > 0:
                    goal = {
                        "type":          "other",
                        "name":          name,
                        "targetAmount":  target,
                        "currentAmount": 0,
                        "monthlySaving": monthly,
                        "priority":      5,
                        "status":        "active",
                    }
                    create_goal(user, goal)
                    user["pendingAction"] = ""
                    save_user(user)
                    return reply(
                        f"{copy(user, 'created')} {goal['name']}. "
                        f"{copy(user, 'monthly')} Rs {goal['monthlySaving']}."
                    )

        print(f"[LLM CREATE OTHER GOAL] Unexpected response: {raw[:200]}")
    except Exception as e:
        print(f"[LLM CREATE OTHER GOAL FAILED] {e}")

    # Stay in pending state -- ask again
    return reply(copy(user, "other"))


# ---------------------------------------------------------------------------
# Save progress
# ---------------------------------------------------------------------------

def save_progress(user, saved):
    goal = add_goal_progress(user, saved["goalType"], saved["amount"])
    if not goal:
        return reply(copy(user, "not_found"))

    remaining = max(0, goal["targetAmount"] - goal["currentAmount"])
    return reply(
        f"{copy(user, 'saved')} Rs {saved['amount']} "
        f"for {GOALS.get(goal['type'], goal['name'])}. "
        f"{copy(user, 'remaining')} Rs {remaining}."
    )


def extract_saving(message):
    data = json_from_llm(
        "If the user is reporting that they saved money for a goal, return ONLY this JSON:\n"
        "{\"amount\": <number>, \"goalType\": \"<one of: emergency_fund, lean_season_reserve, healthcare_fund, education_fund, other>\"}\n"
        "If the message is NOT about saving money, return: {}",
        message,
    )
    return data if data.get("amount") and data.get("goalType") else {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def json_from_llm(system, message):
    try:
        raw   = llm([{"role": "system", "content": system}, {"role": "user", "content": str(message)}])
        match = re.search(r"\{.*?\}", raw, re.S)
        return json.loads(match.group(0) if match else "{}")
    except Exception:
        return {}


def goal_buttons(user, goals):
    return [[{"text": label(user, goal), "data": f"choose_goal:{goal['type']}"}] for goal in goals]


def label(user, goal):
    return BUTTON_LABELS.get(user.get("language"), {}).get(goal["type"], goal["name"])


def copy(user, key):
    return TEXT.get(user.get("language"), TEXT["en"]).get(key, "")


def money(value):
    number = re.sub(r"[^0-9.]", "", str(value or "0"))
    return float(number or 0)


def reply(text, buttons=None):
    return {"reply": text, "buttons": buttons or [], "skipTranslation": True}
