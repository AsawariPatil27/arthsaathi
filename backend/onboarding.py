import re

from language import to_english
from users import save_user

# Steps where the user types a free-form answer (not a button callback)
FREE_TEXT_STEPS = {
    "monthlyIncome", "averageIncome", "lowestMonthIncome",
    "monthlyExpense",
    "state", "district",
    "leanDurationMonths", "leanMonthlyExpense",
    "harvestIncome",
}

NUMERIC_STEPS = {
    "monthlyIncome", "averageIncome", "lowestMonthIncome",
    "monthlyExpense",
    "leanDurationMonths", "leanMonthlyExpense",
    "harvestIncome",
}

COPY = {
    "language": "Choose your language.",
    "mode": "Which mode suits you better?",
    "other": "More languages will come later. For now choose English, Hindi, or Marathi.",
    "incomeType": "Your income type?",
    "occupation": "Choose your occupation.",
    "salary": "Monthly take-home salary?",
    "averageIncome": "Average monthly income?",
    "lowestIncome": "Lowest month income?",
    "expense": "Monthly expenses?",
    "state": "Which state are you in?",
    "district": "Which district are you in?",
    "leanDuration": "How many months is your lean season?",
    "leanExpense": "Monthly expenses during lean season?",
    "harvestIncome": "What is your typical income per harvest?",
    "done": "Profile completed. I can now help you with your finances.",
}

OPTIONS = {
    "mode": [("voice", "Voice first"), ("text", "Visual / text")],
    "incomeType": [("fixed", "Fixed income"), ("variable", "Variable income")],
    "fixedJobs": [
        ("government_employee", "Government Employee"),
        ("private_employee", "Private Sector Employee"),
        ("teacher", "Teacher / Professor"),
        ("healthcare_worker", "Healthcare Worker"),
        ("other", "Other"),
    ],
    "variableJobs": [
        ("farmer", "Farmer"),
        ("gig_worker", "Gig Worker"),
        ("shop_owner", "Small Business / Shop Owner"),
        ("daily_wage", "Daily Wage Worker"),
        ("freelancer", "Freelancer"),
        ("homemaker", "Homemaker"),
        ("student", "Student"),
        ("other", "Other"),
    ],
}

# Language buttons stay in native scripts — user hasn't chosen language yet so no translation runs
LANGUAGE_BUTTONS = [
    [{"text": "हिंदी", "data": "hi"}, {"text": "मराठी", "data": "mr"}, {"text": "English", "data": "en"}],
    [{"text": "ಕನ್ನಡ", "data": "kn"}, {"text": "Other languages", "data": "other_lang"}],
]


def ask(key, buttons=None):
    return {"reply": COPY[key], "buttons": buttons or []}


def option_rows(key, one_row=False):
    buttons = [{"text": label, "data": value} for value, label in OPTIONS[key]]
    return [buttons] if one_row else [[b] for b in buttons]


def number(value):
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else 0


def start_onboarding(user):
    user["currentStep"] = "language"
    user["profileCompleted"] = False
    save_user(user)
    return ask("language", LANGUAGE_BUTTONS)


def handle_onboarding(user, raw_answer):
    answer = str(raw_answer or "").strip()
    step = user.get("currentStep")
    # Numeric answers must stay raw. Translating plain amounts can distort them.
    if step in FREE_TEXT_STEPS and step not in NUMERIC_STEPS and answer and not answer.startswith("/"):
        answer = to_english(answer, user.get("language") or "en")

    if answer == "/start" or step == "start":
        return start_onboarding(user)
    if step == "language":
        return set_language(user, answer)
    if step == "interactionMode":
        return set_next(user, "interactionMode", "voice" if answer == "voice" else "text", "incomeType")
    if step == "incomeType":
        user["incomeType"] = "fixed" if answer == "fixed" else "variable"
        return move(user, "occupation", ask("occupation", occupation_buttons(user)))
    if step == "occupation":
        return set_next(user, "occupation", answer, next_income_step({**user, "occupation": answer}))
    if step in ["monthlyIncome", "averageIncome", "lowestMonthIncome", "harvestIncome", "state", "district", "leanDurationMonths", "leanMonthlyExpense", "monthlyExpense"]:
        return save_step(user, step, answer)
    return complete(user)


def set_language(user, answer):
    if answer in ["other_lang", "kn"]:
        return ask("other", LANGUAGE_BUTTONS)
    user["language"] = answer if answer in ["en", "hi", "mr"] else "en"
    return move(user, "interactionMode", ask("mode", option_rows("mode", one_row=True)))


def save_step(user, step, answer):
    value = number(answer) if step not in ["state", "district"] else answer
    user["monthlyIncome" if step == "averageIncome" else step] = value
    next_step = {
        "monthlyIncome": "monthlyExpense",
        "averageIncome": "lowestMonthIncome",
        "lowestMonthIncome": "monthlyExpense",
        "harvestIncome": "state",
        "state": "district",
        "district": "leanDurationMonths",
        "leanDurationMonths": "leanMonthlyExpense",
    }.get(step)
    return complete(user) if not next_step else move(user, next_step, ask_current({**user, "currentStep": next_step}))


def set_next(user, field, value, next_step):
    user[field] = value
    return move(user, next_step, ask_current({**user, "currentStep": next_step}))


def move(user, step, response):
    user["currentStep"] = step
    save_user(user)
    return response


def ask_current(user):
    key = {
        "incomeType": "incomeType",
        "monthlyIncome": "salary",
        "averageIncome": "averageIncome",
        "lowestMonthIncome": "lowestIncome",
        "monthlyExpense": "expense",
        "harvestIncome": "harvestIncome",
        "state": "state",
        "district": "district",
        "leanDurationMonths": "leanDuration",
        "leanMonthlyExpense": "leanExpense",
    }[user["currentStep"]]
    buttons = option_rows("incomeType", one_row=True) if user["currentStep"] == "incomeType" else []
    return ask(key, buttons)


def occupation_buttons(user):
    return option_rows("fixedJobs" if user.get("incomeType") == "fixed" else "variableJobs")


def next_income_step(user):
    if user.get("incomeType") == "fixed":
        return "monthlyIncome"
    return "harvestIncome" if user.get("occupation") == "farmer" else "averageIncome"


def complete(user):
    user["currentStep"] = "done"
    user["profileCompleted"] = True
    save_user(user)

    from menu import get_menu_response

    menu_resp = get_menu_response(user)
    menu_resp["reply"] = f"{COPY['done']}\n\n{menu_resp['reply']}"
    return menu_resp
