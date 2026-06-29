import csv
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

_TRUSTED_DOMAINS = {
    "sbi.co.in", "onlinesbi.sbi", "hdfcbank.com", "www.hdfcbank.com",
    "icicibank.com", "axisbank.com", "kotak.com", "bankofbaroda.in",
    "pnbindia.in", "canarabank.in", "unionbankofindia.co.in", "indianbank.in",
    "bankofindia.co.in", "mahindrafinance.com", "bajajfinserv.in",
    "liciindia.in", "licindia.in", "npci.org.in", "rbi.org.in",
    "sebi.gov.in", "irdai.gov.in", "pmkisan.gov.in", "myscheme.gov.in",
    "india.gov.in", "digilocker.gov.in",
}

_TRUSTED_TLDS = {".gov.in", ".nic.in", ".bank.in", ".edu.in", ".ac.in"}


def scam_agent(user, message):
    text = str(user.get("originalMessage") or message or "").strip()
    if not text:
        return {"reply": "Please send the suspicious message or text you want me to check for scams.", "buttons": []}

    urls = list(dict.fromkeys(re.findall(r"https?://[^\s<>\"'`,;)}\]]+", text, re.I)))
    domains = list(dict.fromkeys(urlparse(u).hostname.lower() for u in urls if urlparse(u).hostname))
    trusted = _is_trusted_domain(domains)

    signals = {
        "trusted_domain": trusted,
        "safe_browsing_flagged": [] if trusted else safe_browsing_matches(urls),
        "rbi_unregistered": False if trusted else _rbi_unregistered(text, domains),
        "domain_young": False,
        "suspicious_tld": False,
    }
    if not trusted:
        signals["domain_young"], signals["suspicious_tld"] = domain_risk_flags(domains)

    return {"reply": llm_verdict(text, signals), "buttons": []}


def llm_verdict(text, signals):
    signals_summary = "\n".join([
        f"- Trusted official domain: {signals['trusted_domain']}",
        f"- Google Safe Browsing flagged URLs: {signals['safe_browsing_flagged'] or 'none'}",
        f"- Sender not in RBI registered list: {signals['rbi_unregistered']}",
        f"- Domain registered very recently (<30 days): {signals['domain_young']}",
        f"- Suspicious domain extension (.xyz, .top, etc.): {signals['suspicious_tld']}",
    ])
    try:
        return llm([
            {"role": "system", "content": (
                "You are ArthSaathi's scam detection assistant for rural Indian users.\n"
                "You receive a message and external verification signals gathered from real APIs.\n"
                "Respond in plain text only — no JSON, no markdown.\n\n"
                "Your response must always include:\n"
                "1. Verdict: (No clear scam indicators / Suspicious / High Risk / Likely Scam)\n"
                "2. Risk Score: X/100\n"
                "3. Red Flags: bullet list of what raised concern (skip section if none)\n"
                "4. What to do: practical bullet list for the user\n"
                "5. Analysis: one cautious sentence about what you saw\n\n"
                "Signal weights when scoring:\n"
                "- Safe Browsing flagged: very high (35 pts)\n"
                "- RBI unregistered sender: high (20 pts)\n"
                "- Very new domain: high (20 pts)\n"
                "- Suspicious TLD: medium (10 pts)\n"
                "- Urgency / pressure language in message: medium (10 pts)\n"
                "- Asks for OTP or bank details: high (25 pts)\n"
                "- Fake prize or lottery offer: high (20 pts)\n\n"
                "Rules:\n"
                "- If trusted_domain=True, the source is likely official — say so clearly and keep score low.\n"
                "- Do NOT claim to verify if a URL is the real official site unless trusted_domain=True.\n"
                "- Keep advice simple for rural Indian users with low financial literacy.\n"
                "- Never use technical jargon."
            )},
            {"role": "user", "content": f"Message to check:\n{text}\n\nExternal signals:\n{signals_summary}"},
        ])
    except Exception as error:
        print(f"[SCAM LLM FAILED]: {error}")
        return "I could not analyze this message right now. When in doubt, do not click any links or share personal details."


def _is_trusted_domain(domains):
    return any(
        d in _TRUSTED_DOMAINS or any(d.endswith(tld) for tld in _TRUSTED_TLDS)
        for d in domains
    )


def _rbi_unregistered(text, domains):
    if not _RBI_ENTITIES:
        return False
    candidates = re.findall(r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\b', text)
    if not candidates:
        return False
    return not any(
        process.extractOne(c, _RBI_ENTITIES, scorer=fuzz.token_sort_ratio, score_cutoff=75)
        for c in candidates
    )


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
        return [m["threat"]["url"] for m in response.json().get("matches", [])]
    except Exception as error:
        print(f"[SAFE BROWSING FAILED]: {error}")
        return []


def domain_risk_flags(domains):
    domain_young = suspicious_tld = False
    for domain in domains:
        if any(domain.endswith(tld) for tld in _SUSPICIOUS_TLDS):
            suspicious_tld = True
        age, _ = _whois_age(domain)
        if age is not None and age < 30:
            domain_young = True
    return domain_young, suspicious_tld


def _whois_age(domain):
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
