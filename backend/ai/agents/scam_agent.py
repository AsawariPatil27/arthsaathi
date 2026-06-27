import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
import whois
from rapidfuzz import fuzz, process
from ai.config.llm import llm

_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "rbi_registered.csv"
_RBI_ENTITIES = []
if _CSV_PATH.exists():
    with open(_CSV_PATH, newline="", encoding="utf-8") as fh:
        _RBI_ENTITIES = [row["entity_name"].strip() for row in csv.DictReader(fh) if row.get("entity_name")]

_SUSPICIOUS_TLDS = {".xyz", ".top", ".buzz", ".club", ".loan", ".work", ".click", ".link", ".online", ".site", ".icu", ".fun", ".tk", ".ml", ".ga", ".cf", ".gq"}

def _get_whois_age(domain):
    try:
        w = whois.whois(domain)
        d = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        if d:
            dt = d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
            return (datetime.now(timezone.utc) - dt).days, w.registrar
    except Exception as e:
        print(f"[WHOIS FAILED] {domain}: {e}")
    return None, None

def scam_agent(user, message):
    text = str(message or "").strip()
    if not text:
        return {"reply": "Please send the suspicious message or text you want me to check for scams.", "buttons": []}

    # 1. Extraction (URLs & Companies)
    urls = list(dict.fromkeys(re.findall(r"https?://[^\s<>\"'`,;)}\]]+", text, re.I)))
    domains = list(dict.fromkeys(urlparse(u).hostname.lower() for u in urls if urlparse(u).hostname))

    # 2. LLM Analysis
    try:
        raw = llm([
            {"role": "system", "content": "You are a scam analyst. Return ONLY JSON (no markdown):\n"
                       "{\"urgency\":bool,\"pressure_language\":bool,\"asks_for_money\":bool,\"asks_bank_details\":bool,"
                       "\"asks_otp\":bool,\"fake_offer\":bool,\"reward_scam\":bool,\"phishing\":bool,"
                       "\"companies\":[\"names\"],\"reason\":\"one line\"}"},
            {"role": "user", "content": text}
        ])
        if "```" in raw:
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        llm_data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    except Exception as e:
        print(f"[LLM FAILED]: {e}")
        llm_data = {}

    # 3. Google Safe Browsing
    sb_unsafe = []
    api_key = os.getenv("GOOGLE_SAFE_BROWSING_KEY", "")
    if urls and api_key:
        try:
            resp = requests.post("https://safebrowsing.googleapis.com/v4/threatMatches:find", params={"key": api_key}, json={
                "client": {"clientId": "arthsaathi", "clientVersion": "1.0.0"},
                "threatInfo": {
                    "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                    "platformTypes": ["ANY_PLATFORM"], "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": u} for u in urls]
                }
            }, timeout=15)
            sb_unsafe = [m["threat"]["url"] for m in resp.json().get("matches", [])]
        except Exception as e:
            print(f"[SAFE BROWSING FAILED]: {e}")

    # 4. RBI Fuzzy Verification
    rbi_unregistered = False
    companies = llm_data.get("companies", [])
    if companies and _RBI_ENTITIES:
        matches = [process.extractOne(c, _RBI_ENTITIES, scorer=fuzz.token_sort_ratio, score_cutoff=75) for c in companies]
        if not any(matches):
            rbi_unregistered = True

    # 5. Domain Intel / WHOIS
    domain_young, suspicious_tld = False, False
    for d in domains:
        if any(d.endswith(tld) for tld in _SUSPICIOUS_TLDS):
            suspicious_tld = True
        age, registrar = _get_whois_age(d)
        if age is not None and age < 30:
            domain_young = True

    # 6. Scoring & Red Flags (Weights from scorer.py)
    checks = [
        (bool(sb_unsafe), 35, "Unsafe URL detected"),
        (rbi_unregistered, 25, "Company not RBI-registered"),
        (domain_young, 20, "Very new domain detected"),
        (suspicious_tld, 10, "Suspicious TLD extension"),
        (llm_data.get("urgency"), 10, "Urgency language"),
        (llm_data.get("pressure_language"), 10, "Pressure tactics"),
        (llm_data.get("asks_otp"), 25, "OTP request"),
        (llm_data.get("asks_bank_details"), 20, "Bank details request"),
        (llm_data.get("fake_offer") or llm_data.get("reward_scam"), 20, "Fake reward / offer"),
        (llm_data.get("phishing"), 15, "Phishing indicators"),
        (llm_data.get("asks_for_money"), 15, "Asks for money")
    ]
    
    score = min(sum(weight for condition, weight, _ in checks if condition), 100)
    reasons = [desc for condition, _, desc in checks if condition]

    # 7. Verdicts & Actions (From verdict.py)
    verdict = "Safe ✅" if score <= 20 else "Suspicious ⚠️" if score <= 50 else "High Risk 🔴" if score <= 75 else "Likely Scam 🚨"
    summary = ("The message appears safe. No significant scam indicators were found." if score <= 20 else
               f"The message has some suspicious characteristics ({len(reasons)} indicator(s) detected). Exercise caution." if score <= 50 else
               f"The message shows multiple high-risk scam indicators ({len(reasons)} detected). Treat with extreme caution." if score <= 75 else
               f"The message contains strong scam/phishing indicators ({len(reasons)} detected). This is very likely a scam.")

    action_thresholds = [
        (20, "Do not click any links in the message."),
        (30, "Do not share personal or financial information."),
        (40, "Never share OTP, PIN, or CVV with anyone."),
        (50, "Block the sender immediately."),
        (60, "Report to your bank if financial details were shared."),
        (70, "File a complaint at https://cybercrime.gov.in"),
        (80, "Report to the National Cyber Crime Helpline: 1930")
    ]
    actions = [act for threshold, act in action_thresholds if score > threshold] or ["No immediate action needed."]

    # 8. Formatting Reply
    lines = [
        "🔍 Scam Detection Result", "",
        f"Verdict: {verdict}",
        f"Risk Score: {score}/100", "",
        summary
    ]
    if reasons:
        lines += ["\nRed Flags:"] + [f"  • {r}" for r in reasons]
    if actions and actions[0] != "No immediate action needed.":
        lines += ["\nWhat to do:"] + [f"  • {a}" for a in actions]
    if llm_data.get("reason"):
        lines += ["", f"Analysis: {llm_data['reason']}"]

    return {"reply": "\n".join(lines), "buttons": []}
