import json
import math
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

FIXED_ALLOCATIONS = {
    "emergency_fund": 0.50,
    "healthcare_fund": 0.30,
    "other": 0.20,
}

VARIABLE_ALLOCATIONS = {
    "emergency_fund": 0.60,
    "healthcare_fund": 0.25,
    "other": 0.15,
}

FARMER_ALLOCATIONS = {
    "lean_season_reserve": 0.50,
    "emergency_fund": 0.25,
    "healthcare_fund": 0.15,
    "other": 0.10,
}

TEXT = {
    "intro": "Based on your profile, these saving goals may fit you:",
    "choose": "Choose the goal you want to create.",
    "active": "Your active saving goals:",
    "also": "You can also create these:",
    "progress": "To add progress, type: I saved 500 for emergency fund.",
    "created": "Created",
    "monthly": "Monthly target is",
    "again": "Please ask me to create your savings plan again.",
    "not_found": "I could not find that goal. Ask me to create your savings plan first.",
    "saved": "Saved",
    "remaining": "Remaining target is",
    "error": "Something went wrong. Please try again.",
}


def planner_agent(user, message):
    text = str(message or "").strip()

    if text.startswith("choose_goal:"):
        return choose_goal(user, text.split(":", 1)[1])
    if text.startswith("confirm_goal:"):
        return confirm_goal(user, text.split(":", 1)[1])
    if text.startswith("edit_goal:"):
        return start_edit_goal(user, text.split(":", 1)[1])

    pending = user.get("pendingAction") or ""
    if pending == "ask_monthly_expense_for_goal_plan":
        return save_missing_monthly_expense(user, text)
    if pending == "ask_this_month_income_for_goal_plan":
        return save_this_month_income(user, text)
    if pending == "ask_farmer_lean_season_for_goal_plan":
        return save_farmer_lean_season_status(user, text)
    if pending in {"other_goal_name", "other_goal_amount", "other_goal_duration"}:
        return continue_other_goal(user, text)
    if pending in {"edit_goal_amount", "edit_goal_duration"}:
        return continue_edit_goal(user, text)

    saved = extract_saving(text)
    if saved:
        return save_progress(user, saved)

    active = user_goals(user)
    if active and is_variable_non_farmer(user):
        clear_planning_income(user)
        readiness = variable_income_readiness(user)
        if readiness:
            return readiness
    return show_existing(user, active) if active else start_plan(user)


def start_plan(user, refresh_variable_income=True):
    if refresh_variable_income and is_variable_non_farmer(user):
        clear_planning_income(user)

    if is_fixed_income(user):
        readiness = fixed_income_readiness(user)
        if readiness:
            return readiness
    elif is_farmer(user):
        readiness = farmer_readiness(user)
        if readiness:
            return readiness
    elif is_variable_non_farmer(user):
        readiness = variable_income_readiness(user)
        if readiness:
            return readiness

    goals = suggested_goals(user)
    if not goals:
        return reply(TEXT["error"])

    user["pendingGoals"] = goals
    save_user(user)

    lines = [TEXT["intro"]]
    if is_fixed_income(user):
        lines.append("For fixed-income users, I divide monthly savings as: 50% emergency fund, 30% healthcare fund, and 20% other goals.")
    elif is_farmer(user):
        lines.append("For farmers, I divide savings as: 50% lean season reserve, 25% emergency fund, 15% healthcare fund, and 10% other goals.")
        lines.append("Lean season reserve comes first because farm income is seasonal and expenses continue even when income is low.")
    elif is_variable_non_farmer(user):
        lines.append("For variable-income users, I divide this month's safe savings as: 60% emergency/income buffer, 25% healthcare fund, and 15% other goals.")
        lines.append("The emergency buffer is first because gig or irregular income can drop suddenly, and it protects monthly expenses in low-income months.")
    lines += [format_goal_line(i, goal) for i, goal in enumerate(goals, 1)]
    lines.append(TEXT["choose"])
    return reply("\n".join(lines), goal_buttons(goals))


def show_existing(user, active):
    created = {goal["type"] for goal in active}
    remaining = [goal for goal in suggested_goals(user) if goal["type"] not in created]
    user["pendingGoals"] = remaining
    save_user(user)

    lines = [TEXT["active"]]
    lines += [
        f"{label(goal)}: Rs {round_money(goal.get('currentAmount'))} / Rs {round_money(goal.get('targetAmount'))}, monthly Rs {round_money(goal.get('monthlySaving'))}"
        for goal in active
    ]
    if remaining:
        lines.append("\n" + TEXT["also"])
        lines += [format_goal_line(i, goal) for i, goal in enumerate(remaining, 1)]
        return reply("\n".join(lines), goal_buttons(remaining))
    lines.append("\n" + TEXT["progress"])
    return reply("\n".join(lines))


def choose_goal(user, goal_type):
    if goal_type == "other":
        user["pendingAction"] = "other_goal_name"
        user["pendingGoalDraft"] = {"type": "other"}
        save_user(user)
        return reply("What is this goal called? Please send only the goal name.")

    goal = next((g for g in user.get("pendingGoals", []) if g["type"] == goal_type), None)
    if not goal:
        return reply(TEXT["again"])

    user["pendingGoalDraft"] = goal
    save_user(user)
    return reply(goal_proposal_text(user, goal), confirm_buttons(goal_type))


def confirm_goal(user, goal_type):
    goal = user.get("pendingGoalDraft") or {}
    if goal.get("type") != goal_type:
        goal = next((g for g in user.get("pendingGoals", []) if g["type"] == goal_type), None)
    if not goal:
        return reply(TEXT["again"])

    create_goal(user, goal)
    user["pendingAction"] = ""
    user["pendingGoalDraft"] = {}
    user["pendingGoalContext"] = {}
    save_user(user)
    return reply(f"{TEXT['created']} {label(goal)}. {TEXT['monthly']} Rs {round_money(goal['monthlySaving'])}.")


def start_edit_goal(user, goal_type):
    goal = user.get("pendingGoalDraft") or {}
    if goal.get("type") != goal_type:
        goal = next((g for g in user.get("pendingGoals", []) if g["type"] == goal_type), None)
    if not goal:
        return reply(TEXT["again"])

    user["pendingAction"] = "edit_goal_amount"
    user["pendingGoalDraft"] = goal
    save_user(user)
    return reply(f"Okay. What target amount do you want for {label(goal)}? Send only the amount in Rs.")


def continue_edit_goal(user, message):
    draft = user.get("pendingGoalDraft") or {}
    if not draft:
        user["pendingAction"] = ""
        save_user(user)
        return reply(TEXT["again"])

    if user.get("pendingAction") == "edit_goal_amount":
        amount = money(message)
        if amount <= 0:
            return reply("Please send a valid target amount in Rs.")
        draft["targetAmount"] = round_money(amount)
        user["pendingGoalDraft"] = draft
        user["pendingAction"] = "edit_goal_duration"
        save_user(user)
        return reply("In how many months do you want to complete this goal? Send only the number of months.")

    months = duration_months(message)
    if not months:
        return reply("Please send a valid duration in months, between 1 and 360.")

    return finalize_draft_with_feasibility(user, draft, months)


def continue_other_goal(user, message):
    draft = user.get("pendingGoalDraft") or {"type": "other"}
    pending = user.get("pendingAction")

    if pending == "other_goal_name":
        name = str(message or "").strip()
        if not name:
            return reply("Please send the goal name.")
        draft.update({"type": "other", "name": name})
        user["pendingGoalDraft"] = draft
        user["pendingAction"] = "other_goal_amount"
        save_user(user)
        return reply("How much money do you need for this goal? Send only the amount in Rs.")

    if pending == "other_goal_amount":
        amount = money(message)
        if amount <= 0:
            return reply("Please send a valid amount in Rs.")
        draft["targetAmount"] = round_money(amount)
        user["pendingGoalDraft"] = draft
        user["pendingAction"] = "other_goal_duration"
        save_user(user)
        return reply("In how many months do you want to complete this goal? Send only the number of months.")

    months = duration_months(message)
    if not months:
        return reply("Please send a valid duration in months, between 1 and 360.")

    return finalize_draft_with_feasibility(user, draft, months)


def finalize_draft_with_feasibility(user, draft, months):
    target = money(draft.get("targetAmount"))
    available = available_monthly_capacity(user, draft.get("type"))
    if available <= 0:
        user["pendingAction"] = ""
        user["pendingGoalDraft"] = {}
        user["pendingGoalContext"] = {}
        save_user(user)
        return reply("I cannot save this goal yet because your current monthly expenses are equal to or higher than your monthly income.")

    required = math.ceil(target / months)
    if required > available:
        corrected_months = math.ceil(target / available)
        draft["monthlySaving"] = round_money(available)
        draft["durationMonths"] = corrected_months
        user["pendingGoalDraft"] = draft
        user["pendingAction"] = ""
        save_user(user)
        return reply(
            "This plan is not possible with your current monthly savings capacity.\n"
            f"You asked for Rs {round_money(target)} in {months} months, which needs Rs {required}/month.\n"
            f"You can safely save up to Rs {round_money(available)}/month for this goal.\n"
            f"Corrected plan: Rs {round_money(target)} in {corrected_months} months.",
            confirm_buttons(draft["type"]),
        )

    draft["monthlySaving"] = required
    draft["durationMonths"] = months
    draft.setdefault("currentAmount", 0)
    draft.setdefault("priority", 5 if draft.get("type") == "other" else 1)
    draft.setdefault("status", "active")
    user["pendingGoalDraft"] = draft
    user["pendingAction"] = ""
    save_user(user)
    return reply(goal_proposal_text(user, draft), confirm_buttons(draft["type"]))


def save_missing_monthly_expense(user, message):
    expense = money(message)
    if expense <= 0:
        return reply("Please send your monthly expenses as a number, for example 18000.")
    user["monthlyExpense"] = expense
    user["pendingAction"] = ""
    save_user(user)
    return start_plan(user)


def save_this_month_income(user, message):
    income = money(message)
    if income <= 0:
        return reply("Please send this month's income as a number, for example 22000.")
    context = dict(user.get("pendingGoalContext") or {})
    context["thisMonthIncome"] = income
    user["pendingGoalContext"] = context
    user["pendingAction"] = ""
    save_user(user)
    return start_plan(user, refresh_variable_income=False)


_YES = {
    # English / Hinglish
    "yes", "y", "yeah", "yep", "yup", "ok", "okay",
    "haan", "ha", "ho", "haa", "han", "ji", "ji haan", "haan ji",
    # Devanagari (Hindi/Marathi)
    "हा", "हाँ", "हां", "हो", "जी", "जी हाँ", "हाँ जी", "हान", "ओके",
}
_NO = {
    # English / Hinglish
    "no", "n", "nope", "nahi", "nahin", "na", "naa",
    # Devanagari (Hindi/Marathi)
    "नहीं", "नही", "ना", "नहीं जी", "नाही", "नाहीं",
}

def save_farmer_lean_season_status(user, message):
    # Check both the (possibly LLM-translated) message AND the original raw text.
    # This makes yes/no detection robust even when to_english() is imperfect.
    candidates = {
        str(msg or "").strip().lower()
        for msg in [message, user.get("originalMessage")]
        if msg
    }
    if candidates & _YES:
        user["isLeanSeasonNow"] = True
    elif candidates & _NO:
        user["isLeanSeasonNow"] = False
    else:
        return reply("Please answer yes or no. Are you currently in lean season?")

    user["pendingAction"] = ""
    save_user(user)
    return start_plan(user)


def suggested_goals(user):
    if is_fixed_income(user):
        return fixed_income_goals(user)
    return non_fixed_goals(user)


def fixed_income_goals(user):
    income = money(user.get("monthlyIncome"))
    expense = money(user.get("monthlyExpense"))
    capacity = max(0, income - expense)

    emergency_monthly = math.floor(capacity * FIXED_ALLOCATIONS["emergency_fund"])
    emergency_target = round_money(expense * 6)

    healthcare_monthly = math.floor(capacity * FIXED_ALLOCATIONS["healthcare_fund"])
    healthcare_target = round_money(expense * 3)
    other_monthly = math.floor(capacity * FIXED_ALLOCATIONS["other"])

    return [
        make_goal("emergency_fund", "Emergency Fund", emergency_target, emergency_monthly, 1),
        make_goal("healthcare_fund", "Healthcare Fund", healthcare_target, healthcare_monthly, 2),
        goal("other", "Other Goal", 0, other_monthly, 3, 0),
    ]


def non_fixed_goals(user):
    if is_variable_non_farmer(user):
        return variable_non_farmer_goals(user)

    expense = money(user.get("leanMonthlyExpense") if is_farmer(user) else user.get("monthlyExpense"))
    if expense <= 0:
        expense = max(1, money(user.get("monthlyIncome")) * 0.6)

    if is_farmer(user):
        capacity = max(0, non_fixed_capacity(user))
        lean_months = max(1, int(money(user.get("leanDurationMonths")) or 1))
        lean_target = round_money(expense * lean_months)
        emergency_target = round_money(expense * 3)
        healthcare_target = round_money(expense * 3)
        return [
            allocated_goal("lean_season_reserve", "Lean Season Reserve", lean_target, capacity, FARMER_ALLOCATIONS, 1),
            allocated_goal("emergency_fund", "Emergency Fund", emergency_target, capacity, FARMER_ALLOCATIONS, 2),
            allocated_goal("healthcare_fund", "Healthcare Fund", healthcare_target, capacity, FARMER_ALLOCATIONS, 3),
            allocated_goal("other", "Other Goal", 0, capacity, FARMER_ALLOCATIONS, 4),
        ]

    emergency_target = round_money(expense * 3)
    healthcare_target = round_money(expense * 3)
    return [
        goal("emergency_fund", "Emergency Fund", emergency_target, math.ceil(emergency_target / 6), 1, 6),
        goal("healthcare_fund", "Healthcare Fund", healthcare_target, math.ceil(healthcare_target / 12), 2, 12),
        goal("other", "Other Goal", 0, 0, 3, 0),
    ]


def variable_non_farmer_goals(user):
    expense = money(user.get("monthlyExpense"))
    capacity = max(0, planning_this_month_income(user) - expense)

    emergency_monthly = math.floor(capacity * VARIABLE_ALLOCATIONS["emergency_fund"])
    healthcare_monthly = math.floor(capacity * VARIABLE_ALLOCATIONS["healthcare_fund"])
    other_monthly = math.floor(capacity * VARIABLE_ALLOCATIONS["other"])

    emergency_target = round_money(expense * 4)
    healthcare_target = round_money(expense * 2)

    return [
        make_goal("emergency_fund", "Emergency / Income Buffer", emergency_target, emergency_monthly, 1),
        make_goal("healthcare_fund", "Healthcare Fund", healthcare_target, healthcare_monthly, 2),
        goal("other", "Other Goal", 0, other_monthly, 3, 0),
    ]


def fixed_income_readiness(user):
    income = money(user.get("monthlyIncome"))
    expense = money(user.get("monthlyExpense"))
    if income <= 0:
        return reply("Please update your monthly take-home salary first, then I can create a savings plan.")
    if expense <= 0:
        user["pendingAction"] = "ask_monthly_expense_for_goal_plan"
        save_user(user)
        return reply("What are your monthly expenses? Send only the amount in Rs.")
    if expense >= income:
        return reply(
            f"Your monthly income is Rs {round_money(income)} and monthly expenses are Rs {round_money(expense)}. "
            "There is no monthly savings capacity right now, so I cannot create a realistic savings goal. "
            "Reduce expenses or update your income/expense profile first."
        )
    return None


def variable_income_readiness(user):
    lowest_income = money(user.get("lowestMonthIncome"))
    monthly_expense = money(user.get("monthlyExpense"))
    this_month_income = planning_this_month_income(user)

    if lowest_income <= 0:
        return reply("Please update your lowest month income first, then I can create a safe savings plan.")
    if monthly_expense <= 0:
        user["pendingAction"] = "ask_monthly_expense_for_goal_plan"
        save_user(user)
        return reply("What are your monthly expenses? Send only the amount in Rs.")
    if this_month_income <= 0:
        user["pendingAction"] = "ask_this_month_income_for_goal_plan"
        save_user(user)
        return reply("What was your income this month? Send only the amount in Rs.")

    safe_income_floor = lowest_income * 1.25
    if this_month_income <= safe_income_floor or this_month_income <= monthly_expense:
        return reply(
            "Your low-month income does not safely cover your monthly expenses. "
            "First goal should be expense reduction or an income buffer.\n"
            f"Your this-month income is Rs {round_money(this_month_income)}, "
            f"your safety check amount is Rs {round_money(safe_income_floor)}, "
            f"and your monthly expenses are Rs {round_money(monthly_expense)}."
        )
    return None


def farmer_readiness(user):
    harvest_income = money(user.get("harvestIncome"))
    lean_months = money(user.get("leanDurationMonths"))
    lean_expense = money(user.get("leanMonthlyExpense"))

    if harvest_income <= 0:
        return reply("Please update your harvest income first, then I can create a farmer savings plan.")
    if lean_months <= 0:
        return reply("Please update your lean season duration first, then I can create a farmer savings plan.")
    if lean_expense <= 0:
        return reply("Please update your lean season monthly expenses first, then I can create a farmer savings plan.")

    if user.get("isLeanSeasonNow") is None:
        user["pendingAction"] = "ask_farmer_lean_season_for_goal_plan"
        save_user(user)
        return reply("Are you currently in lean season? Reply yes or no.")

    lean_need = lean_expense * lean_months
    if user.get("isLeanSeasonNow") is True:
        return reply(
            "You are in lean season now, so do not try to save this month. "
            "Use your lean season reserve for necessary expenses if you have it.\n"
            f"Your estimated lean season need is Rs {round_money(lean_need)} "
            f"({round_money(lean_expense)} x {round_money(lean_months)} months)."
        )

    if harvest_income < lean_need:
        return reply(
            "Your harvest income may not safely cover your lean-season expenses. "
            "First goal should be reducing expenses, increasing income, or creating a lean-season survival buffer.\n"
            f"Harvest income: Rs {round_money(harvest_income)}. "
            f"Lean season need: Rs {round_money(lean_need)}."
        )
    return None


def available_monthly_capacity(user, goal_type=None):
    if is_fixed_income(user):
        base = money(user.get("monthlyIncome")) - money(user.get("monthlyExpense"))
        if goal_type in FIXED_ALLOCATIONS:
            return max(0, math.floor(base * FIXED_ALLOCATIONS[goal_type]))
    elif is_variable_non_farmer(user):
        base = planning_this_month_income(user) - money(user.get("monthlyExpense"))
        if goal_type in VARIABLE_ALLOCATIONS:
            return max(0, math.floor(base * VARIABLE_ALLOCATIONS[goal_type]))
    elif is_farmer(user):
        base = non_fixed_capacity(user)
        if goal_type in FARMER_ALLOCATIONS:
            return max(0, math.floor(base * FARMER_ALLOCATIONS[goal_type]))
    else:
        base = non_fixed_capacity(user)

    committed = 0
    for existing in user_goals(user):
        if existing.get("type") == goal_type and goal_type != "other":
            continue
        committed += money(existing.get("monthlySaving"))
    return max(0, math.floor(base - committed))


def non_fixed_capacity(user):
    if is_variable_non_farmer(user):
        return planning_this_month_income(user) - money(user.get("monthlyExpense"))
    if is_farmer(user):
        return money(user.get("harvestIncome")) / 12 - money(user.get("leanMonthlyExpense"))
    average = (money(user.get("monthlyIncome")) + money(user.get("lowestMonthIncome"))) / 2
    return average - money(user.get("monthlyExpense"))


def goal(goal_type, name, target, monthly, priority, duration):
    return {
        "type": goal_type,
        "name": name,
        "targetAmount": round_money(target),
        "currentAmount": 0,
        "monthlySaving": round_money(monthly),
        "durationMonths": int(duration or 0),
        "priority": priority,
        "status": "active",
    }


def make_goal(goal_type, name, target, monthly, priority, duration=None):
    return goal(goal_type, name, target, monthly, priority, months_for(target, monthly) if duration is None else duration)


def allocated_goal(goal_type, name, target, capacity, allocations, priority):
    monthly = math.floor(capacity * allocations[goal_type])
    return make_goal(goal_type, name, target, monthly, priority, 0 if target == 0 else None)


def goal_proposal_text(user, goal_data):
    if goal_data["type"] == "other":
        cap = available_monthly_capacity(user, "other")
        percent = allocation_percent(user, "other")
        return (
            f"Suggested plan for {goal_data.get('name', 'Other Goal')}:\n"
            f"Target: Rs {round_money(goal_data.get('targetAmount'))}\n"
            f"Duration: {int(goal_data.get('durationMonths') or 0)} months\n"
            f"Monthly saving: Rs {round_money(goal_data.get('monthlySaving'))}\n"
            f"Your available monthly savings capacity for other goals is Rs {round_money(cap)}. This uses {percent}% of your monthly savings capacity."
        )

    percent = allocation_percent(user, goal_data["type"])
    percent_text = f" This uses {percent}% of your monthly savings capacity." if percent else ""
    return (
        f"Suggested plan for {label(goal_data)}:\n"
        f"Target: Rs {round_money(goal_data.get('targetAmount'))}\n"
        f"Duration: {int(goal_data.get('durationMonths') or 0)} months\n"
        f"Monthly saving: Rs {round_money(goal_data.get('monthlySaving'))}.{percent_text}"
    )


def format_goal_line(index, goal_data):
    if goal_data["type"] == "other":
        monthly = round_money(goal_data.get("monthlySaving"))
        return f"{index}. {label(goal_data)} - reserve up to Rs {monthly}/month, choose your own name, amount, and duration"
    return (
        f"{index}. {label(goal_data)} - target Rs {round_money(goal_data['targetAmount'])}, "
        f"monthly Rs {round_money(goal_data['monthlySaving'])}, duration {goal_data.get('durationMonths', 0)} months"
    )


def save_progress(user, saved):
    goal_data = add_goal_progress(user, saved["goalType"], saved["amount"])
    if not goal_data:
        return reply(TEXT["not_found"])

    remaining = max(0, money(goal_data["targetAmount"]) - money(goal_data["currentAmount"]))
    return reply(
        f"{TEXT['saved']} Rs {round_money(saved['amount'])} "
        f"for {GOALS.get(goal_data['type'], goal_data['name'])}. "
        f"{TEXT['remaining']} Rs {round_money(remaining)}."
    )


def extract_saving(message):
    data = json_from_llm(
        "If the user is reporting that they saved money for a goal, return ONLY this JSON:\n"
        "{\"amount\": <number>, \"goalType\": \"<one of: emergency_fund, lean_season_reserve, healthcare_fund, education_fund, other>\"}\n"
        "If the message is NOT about saving money, return: {}",
        message,
    )
    return data if data.get("amount") and data.get("goalType") else {}


def json_from_llm(system, message):
    try:
        raw = llm([{"role": "system", "content": system}, {"role": "user", "content": str(message)}])
        match = re.search(r"\{.*?\}", raw, re.S)
        return json.loads(match.group(0) if match else "{}")
    except Exception:
        return {}


def goal_buttons(goals):
    return [[{"text": label(goal_data), "data": f"choose_goal:{goal_data['type']}"}] for goal_data in goals]


def confirm_buttons(goal_type):
    return [[
        {"text": "Save", "data": f"confirm_goal:{goal_type}"},
        {"text": "Edit", "data": f"edit_goal:{goal_type}"},
    ]]


def label(goal_data):
    return goal_data.get("name") or GOALS.get(goal_data["type"], "Goal")


def is_fixed_income(user):
    return (user.get("incomeType") or "").lower().strip() == "fixed"


def is_farmer(user):
    return (user.get("occupation") or "").lower().strip() == "farmer"


def is_variable_non_farmer(user):
    return (user.get("incomeType") or "").lower().strip() == "variable" and not is_farmer(user)


def allocation_percent(user, goal_type):
    allocations = FIXED_ALLOCATIONS if is_fixed_income(user) else FARMER_ALLOCATIONS if is_farmer(user) else VARIABLE_ALLOCATIONS if is_variable_non_farmer(user) else {}
    return int(allocations.get(goal_type, 0) * 100)


def planning_this_month_income(user):
    return money((user.get("pendingGoalContext") or {}).get("thisMonthIncome"))


def clear_planning_income(user):
    context = dict(user.get("pendingGoalContext") or {})
    if context.pop("thisMonthIncome", None) is not None:
        user["pendingGoalContext"] = context
        save_user(user)


def money(value):
    number = re.sub(r"[^0-9.]", "", str(value or "0"))
    try:
        return float(number or 0)
    except ValueError:
        return 0


def duration_months(value):
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return 0
    months = int(match.group(0))
    return months if 1 <= months <= 360 else 0


def round_money(value):
    return int(round(float(value or 0)))


def months_for(target, monthly):
    return int(math.ceil(target / monthly)) if monthly and target else 0


def reply(text, buttons=None):
    return {"reply": text, "buttons": buttons or []}
