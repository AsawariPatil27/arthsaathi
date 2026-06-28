def lang(user):
    return user.get("language") or "en"

MENU_COPY = {
    "en": {
        "text": "Choose a feature from the menu below:",
        "planner": "🎯 Savings Goals & Planner",
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
    },
    "hi": {
        "text": "नीचे दिए गए मेनू से एक सुविधा चुनें:",
        "planner": "🎯 बचत लक्ष्य और योजना",
        "tracker": "💵 दैनिक खर्च ट्रैकर",
        "insights": "📊 खर्च के विश्लेषण",
        "mandi": "🌾 मंडी फसल के भाव",
        "schemes": "🏛️ सरकारी योजनाएं",
        "jargon": "📖 वित्तीय शब्द स्पष्टीकरण",
        "scam": "🛡️ घोटाला और फ़िशिंग जांच",
        "profile": "👤 प्रोफ़ाइल अपडेट करें",
        "tracker_prompt": "कृपया खर्च रिकॉर्ड करने के लिए डेबिट/क्रेडिट एसएमएस भेजें या अपना खर्च लिखें (जैसे 'खाने पर 500 खर्च किए')।",
        "mandi_prompt": "आप किस फसल या कमोडिटी की कीमत देखना चाहते हैं?",
        "schemes_prompt": "आप किस योजना के बारे में खोजना चाहते हैं, या आपका व्यवसाय क्या है?",
        "jargon_prompt": "आप मुझसे कौन सा वित्तीय शब्द समझना चाहते हैं (जैसे, एसआईपी, ईएमआई, एनएवी)?",
        "scam_prompt": "कृपया वह संदिग्ध लिंक, वेबसाइट, संदेश या फोन नंबर पेस्ट करें जिसे आप सत्यापित करना चाहते हैं।",
        "profile_prompt": "आप कौन सी जानकारी अपडेट करना चाहते हैं? (जैसे 'भाषा बदलकर हिंदी करें', 'मेरी मासिक आय अपडेट करें')",
    },
    "mr": {
        "text": "खालील मेनूमधून एक वैशिष्ट्य निवडा:",
        "planner": "🎯 बचत उद्दिष्टे आणि नियोजन",
        "tracker": "💵 खर्च ट्रॅकर",
        "insights": "📊 खर्चाचे विश्लेषण",
        "mandi": "🌾 मंडी पिकांचे भाव",
        "schemes": "🏛️ सरकारी योजना",
        "jargon": "📖 वित्तीय संज्ञा स्पष्टीकरण",
        "scam": "🛡️ घोटाळा आणि फिशिंग तपासणी",
        "profile": "👤 प्रोफाइल अपडेट करा",
        "tracker_prompt": "कृपया खर्च नोंदवण्यासाठी डेबिट/क्रेडिट एसएमएस पाठवा किंवा तुमचा खर्च लिहा (उदा. 'जेवणावर 500 खर्च केले')।",
        "mandi_prompt": "तुम्हाला कोणत्या पिकाचे किंवा वस्तूचे भाव तपासायचे आहेत?",
        "schemes_prompt": "तुम्हाला कोणत्या योजनेबद्दल शोधायचे आहे, किंवा तुमचा व्यवसाय काय आहे?",
        "jargon_prompt": "तुम्हाला माझ्याकडून कोणती वित्तीय संज्ञा समजून घ्यायची आहे (उदा., एसआईपी, ईएमआई, एनएवी)?",
        "scam_prompt": "कृपया तुम्ही तपासू इच्छित असलेली संशयास्पद लिंक, वेबसाइट, संदेश किंवा फोन नंबर पेस्ट करा.",
        "profile_prompt": "तुम्ही कोणती माहिती अपडेट करू इच्छिता? (उदा. 'भाषा मराठी करा', 'माझे उत्पन्न अपडेट करा')",
    }
}


def get_menu_response(user):
    user_lang = lang(user)
    copy = MENU_COPY.get(user_lang, MENU_COPY["en"])

    buttons = [
        [{"text": copy["planner"], "data": "menu:planner"}],
        [{"text": copy["tracker"], "data": "menu:tracker"}],
        [{"text": copy["insights"], "data": "menu:insights"}],
        [{"text": copy["mandi"], "data": "menu:mandi"}],
        [{"text": copy["schemes"], "data": "menu:schemes"}],
        [{"text": copy["jargon"], "data": "menu:jargon"}],
        [{"text": copy["scam"], "data": "menu:scam"}],
        [{"text": copy["profile"], "data": "menu:profile"}],
    ]

    return {
        "reply": copy["text"],
        "buttons": buttons,
        "skipTranslation": True
    }


from users import save_user

def handle_menu_callback(user, action):
    # Clear any pending action since the user is starting a new flow from the menu
    user["pendingAction"] = ""
    save_user(user)

    user_lang = lang(user)
    copy = MENU_COPY.get(user_lang, MENU_COPY["en"])

    if action == "planner":
        from ai.agents.planner_agent import planner_agent
        return planner_agent(user, "")

    if action == "tracker":
        return {"reply": copy["tracker_prompt"], "buttons": [], "skipTranslation": True}

    if action == "insights":
        from ai.agents.insights_agent import insights_agent
        return insights_agent(user, "")

    if action == "mandi":
        return {"reply": copy["mandi_prompt"], "buttons": [], "skipTranslation": True}

    if action == "schemes":
        return {"reply": copy["schemes_prompt"], "buttons": [], "skipTranslation": True}

    if action == "jargon":
        return {"reply": copy["jargon_prompt"], "buttons": [], "skipTranslation": True}

    if action == "scam":
        return {"reply": copy["scam_prompt"], "buttons": [], "skipTranslation": True}

    if action == "profile":
        return {"reply": copy["profile_prompt"], "buttons": [], "skipTranslation": True}

    return get_menu_response(user)
