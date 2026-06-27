from language import to_english
from users import save_user

# Steps where the user types a free-form answer (not a button callback)
FREE_TEXT_STEPS = {
    "familySize", "earningMembers",
    "emergencyFundAmount",
    "monthlyIncome", "averageIncome", "lowestMonthIncome",
    "monthlyExpense",
    "state", "district", "harvestMonth",
    "leanDurationMonths", "leanMonthlyExpense",
    "harvestIncome",
}

COPY = {
    "en": {
        "language": "Choose your language.",
        "mode": "Which mode suits you better?",
        "other": "More languages will come later. For now choose English, Hindi, or Marathi.",
        "incomeType": "Your income type?",
        "occupation": "Choose your occupation.",
        "familySize": "How many people are in your family?",
        "earningMembers": "How many people earn in your family?",
        "insurance": "Do you have health insurance?",
        "emergency": "Do you already have an emergency fund?",
        "emergencyAmount": "Approximately how much is in your emergency fund?",
        "salary": "Monthly take-home salary?",
        "averageIncome": "Average monthly income?",
        "lowestIncome": "Lowest month income?",
        "expense": "Monthly expenses?",
        "state": "Which state are you in?",
        "district": "Which district are you in?",
        "harvestMonth": "Which month is your harvest month?",
        "leanDuration": "How many months is your lean season?",
        "leanExpense": "Monthly expenses during lean season?",
        "harvestIncome": "What is your typical income per harvest?",
        "done": "Profile completed. I can now create your plan.",
    },
    "hi": {
        "language": "अपनी भाषा चुनें।",
        "mode": "आपके लिए कौन सा तरीका बेहतर है?",
        "other": "बाकी भाषाएं बाद में आएंगी। अभी अंग्रेजी, हिंदी या मराठी चुनें।",
        "incomeType": "आपकी कमाई किस प्रकार की है?",
        "occupation": "अपना काम चुनें।",
        "familySize": "आपके परिवार में कितने लोग हैं?",
        "earningMembers": "परिवार में कमाने वाले कितने लोग हैं?",
        "insurance": "क्या आपके पास स्वास्थ्य बीमा है?",
        "emergency": "क्या आपके पास पहले से आपातकालीन निधि है?",
        "emergencyAmount": "आपातकालीन निधि में लगभग कितनी राशि है?",
        "salary": "मासिक हाथ में आने वाली तनख्वाह कितनी है?",
        "averageIncome": "औसत मासिक आय कितनी है?",
        "lowestIncome": "सबसे कम आय वाले महीने में कितनी कमाई होती है?",
        "expense": "मासिक खर्च कितना है?",
        "state": "आप किस राज्य में हैं?",
        "district": "आप किस जिले में हैं?",
        "harvestMonth": "फसल कटाई का महीना कौन सा है?",
        "leanDuration": "कमाई कम रहने का समय कितने महीने होता है?",
        "leanExpense": "उस समय मासिक खर्च कितना होता है?",
        "harvestIncome": "फसल कटाई पर आपकी आमदनी (कमाई) लगभग कितनी होती है?",
        "done": "प्रोफाइल पूरी हो गई। अब मैं आपका योजना बना सकता हूं।",
    },
    "mr": {
        "language": "तुमची भाषा निवडा.",
        "mode": "तुमच्यासाठी कोणता प्रकार जास्त सोयीचा आहे?",
        "other": "इतर भाषा नंतर येतील. सध्या इंग्रजी, हिंदी किंवा मराठी निवडा.",
        "incomeType": "तुमचे उत्पन्न कोणत्या प्रकारचे आहे?",
        "occupation": "तुमचा व्यवसाय निवडा.",
        "familySize": "तुमच्या कुटुंबात किती लोक आहेत?",
        "earningMembers": "कुटुंबात कमावणारे किती लोक आहेत?",
        "insurance": "तुमच्याकडे आरोग्य विमा आहे का?",
        "emergency": "तुमच्याकडे आधीपासून आपत्कालीन निधी आहे का?",
        "emergencyAmount": "आपत्कालीन निधीत अंदाजे किती रक्कम आहे?",
        "salary": "दर महिन्याला हातात येणारा पगार किती आहे?",
        "averageIncome": "सरासरी मासिक उत्पन्न किती आहे?",
        "lowestIncome": "सगळ्यात कमी उत्पन्नाच्या महिन्यात किती कमाई होते?",
        "expense": "मासिक खर्च किती आहे?",
        "state": "तुम्ही कोणत्या राज्यात आहात?",
        "district": "तुम्ही कोणत्या जिल्ह्यात आहात?",
        "harvestMonth": "पीक कापणीचा महिना कोणता?",
        "leanDuration": "कमी उत्पन्नाचा काळ किती महिने असतो?",
        "leanExpense": "त्या काळात मासिक खर्च किती असतो?",
        "harvestIncome": "पीक कापणीच्या वेळी तुमचे अंदाजे उत्पन्न किती असते?",
        "done": "प्रोफाइल पूर्ण झाली. आता मी तुमची योजना बनवू शकतो.",
    },
}

OPTIONS = {
    "mode": [("voice", "Voice first", "आवाज आधी", "आवाज प्रथम"), ("text", "Visual / text", "दृश्य / मजकूर", "दृश्य / मजकूर")],
    "incomeType": [("fixed", "Fixed income", "निश्चित आय", "निश्चित उत्पन्न"), ("variable", "Variable income", "बदलती आय", "बदलते उत्पन्न")],
    "yesNo": [("yes", "Yes", "हां", "हो"), ("no", "No", "नहीं", "नाही")],
    "fixedJobs": [
        ("government_employee", "Government Employee", "सरकारी कर्मचारी", "सरकारी कर्मचारी"),
        ("private_employee", "Private Sector Employee", "निजी क्षेत्र कर्मचारी", "खाजगी क्षेत्रातील कर्मचारी"),
        ("teacher", "Teacher / Professor", "शिक्षक / प्रोफेसर", "शिक्षक / प्राध्यापक"),
        ("healthcare_worker", "Healthcare Worker", "स्वास्थ्य कर्मचारी", "आरोग्य कर्मचारी"),
        ("other", "Other", "अन्य", "इतर"),
    ],
    "variableJobs": [
        ("farmer", "Farmer", "किसान", "शेतकरी"),
        ("gig_worker", "Gig Worker", "गिग कामगार", "गिग कामगार"),
        ("shop_owner", "Small Business / Shop Owner", "छोटा व्यवसाय / दुकानदार", "लहान व्यवसाय / दुकानदार"),
        ("daily_wage", "Daily Wage Worker", "दिहाड़ी मजदूर", "रोजंदारी कामगार"),
        ("freelancer", "Freelancer", "स्वतंत्र कामगार", "स्वतंत्र कामगार"),
        ("homemaker", "Homemaker", "गृहिणी", "गृहिणी"),
        ("student", "Student", "विद्यार्थी", "विद्यार्थी"),
        ("other", "Other", "अन्य", "इतर"),
    ],
}

LANGUAGE_BUTTONS = [
    [{"text": "हिंदी", "data": "hi"}, {"text": "मराठी", "data": "mr"}, {"text": "English", "data": "en"}],
    [{"text": "ಕನ್ನಡ", "data": "kn"}, {"text": "Other languages", "data": "other_lang"}],
]


def lang(user):
    return user.get("language") or "en"


def ask(user, key, buttons=None):
    return {"reply": COPY[lang(user)][key], "buttons": buttons or []}


def option_button(item, user):
    index = {"en": 1, "hi": 2, "mr": 3}.get(lang(user), 1)
    return {"text": item[index], "data": item[0]}


def option_rows(key, user, one_row=False):
    buttons = [option_button(item, user) for item in OPTIONS[key]]
    return [buttons] if one_row else [[button] for button in buttons]


def number(value):
    digits = "".join(ch for ch in str(value or "0") if ch.isdigit() or ch == ".")
    return float(digits) if digits else 0


def start_onboarding(user):
    user["currentStep"] = "language"
    user["profileCompleted"] = False
    save_user(user)
    return ask(user, "language", LANGUAGE_BUTTONS)


def handle_onboarding(user, raw_answer):
    answer = str(raw_answer or "").strip()
    step = user.get("currentStep")
    # Normalise free-text answers to English/numeric before processing
    if step in FREE_TEXT_STEPS and answer and not answer.startswith("/"):
        answer = to_english(answer, user.get("language") or "en")

    if answer == "/start" or step == "start":
        return start_onboarding(user)
    if step == "language":
        return set_language(user, answer)
    if step == "interactionMode":
        return set_next(user, "interactionMode", "voice" if answer == "voice" else "text", "incomeType")
    if step == "incomeType":
        user["incomeType"] = "fixed" if answer == "fixed" else "variable"
        return move(user, "occupation", ask(user, "occupation", occupation_buttons(user)))
    if step == "occupation":
        return set_next(user, "occupation", answer, "familySize")
    if step == "familySize":
        return set_next(user, "familySize", number(answer), "earningMembers")
    if step == "earningMembers":
        return set_next(user, "earningMembers", number(answer), "hasInsurance")
    if step == "hasInsurance":
        return set_next(user, "hasInsurance", answer == "yes", "hasEmergencyFund")
    if step == "hasEmergencyFund":
        user["hasEmergencyFund"] = answer == "yes"
        next_step = "emergencyFundAmount" if user["hasEmergencyFund"] else next_income_step(user)
        return move(user, next_step, ask_current({**user, "currentStep": next_step}))
    if step in ["emergencyFundAmount", "monthlyIncome", "averageIncome", "lowestMonthIncome", "harvestIncome", "state", "district", "harvestMonth", "leanDurationMonths", "leanMonthlyExpense", "monthlyExpense"]:
        return save_step(user, step, answer)
    return complete(user)


def set_language(user, answer):
    if answer in ["other_lang", "kn"]:
        return ask(user, "other", LANGUAGE_BUTTONS)
    user["language"] = answer if answer in ["en", "hi", "mr"] else "en"
    return move(user, "interactionMode", ask(user, "mode", option_rows("mode", user, True)))


def save_step(user, step, answer):
    value = number(answer) if step not in ["state", "district", "harvestMonth"] else answer
    user["monthlyIncome" if step == "averageIncome" else step] = value
    next_step = {
        "emergencyFundAmount": next_income_step(user),
        "monthlyIncome": "monthlyExpense",
        "averageIncome": "lowestMonthIncome",
        "lowestMonthIncome": "monthlyExpense",
        "harvestIncome": "state",
        "state": "district",
        "district": "harvestMonth",
        "harvestMonth": "leanDurationMonths",
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
        "familySize": "familySize",
        "earningMembers": "earningMembers",
        "hasInsurance": "insurance",
        "hasEmergencyFund": "emergency",
        "emergencyFundAmount": "emergencyAmount",
        "monthlyIncome": "salary",
        "averageIncome": "averageIncome",
        "lowestMonthIncome": "lowestIncome",
        "monthlyExpense": "expense",
        "harvestIncome": "harvestIncome",
        "state": "state",
        "district": "district",
        "harvestMonth": "harvestMonth",
        "leanDurationMonths": "leanDuration",
        "leanMonthlyExpense": "leanExpense",
    }[user["currentStep"]]
    buttons = option_rows("incomeType", user, True) if user["currentStep"] == "incomeType" else option_rows("yesNo", user, True) if user["currentStep"] in ["hasInsurance", "hasEmergencyFund"] else []
    return ask(user, key, buttons)


def occupation_buttons(user):
    return option_rows("fixedJobs" if user.get("incomeType") == "fixed" else "variableJobs", user)


def next_income_step(user):
    if user.get("incomeType") == "fixed":
        return "monthlyIncome"
    return "harvestIncome" if user.get("occupation") == "farmer" else "averageIncome"


def complete(user):
    user["currentStep"] = "done"
    user["profileCompleted"] = True
    save_user(user)

    from ai.agents.planner_agent import start_plan
    from language import to_user_language

    plan = start_plan(user)
    plan["reply"] = f"{COPY['en']['done']}\n\n{plan['reply']}"
    return to_user_language(plan, lang(user))
