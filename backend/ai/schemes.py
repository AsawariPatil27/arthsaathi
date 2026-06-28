import json
import os
import re
from urllib.parse import quote_plus

import requests


# Load schemes once at startup from the JSON file
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "schemes.json")

with open(_DATA_PATH, encoding="utf-8") as _f:
    _SCHEMES: list[dict] = json.load(_f)

_SCHEMES_BY_SLUG: dict[str, dict] = {s["slug"]: s for s in _SCHEMES}

OCCUPATION_TERMS = {
    "farmer": ["farmer", "farming", "agriculture", "crop", "kisan", "irrigation", "soil"],
    "teacher": ["teacher", "professor", "faculty", "school head", "education quality", "training"],
    "student": ["student", "scholarship", "education", "college", "school", "marksheet"],
    "healthcare_worker": ["healthcare worker", "health", "medical", "hospital", "clinic", "nurse", "doctor", "insurance"],
    "government_employee": ["government employee", "salaried", "employee", "epf", "pension", "retirement"],
    "private_employee": ["private employee", "salaried", "employee", "epf", "esic", "pension", "retirement"],
    "gig_worker": ["gig worker", "platform worker", "unorganised", "informal", "worker", "social security", "micro-loan"],
    "shop_owner": ["shop owner", "business", "entrepreneur", "loan", "msme", "startup", "self employment", "working capital"],
    "daily_wage": ["daily wage", "worker", "income", "poor", "bpl", "financial assistance", "livelihood"],
    "freelancer": ["freelancer", "self employed", "business", "skill", "pension", "loan", "entrepreneur"],
    "homemaker": ["homemaker", "women", "woman", "girl", "mother", "shg", "self help group", "livelihood"],
}

REQUEST_TERMS = {
    "farmer": OCCUPATION_TERMS["farmer"],
    "kisan": OCCUPATION_TERMS["farmer"],
    "student": OCCUPATION_TERMS["student"],
    "scholarship": OCCUPATION_TERMS["student"],
    "teacher": OCCUPATION_TERMS["teacher"],
    "health": OCCUPATION_TERMS["healthcare_worker"],
    "medical": OCCUPATION_TERMS["healthcare_worker"],
    "business": OCCUPATION_TERMS["shop_owner"],
    "loan": OCCUPATION_TERMS["shop_owner"],
    "gig": OCCUPATION_TERMS["gig_worker"],
    "worker": OCCUPATION_TERMS["gig_worker"],
    "women": OCCUPATION_TERMS["homemaker"],
    "woman": OCCUPATION_TERMS["homemaker"],
}

FARMER_ONLY_TERMS = ["pm kisan", "pm-kisan", "kisan credit", "fasal bima", "crop insurance", "solar pump", "soil health", "krishi", "irrigation"]
TEACHER_ONLY_TERMS = ["teacher", "faculty", "professor"]
STUDENT_ONLY_TERMS = ["student", "scholarship", "marksheet"]
UNORGANISED_WORKER_TERMS = ["unorganised", "unorganized", "gig worker", "platform worker", "street vendor", "daily wage"]

FLAGSHIP_BOOSTS = {
    "farmer": ["pm-kisan", "kcc", "pmfby"],
    "teacher": ["nishtha", "diksha", "national-awards-to-teachers"],
    "student": ["pm-yasasvi", "csss", "post-matric-scholarship"],
    "government_employee": ["nps", "epf"],
    "private_employee": ["epf", "esic", "nps"],
    "gig_worker": ["e-shram", "pm-sym", "pm-svanidhi"],
    "shop_owner": ["pmmy-mudra", "pmegp", "stand-up-india"],
    "daily_wage": ["e-shram", "pm-sym", "day-nulm"],
    "freelancer": ["pmmy-mudra", "pmegp", "nps"],
    "homemaker": ["day-nrlm", "stand-up-india", "sukanya-samriddhi-yojana"],
    "healthcare_worker": ["abdm", "ab-pmjay", "esic"],
}


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
    scheme = _SCHEMES_BY_SLUG.get(slug)
    if not scheme:
        return {"reply": "I could not find that scheme again. Please search schemes once more.", "buttons": []}

    videos = youtube_links(scheme["scheme_name"], user.get("language", "en"))
    link = scheme.get("applicationLink", "")
    apply_line = f"\n\nApply here: {link}" if link else ""
    reply = (
        f"{scheme['scheme_name']}\n\n"
        f"Why you may be eligible: {why_eligible(user, scheme)}\n\n"
        f"Benefit: {short(scheme.get('benefits'), 500)}\n\n"
        f"Documents: {short(scheme.get('documents'), 500)}\n\n"
        f"How to apply: {short(scheme.get('application'), 700)}"
        f"{apply_line}\n\n"
        f"Videos:\n" + "\n".join(videos)
    )
    return {"reply": reply, "buttons": []}


def find_schemes(user, message):
    occupation = str(user.get("occupation") or "").lower()
    if occupation == "other" and not has_explicit_scheme_group(message):
        return []

    terms = match_terms(user, message)
    matches = [(scheme_score(scheme, terms, occupation, message), scheme) for scheme in _SCHEMES]
    return [scheme for points, scheme in sorted(matches, key=lambda row: row[0], reverse=True) if points > 0][:3]


def has_explicit_scheme_group(message):
    text = str(message or "").lower()
    groups = [
        "farmer", "kisan", "agriculture", "crop",
        "teacher", "professor", "faculty",
        "student", "scholarship", "education",
        "health", "medical", "insurance",
        "business", "loan", "startup", "msme", "shop",
        "gig", "daily wage", "freelancer", "vendor", "worker",
        "women", "woman", "homemaker",
    ]
    return has(text, groups)


def match_terms(user, message):
    occupation = str(user.get("occupation") or "").lower()
    request = str(message or "").lower()
    terms = list(OCCUPATION_TERMS.get(occupation, []))

    for trigger, add_terms in REQUEST_TERMS.items():
        if trigger in request:
            terms.extend(add_terms)

    return list(dict.fromkeys(term.lower() for term in terms if term))


def scheme_score(scheme, terms, occupation, message=""):
    text = scheme_text(scheme)
    points = sum(5 for term in terms if term in text)
    request_words = re.findall(r"[a-zA-Z][a-zA-Z-]+", str(message or "").lower())
    points += sum(1 for word in request_words if word in text)

    if occupation != "farmer" and not has_explicit_farmer_request(message) and has(text, FARMER_ONLY_TERMS):
        points -= 80
    if occupation not in ["teacher", "professor"] and has(text, TEACHER_ONLY_TERMS):
        points -= 30
    if occupation != "student" and has(text, STUDENT_ONLY_TERMS):
        points -= 25
    if occupation in ["government_employee", "private_employee"] and has(text, UNORGANISED_WORKER_TERMS):
        points -= 35
    if scheme.get("slug") in FLAGSHIP_BOOSTS.get(occupation, []):
        points += 25

    return points


def scheme_text(scheme):
    return " ".join(
        str(scheme.get(field, ""))
        for field in ["scheme_name", "details", "eligibility", "schemeCategory", "tags"]
    ).lower()


def has_explicit_farmer_request(message):
    return has(str(message or "").lower(), ["farmer", "kisan", "agriculture", "crop", "farming"])


def quick_reason(user, scheme):
    text = " ".join(str(scheme.get(field, "")) for field in ["eligibility", "details", "tags", "schemeCategory"]).lower()
    occupation = str(user.get("occupation") or "").replace("_", " ")
    if occupation and occupation.lower() in text:
        return f"Your profile says you are a {occupation}, and this scheme mentions that group."
    if occupation:
        return f"This scheme's keywords match your {occupation} profile or request. Please check final eligibility before applying."
    return "This scheme's keywords match your request. Please check final eligibility before applying."


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
