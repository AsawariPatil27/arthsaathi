import os
import re
from urllib.parse import quote_plus

import requests

from db import schemes


def scheme_reply(user, message):
    if str(message).startswith("scheme:"):
        return scheme_details(user, str(message).split(":", 1)[1])

    matches = find_schemes(user, message)[:3]
    if not matches:
        return {"reply": "I could not find matching schemes right now. Try asking for farmer, student, health, or business schemes.", "buttons": []}

    lines = ["Top schemes that may fit you:"]
    buttons = []
    for i, scheme in enumerate(matches, 1):
        reason = quick_reason(user, scheme)
        lines.append(f"\n{i}. {scheme['scheme_name']}\nBenefit: {short(scheme.get('benefits'))}\nWhy: {reason}")
        buttons.append([{"text": f"View {i}", "data": f"scheme:{scheme['slug']}"}])

    return {"reply": "\n".join(lines), "buttons": buttons}


def scheme_details(user, slug):
    scheme = schemes.find_one({"slug": slug})
    if not scheme:
        return {"reply": "I could not find that scheme again. Please search schemes once more.", "buttons": []}

    videos = youtube_links(scheme["scheme_name"], user.get("language", "en"))
    reply = (
        f"{scheme['scheme_name']}\n\n"
        f"Why you may be eligible: {why_eligible(user, scheme)}\n\n"
        f"Benefit: {short(scheme.get('benefits'), 500)}\n\n"
        f"Documents: {short(scheme.get('documents'), 500)}\n\n"
        f"How to apply: {short(scheme.get('application'), 700)}\n\n"
        f"Videos:\n" + "\n".join(videos)
    )
    return {"reply": reply, "buttons": []}


def find_schemes(user, message):
    words = keywords(user, message)
    pattern = "|".join(re.escape(word) for word in words)
    query = {
        "$and": [
            {"level": "Central"},
            {
                "$or": [
                    {"scheme_name": {"$regex": pattern, "$options": "i"}},
                    {"details": {"$regex": pattern, "$options": "i"}},
                    {"eligibility": {"$regex": pattern, "$options": "i"}},
                    {"schemeCategory": {"$regex": pattern, "$options": "i"}},
                    {"tags": {"$regex": pattern, "$options": "i"}},
                ]
            },
        ]
    }
    rows = list(schemes.find(query).limit(150))
    return sorted(rows, key=lambda row: score(row, user, words), reverse=True)


def keywords(user, message):
    text = f"{message} {user.get('occupation', '')} {user.get('incomeType', '')}".lower()
    words = ["financial assistance", "welfare", "benefit", "support"]

    groups = {
        ("farmer", "agriculture", "crop", "kisan"): ["farmer", "farming", "agriculture", "crop", "kisan", "irrigation", "soil"],
        ("student", "education", "scholarship", "college", "school"): ["student", "education", "scholarship", "hostel", "college", "school"],
        ("health", "medical", "hospital", "insurance"): ["health", "medical", "hospital", "insurance", "treatment"],
        ("business", "loan", "startup", "msme", "self employed"): ["business", "entrepreneur", "loan", "msme", "startup", "self employment"],
        ("woman", "women", "girl", "female"): ["women", "girl", "mother", "widow"],
        ("variable", "low income", "poor"): ["income", "poor", "bpl", "financial assistance"],
    }
    for triggers, add in groups.items():
        if has(text, triggers):
            words += add

    return list(dict.fromkeys(words))


def score(scheme, user, words):
    text = " ".join(str(scheme.get(field, "")) for field in ["scheme_name", "details", "eligibility", "schemeCategory", "tags"]).lower()
    points = sum(3 for word in words if word.lower() in text)
    if user.get("occupation") == "farmer" and has(text, ["pm kisan", "pm-kisan", "kisan samman nidhi", "pradhan mantri kisan"]):
        points += 100
    points += 5 if user.get("occupation", "").lower() and user["occupation"].lower() in text else 0
    points += 2 if money(user.get("monthlyIncome")) and has(text, ["income", "poor", "bpl", "financial assistance"]) else 0
    return points


def quick_reason(user, scheme):
    text = " ".join(str(scheme.get(field, "")) for field in ["eligibility", "details", "tags", "schemeCategory"]).lower()
    if user.get("occupation") and user["occupation"].lower() in text:
        return f"Your profile says you are a {user['occupation']}, and this scheme mentions that group."
    return "This is a Central scheme and its category/keywords match your profile. Please check final eligibility before applying."


def why_eligible(user, scheme):
    return quick_reason(user, scheme)


def youtube_links(scheme_name, language):
    query = f"{scheme_name} apply kaise kare {language}"
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key:
        return [f"https://www.youtube.com/results?search_query={quote_plus(query)}"]

    try:
        data = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video", "maxResults": 3, "regionCode": "IN", "relevanceLanguage": language, "safeSearch": "moderate", "key": key},
            timeout=10,
        ).json()
        return [f"https://www.youtube.com/watch?v={item['id']['videoId']}" for item in data.get("items", [])]
    except Exception:
        return [f"https://www.youtube.com/results?search_query={quote_plus(query)}"]


def short(value, size=260):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:size] + ("..." if len(text) > size else "")


def has(text, words):
    return any(word in text for word in words)


def money(value):
    number = re.sub(r"[^0-9.]", "", str(value or "0"))
    return float(number or 0)
