import json
import re

from ai.agents.insights_agent import insights_agent
from ai.agents.jargon_agent import jargon_agent
from ai.agents.planner_agent import planner_agent
from ai.agents.scam_agent import scam_agent
from ai.agents.tracker_agent import tracker_agent
from ai.config.llm import llm
from ai.mandi_prices import mandi_price_reply
from ai.profile_update import update_profile_from_message
from ai.schemes import scheme_reply


ROUTES = {
    "planner": planner_agent,
    "tracker": tracker_agent,
    "insights": insights_agent,
    "mandi": mandi_price_reply,
    "profile": update_profile_from_message,
    "schemes": scheme_reply,
    "jargon": jargon_agent,
    "scam": scam_agent,
}


def run_graph(user, message):
    route = route_intent(user, message)
    print(f"[GRAPH ROUTE] {route}")
    return ROUTES.get(route, planner_agent)(user, message)


def route_intent(user, message):
    text = str(message or "").lower()

    # ── Machine callbacks always go direct ────────────────────────────────
    if text.startswith(("choose_goal:", "confirm_goal:", "edit_goal:")):
        return "planner"
    if text.startswith("scheme:"):
        return "schemes"

    # ── Unambiguous signal checks FIRST — these must never be hijacked ────
    # Scam: URL present with safety keywords OR explicit scam words
    if re.search(r"https?://", text) or has(text, [
        "scam", "fraud", "fake", "phishing", "suspicious", "fishy", "lottery",
        "won prize", "you have won", "is this real", "is this safe",
        "is this link", "is this url", "verify this", "check this",
        "otp maang", "bank details maang",
    ]):
        return "scam"

    # Tracker: bank/UPI SMS — very specific keywords
    if has(text, ["debited", "credited", "upi", "refno", "trf to", "a/c",
                  "account debited", "account credited"]):
        return "tracker"

    # Mandi: crop/commodity price — also very specific
    if has(text, ["mandi", "market price", "price of", "rate of", "crop",
                  "commodity", "bhaav", "bhav", "kaanda", "kanda", "tamatar",
                  "टमाटर", "कांदा", "कांदे", "भाव", "भाऊ", "दर", "किंमत"]):
        return "mandi"

    # ── PendingAction routing — only AFTER clear signals are ruled out ────
    planner_pending_actions = {
        "other_goal_details", "ask_monthly_expense_for_goal_plan",
        "other_goal_name", "other_goal_amount", "other_goal_duration",
        "edit_goal_amount", "edit_goal_duration",
        "ask_this_month_income_for_goal_plan",
        "ask_farmer_lean_season_for_goal_plan",
    }
    pending = user.get("pendingAction") or ""
    if pending == "mandi_price":
        return "mandi"
    if pending in planner_pending_actions:
        return "planner"

    # ── Remaining content checks ───────────────────────────────────────────
    if has(text, ["where did my money go", "monthly spending", "spending insight",
                  "money spent", "how much did i spend", "how much i spent",
                  "this month spending", "this month expense",
                  "kharch", "kitna kharch", "is mahine"]):
        return "insights"
    if has(text, ["change profile", "update profile", "edit profile",
                  "change my", "update my"]):
        return "profile"
    if has(text, ["what is", "explain", "meaning of", "matlab", "kya hota hai",
                  "nav", "sip", "emi", "credit score", "interest"]):
        return "jargon"
    if has(text, ["scheme", "schemes", "government scheme", "yojana", "yojna",
                  "sarkari", "subsidy", "scholarship", "farmer scheme", "student scheme"]):
        return "schemes"
    if has(text, ["save", "saving", "goal", "plan", "emergency fund", "education fund"]):
        return "planner"

    return llm_route(message)


def llm_route(message):
    try:
        raw = llm([
            {
                "role": "system",
                "content": (
                    "You are ArthSaathi's intent router. Return only valid JSON. No markdown. "
                    "Output exactly one of: {\"route\":\"planner\"}, {\"route\":\"tracker\"}, "
                    "{\"route\":\"insights\"}, {\"route\":\"mandi\"}, {\"route\":\"profile\"}, {\"route\":\"schemes\"}, {\"route\":\"jargon\"}, {\"route\":\"scam\"}. "
                    "planner: savings plans, goals, emergency fund, education fund, saved amount. "
                    "tracker: bank SMS, debit, credit, UPI, transaction, expense entry. "
                    "insights: where money went, monthly spending, spending by category. "
                    "mandi: crop/commodity/market/mandi prices, bhaav, rate, onion/kaanda/tomato. "
                    "profile: change/update/edit profile fields like income, expense, language, district. "
                    "schemes: government schemes, yojana/yojna, sarkari benefits, subsidy, scholarship, farmer/student benefits. "
                    "jargon: explain financial words like SIP, NAV, EMI, credit score, interest, insurance terms. "
                    "scam: check if a message is a scam/fraud/phishing, verify suspicious messages, lottery wins, OTP/bank detail requests."
                ),
            },
            {"role": "user", "content": str(message)},
        ])
        m = re.search(r"\{[^{}]*\}", raw, re.S)
        return json.loads(m.group(0) if m else "{}").get("route", "planner")
    except Exception as error:
        print(f"[GRAPH LLM ROUTE FALLBACK] {error}")
        return "planner"


def has(text, words):
    return any(word in text for word in words)
