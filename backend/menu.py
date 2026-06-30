MENU_COPY = {
    "text": "Choose a feature from the menu below:",
    "tracker": "💵 Expense Tracker",
    "insights": "📊 Spending Insights",
    "mandi": "🌾 Mandi Crop Prices",
    "schemes": "🏛️ Govt Schemes",
    "jargon": "📖 Financial Jargon Explainer",
    "scam": "🛡️ Scam & Phishing Checker",
    "profile": "👤 Update Profile",
    "tracker_prompt": "Please send a debit/credit SMS or type your expense (e.g., 'spent 500 on food') to record it.",
    "mandi_prompt": "Which crop or commodity price do you want to check?",
    "schemes_prompt": "Which scheme would you like to search for, or what is your occupation?",
    "jargon_prompt": "What financial term would you like me to explain (e.g., SIP, EMI, NAV, Inflation)?",
    "scam_prompt": "Please paste the suspicious link, website, message, or phone number you want to verify.",
    "profile_prompt": "What details would you like to update? (e.g., 'change language to Hindi', 'update my monthly income')",
}


def get_menu_response(user):
    buttons = [
        [{"text": MENU_COPY["tracker"], "data": "menu:tracker"}],
        [{"text": MENU_COPY["insights"], "data": "menu:insights"}],
        [{"text": MENU_COPY["mandi"], "data": "menu:mandi"}],
        [{"text": MENU_COPY["schemes"], "data": "menu:schemes"}],
        [{"text": MENU_COPY["jargon"], "data": "menu:jargon"}],
        [{"text": MENU_COPY["scam"], "data": "menu:scam"}],
        [{"text": MENU_COPY["profile"], "data": "menu:profile"}],
    ]
    return {"reply": MENU_COPY["text"], "buttons": buttons}


def handle_menu_callback(user, action):
    if action == "tracker":
        return {"reply": MENU_COPY["tracker_prompt"], "buttons": []}

    if action == "insights":
        from ai.agents.insights_agent import insights_agent
        return insights_agent(user, "")

    if action == "mandi":
        return {"reply": MENU_COPY["mandi_prompt"], "buttons": []}

    if action == "schemes":
        return {"reply": MENU_COPY["schemes_prompt"], "buttons": []}

    if action == "jargon":
        return {"reply": MENU_COPY["jargon_prompt"], "buttons": []}

    if action == "scam":
        return {"reply": MENU_COPY["scam_prompt"], "buttons": []}

    if action == "profile":
        return {"reply": MENU_COPY["profile_prompt"], "buttons": []}

    return get_menu_response(user)
