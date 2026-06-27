import json
import re

from ai.agents.insights_agent import insights_agent
from ai.agents.planner_agent import planner_agent
from ai.agents.scam_agent import scam_agent
from ai.agents.tracker_agent import tracker_agent
from ai.config.llm import llm
from ai.jargon import jargon_reply
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
    "jargon": jargon_reply,
    "scam": scam_agent,
}


def run_graph(user, message):
    route = route_intent(user, message)
    print(f"[GRAPH ROUTE] {route}")
    return ROUTES.get(route, planner_agent)(user, message)


def route_intent(user, message):
    text = str(message or "").lower()

    if user.get("pendingAction") in ["mandi_price", "other_goal_details"]:
        return "mandi" if user["pendingAction"] == "mandi_price" else "planner"
    if text.startswith("choose_goal:"):
        return "planner"
    if text.startswith("scheme:"):
        return "schemes"
    if has(text, [
        "where did my money go",
        "monthly spending",
        "spending insight",
        "spending insights",
        "money spent",
        "how much did i spend",
        "how much i spent",
        "this month spending",
        "this month expense",
        "kharch",
        "kitna kharch",
        "is mahine",
    ]):
        return "insights"
    if has(text, ["debited", "credited", "upi", "refno", "trf to", "a/c", "account debited", "account credited"]):
        return "tracker"
    if has(text, ["mandi", "market price", "price of", "rate of", "crop", "commodity", "bhaav", "bhav", "kaanda", "kanda", "kaande", "tamatar", "टमाटर", "कांदा", "कांदे", "भाव", "भाऊ", "दर", "किंमत"]):
        return "mandi"
    if has(text, ["change profile", "update profile", "edit profile", "change my", "update my"]):
        return "profile"
    if has(text, ["what is", "explain", "meaning of", "matlab", "kya hota hai", "nav", "sip", "emi", "credit score", "interest"]):
        return "jargon"
    if has(text, ["scheme", "schemes", "government scheme", "yojana", "yojna", "sarkari", "subsidy", "scholarship", "farmer scheme", "student scheme"]):
        return "schemes"
    if has(text, ["save", "saving", "goal", "plan", "emergency fund", "education fund"]):
        return "planner"
    if has(text, ["scam", "fraud", "fake", "phishing", "is this real", "is this safe", "check this", "suspicious", "fishy", "lottery", "won prize", "otp maang", "bank details maang", "verify this", "is this genuine"]):
        return "scam"

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
