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


_SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".buzz", ".club", ".loan", ".work", ".click", ".link",
    ".online", ".site", ".icu", ".fun", ".tk", ".ml", ".ga", ".cf", ".gq",
}

# Known legitimate Indian financial institution domains — never flag these
_TRUSTED_DOMAINS = {
    "sbi.co.in", "onlinesbi.sbi", "hdfcbank.com", "www.hdfcbank.com",
    "hdfc.bank.in", "www.hdfc.bank.in", "icicibank.com", "axisbank.com",
    "kotak.com", "bankofbaroda.in", "pnbindia.in", "canarabank.in",
    "unionbankofindia.co.in", "indianbank.in", "bankofindia.co.in",
    "mahindrafinance.com", "bajajfinserv.in", "liciindia.in", "licindia.in",
    "npci.org.in", "rbi.org.in", "sebi.gov.in", "irdai.gov.in",
    "pmkisan.gov.in", "myscheme.gov.in", "india.gov.in", "digilocker.gov.in",
}

_TRUSTED_TLDS = {".gov.in", ".nic.in", ".bank.in", ".edu.in", ".ac.in"}


def _is_trusted_domain(domains):
    """Return True if any domain is in the whitelist or has a trusted TLD."""
    for d in domains:
        if d in _TRUSTED_DOMAINS:
            return True
        if any(d.endswith(tld) for tld in _TRUSTED_TLDS):
            return True
    return False


def scam_agent(user, message):
    # Always use the original untranslated message for URL/text extraction.
    # to_english() can strip URLs, so we preserve them via originalMessage.
    text = str(user.get("originalMessage") or message or "").strip()
    if not text:
        return {"reply": "Please send the suspicious message or text you want me to check for scams.", "buttons": []}

    urls = list(dict.fromkeys(re.findall(r"https?://[^\s<>\"'`,;)}\]]+", text, re.I)))
    domains = list(dict.fromkeys(urlparse(url).hostname.lower() for url in urls if urlparse(url).hostname))
    trusted = _is_trusted_domain(domains)

    llm_data = extract_visible_risk_signals(text)
    sb_unsafe = [] if trusted else safe_browsing_matches(urls)
    rbi_flag = False if trusted else company_not_in_rbi(llm_data.get("companies", []), domains)
    domain_young, suspicious_tld = (False, False) if trusted else domain_risk_flags(domains)

    checks = [
        (bool(sb_unsafe),                                              35, "URL flagged by Google Safe Browsing"),
        (rbi_flag,                                                     20, "Sender company not found in RBI registered list"),
        (domain_young,                                                 20, "Very new domain (registered recently)"),
        (suspicious_tld,                                               10, "Suspicious TLD extension"),
        (llm_data.get("urgency"),                                      10, "Urgency language detected"),
        (llm_data.get("pressure_language"),                            10, "Pressure / threat tactics"),
        (llm_data.get("asks_otp"),                                     25, "Asks for OTP"),
        (llm_data.get("asks_bank_details"),                            20, "Asks for bank/card details"),
        (llm_data.get("fake_offer") or llm_data.get("reward_scam"),   20, "Fake reward or prize offer"),
        (llm_data.get("phishing"),                                     15, "Phishing indicators"),
        (llm_data.get("asks_for_money"),                               15, "Asks you to send money"),
    ]

    score = min(sum(weight for condition, weight, _ in checks if condition), 100)
    reasons = [desc for condition, _, desc in checks if condition]
    verdict, summary = verdict_text(score, reasons)
    actions = recommended_actions(score)

    lines = [
        "Scam Detection Result",
        "",
        f"Verdict: {verdict}",
        f"Risk Score: {score}/100",
        "",
        summary,
    ]
    if reasons:
        lines += ["", "Red Flags:"] + [f"- {reason}" for reason in reasons]
    if actions:
        lines += ["", "What to do:"] + [f"- {action}" for action in actions]

    if score > 20 and llm_data.get("reason"):
        lines += ["", f"Analysis: {llm_data['reason']}"]
    elif score <= 20 and urls:
        lines += [
            "",
            "Note: I cannot guarantee this link is official or safe. I only found no strong scam indicators in the message.",
        ]

    return {"reply": "\n".join(lines), "buttons": []}


def extract_visible_risk_signals(text):
    try:
        raw = llm([
            {
                "role": "system",
                "content": (
                    "You are a scam risk signal extractor. Return ONLY JSON.\n"
                    "Do not verify whether a URL is official, real, fake, safe, or unsafe.\n"
                    "Do not claim the correct official domain of any company.\n"
                    "Only extract visible scam indicators from the message text itself.\n"
                    "If there are no clear visible scam indicators, set phishing=false and "
                    "reason=\"No clear scam indicators visible in the message text.\"\n"
                    "{\"urgency\":bool,\"pressure_language\":bool,\"asks_for_money\":bool,"
                    "\"asks_bank_details\":bool,\"asks_otp\":bool,\"fake_offer\":bool,"
                    "\"reward_scam\":bool,\"phishing\":bool,\"companies\":[\"names\"],"
                    "\"reason\":\"one cautious line about visible indicators only\"}"
                ),
            },
            {"role": "user", "content": text},
        ])
        if "```" in raw:
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        match = re.search(r"\{.*\}", raw, re.S)
        return json.loads(match.group(0) if match else "{}")
    except Exception as error:
        print(f"[LLM FAILED]: {error}")
        return {}


def safe_browsing_matches(urls):
    api_key = os.getenv("GOOGLE_SAFE_BROWSING_KEY", "")
    if not urls or not api_key:
        return []
    try:
        response = requests.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find",
            params={"key": api_key},
            json={
                "client": {"clientId": "arthsaathi", "clientVersion": "1.0.0"},
                "threatInfo": {
                    "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": url} for url in urls],
                },
            },
            timeout=15,
        )
        return [match["threat"]["url"] for match in response.json().get("matches", [])]
    except Exception as error:
        print(f"[SAFE BROWSING FAILED]: {error}")
        return []


def company_not_in_rbi(companies, domains):
    """Only flag if LLM extracted company names AND none match RBI list AND domain isn't trusted."""
    if not companies or not _RBI_ENTITIES:
        return False
    matches = [process.extractOne(c, _RBI_ENTITIES, scorer=fuzz.token_sort_ratio, score_cutoff=75) for c in companies]
    return not any(matches)


def domain_risk_flags(domains):
    domain_young = False
    suspicious_tld = False
    for domain in domains:
        if any(domain.endswith(tld) for tld in _SUSPICIOUS_TLDS):
            suspicious_tld = True
        age, _ = get_whois_age(domain)
        if age is not None and age < 30:
            domain_young = True
    return domain_young, suspicious_tld


def get_whois_age(domain):
    try:
        data = whois.whois(domain)
        created_at = data.creation_date[0] if isinstance(data.creation_date, list) else data.creation_date
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if created_at:
            created_at = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
            return (datetime.now(timezone.utc) - created_at).days, data.registrar
    except Exception as error:
        print(f"[WHOIS FAILED] {domain}: {error}")
    return None, None


def verdict_text(score, reasons):
    if score <= 20:
        return (
            "No clear scam indicators found",
            "I did not find strong scam indicators, but I cannot fully verify that a website or sender is official. Check the URL manually before sharing any details.",
        )
    if score <= 50:
        return "Suspicious", f"The message has some suspicious characteristics ({len(reasons)} indicator(s) detected). Exercise caution."
    if score <= 75:
        return "High Risk", f"The message shows multiple high-risk scam indicators ({len(reasons)} detected). Treat with extreme caution."
    return "Likely Scam", f"The message contains strong scam/phishing indicators ({len(reasons)} detected). This is very likely a scam."


def recommended_actions(score):
    action_thresholds = [
        (20, "Do not click any links in the message."),
        (30, "Do not share personal or financial information."),
        (40, "Never share OTP, PIN, or CVV with anyone."),
        (50, "Block the sender immediately."),
        (60, "Report to your bank if financial details were shared."),
        (70, "File a complaint at https://cybercrime.gov.in"),
        (80, "Report to the National Cyber Crime Helpline: 1930"),
    ]
    actions = [action for threshold, action in action_thresholds if score > threshold]
    if actions:
        return actions
    return ["Open links only after checking the exact domain yourself. Do not share OTP, PIN, CVV, or passwords."]
