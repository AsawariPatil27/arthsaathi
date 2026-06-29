import json
import re

from ai.agents.insights_agent import insights_agent
from ai.agents.jargon_agent import jargon_agent
from ai.agents.planner_agent import planner_agent
from ai.agents.scam_agent import scam_agent
from ai.agents.tracker_agent import tracker_agent
from ai.config.llm import llm
from ai.mandi_prices import mandi_price_reply
from db import conversations
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

VALID_ROUTES = frozenset(ROUTES)

PLANNER_PENDING_ACTIONS = frozenset({
    "ask_monthly_expense_for_goal_plan",
    "ask_this_month_income_for_goal_plan",
    "ask_farmer_lean_season_for_goal_plan",
    "other_goal_name", "other_goal_amount", "other_goal_duration",
    "edit_goal_amount", "edit_goal_duration",
})

ROUTER_PROMPT = """You are ArthSaathi's intent router for a rural Indian financial assistant.
Classify the user message into exactly one route and return ONLY valid JSON — no explanation, no markdown.

ROUTES and when to use each:
- planner   : User wants to save money, set a savings goal, build an emergency/education/wedding fund, or asks about how much they have saved.
- tracker   : A bank or UPI SMS forwarded by the user, OR the user reporting a specific past transaction (debited, credited, money sent/received, UPI ref, A/C no, REFNO).
- insights  : User asking where their money went, monthly spending summary, or expense breakdown by category. E.g. "how much did I spend", "kharch kitna hua", "paise kahan gaye", "is mahine kitna gaya".
- mandi     : User asking for a crop or commodity market price. E.g. onion/kaanda/kanda price, wheat/gehu rate, tamatar bhav, mandi price. Includes Hindi and Marathi crop names.
- profile   : User wants to update or change their own profile info — income, expenses, language, district, name, or occupation.
- schemes   : User asking about government schemes, yojana, subsidies, scholarships, or benefits for farmers/students/women.
- jargon    : User asking to explain a financial term or concept. E.g. "what is SIP", "explain EMI", "kya hota hai credit score", "what does NAV mean".
- scam      : User sharing a suspicious message or link, asking if something is fraud/fake/lottery/scam, or worried about OTP or bank detail requests. Any http/https URL is a strong scam signal.

RULES:
1. Users are rural Indians — messages may be in Hindi, Marathi, Hinglish, or mixed. Understand them semantically, not just by keywords.
2. If a URL (http or https) appears in the message, route to scam — unless it is clearly an official government domain (.gov.in / nic.in).
3. Distinguish tracker (user reporting a PAST transaction) from planner (user PLANNING future savings).
4. If a message contains "what is" or "explain" or "kya hai" before a financial term, it is jargon — not schemes or planner.
5. If a "Previous message" is provided and the current message is a follow-up (e.g. "I didn't understand", "explain again", "give example") with no new topic, route to the same category as the previous message.
6. Default to planner if the intent is genuinely unclear.

Return ONLY this JSON and nothing else:
{"route": "<planner|tracker|insights|mandi|profile|schemes|jargon|scam>"}"""


def run_graph(user, message):
    route = route_intent(user, message)
    print(f"[GRAPH ROUTE] {route}")
    return ROUTES.get(route, planner_agent)(user, message)


def route_intent(user, message):
    text = str(message or "").lower()

    # Machine-generated callbacks — not natural language, bypass LLM
    if text.startswith(("choose_goal:", "confirm_goal:", "edit_goal:")):
        return "planner"
    if text.startswith("scheme:"):
        return "schemes"

    # Server-side pending state — LLM has no visibility into this
    pending = user.get("pendingAction") or ""
    if pending == "mandi_price":
        return "mandi"
    if pending in PLANNER_PENDING_ACTIONS:
        return "planner"

    last = _last_user_topic(user.get("telegramId", ""))
    return llm_route(message, context=f"Previous message: {last}" if last else "")


def _last_user_topic(telegram_id):
    try:
        doc = conversations.find_one({"telegramId": str(telegram_id)}) or {}
        for msg in reversed(doc.get("messages", [])):
            if msg.get("role") == "user":
                return str(msg.get("content", ""))
    except Exception:
        pass
    return ""


def llm_route(message, context=""):
    system = ROUTER_PROMPT + (f"\n\nContext: {context}" if context else "")
    try:
        raw = llm([
            {"role": "system", "content": system},
            {"role": "user", "content": str(message)},
        ])
        m = re.search(r"\{[^{}]*\}", raw, re.S)
        route = json.loads(m.group(0) if m else "{}").get("route", "planner")
        return route if route in VALID_ROUTES else "planner"
    except Exception as error:
        print(f"[GRAPH LLM ROUTE FALLBACK] {error}")
        return "planner"
