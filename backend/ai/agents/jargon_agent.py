import json
import logging
import re
from datetime import datetime

from ai.config.llm import llm
from db import conversations, goals, users


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are ArthSaathi, an AI Financial Literacy Coach.

Your purpose is to improve financial literacy.

Rules:
- Never recommend investments.
- Never recommend financial products.
- Never predict returns.
- Never say "buy", "sell", or "invest in".
- Explain in beginner-friendly language.
- Maximum 150 words.

Use the User Context only to personalize the analogy and example. Do not
recommend a goal, allocation, product, or saving amount. If asked "how much
should I save" or similar, explain the concept of goal-based saving generally.

Always include:
1. Simple definition
2. Real-life analogy based on the user's occupation and income pattern
3. Practical example
4. One common misconception
5. One follow-up learning suggestion

If the user asks to compare concepts, generate a comparison array.

If the user asks about financial products, explain purpose, how it works,
advantages, limitations, and important terms.

Do not hallucinate. If uncertain, say you don't know.

STRICT OUTPUT RULES:
- Return ONLY valid JSON.
- The first character of your response MUST be { and the last character MUST be }.
- Do NOT write markdown.
- Do NOT wrap the JSON in ```json fences.
- Do NOT add explanations before or after the JSON.
- Do NOT use comments, trailing commas, single quotes, or Python-style booleans.
- Every value must be a JSON string or JSON array.
- If you do not know something, put that uncertainty inside the relevant JSON string.
- Your response MUST parse with json.loads exactly as-is.

Return STRICTLY this JSON schema and no other keys:
{
  "title": "",
  "definition": "",
  "analogy": "",
  "example": "",
  "misconception": "",
  "comparison": [],
  "next_topics": []
}"""



def jargon_agent(user, message):
    telegram_id = str(user.get("telegramId", ""))
    profile = load_user_profile(user, telegram_id)

    if not profile:
        return reply("Welcome to ArthSaathi! Please complete your onboarding first so that I can tailor explanations to your background.")

    if not profile.get("profileCompleted"):
        return reply("It looks like your profile onboarding is incomplete. Please finish the registration steps first.")

    history = get_conversation_history(telegram_id)
    messages = build_prompt(profile, history, str(message or ""))

    try:
        raw_response = llm(messages)
        parsed = parse_response(raw_response)
    except Exception as error:
        logger.warning("Jargon agent failed for %s: %s", telegram_id, error)
        return reply("I could not prepare that explanation right now. Please ask again in simpler words.")

    save_conversation_turn(telegram_id, str(message or ""), json.dumps(parsed, ensure_ascii=False))
    return reply(format_response(parsed), next_topic_buttons(parsed))


def load_user_profile(user, telegram_id):
    if user and user.get("telegramId"):
        profile = dict(user)
    else:
        profile = users.find_one({"telegramId": telegram_id}) or {}

    profile.pop("_id", None)
    profile["pendingGoals"] = active_goals(telegram_id)
    return profile


def active_goals(telegram_id):
    rows = goals.find({"telegramId": str(telegram_id), "status": "active"}).sort("priority", 1)
    return [{k: v for k, v in row.items() if k != "_id"} for row in rows]


def build_prompt(profile, history, current_question):
    user_context = derive_user_context(profile)
    messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\nUser Context:\n{user_context}"}]
    messages.extend(history)
    messages.append({"role": "user", "content": current_question})
    return messages


def derive_user_context(profile):
    occupation = humanize(profile.get("occupation")) or "user"
    district = profile.get("district") or "their district"
    state = profile.get("state") or "their state"
    income_type = str(profile.get("incomeType") or "").lower()

    if income_type == "variable":
        harvest_income = money_text(profile.get("harvestIncome"), "seasonal income")
        lean_text = ""
        if profile.get("leanDurationMonths") or profile.get("leanMonthlyExpense"):
            duration = profile.get("leanDurationMonths") or "some"
            expense = money_text(profile.get("leanMonthlyExpense"), "usual expenses")
            lean_text = f", then faces a {duration}-month lean season with around {expense}/month expenses"
        income_pattern = f"{occupation} in {district}, {state}. Earns {harvest_income}{lean_text}."
    else:
        monthly_income = money_text(profile.get("monthlyIncome"), "monthly income")
        monthly_expense = money_text(profile.get("monthlyExpense"), "monthly expenses")
        income_pattern = f"{occupation} in {district}, {state}. Earns {monthly_income}/month and has {monthly_expense}/month expenses."

    active = sorted(profile.get("pendingGoals", []), key=lambda goal: goal.get("priority", 99))
    goal_parts = [f"{goal.get('name', 'Goal')} target {money_text(goal.get('targetAmount'), 'not set')}" for goal in active]
    goals_text = ", ".join(goal_parts) if goal_parts else "none specified"

    return f"{income_pattern} Active savings goals: {goals_text}."


def get_conversation_history(telegram_id, limit_turns=10):
    doc = conversations.find_one({"telegramId": str(telegram_id)}) or {}
    messages = doc.get("messages", [])
    return [
        {"role": item.get("role", "user"), "content": str(item.get("content", ""))}
        for item in messages[-(limit_turns * 2):]
        if item.get("content")
    ]


def save_conversation_turn(telegram_id, user_message, assistant_message, limit_turns=10):
    now = datetime.utcnow()
    conversations.update_one(
        {"telegramId": str(telegram_id)},
        {
            "$push": {"messages": {"$each": [
                {"role": "user", "content": user_message, "timestamp": now},
                {"role": "assistant", "content": assistant_message, "timestamp": now},
            ], "$slice": -(limit_turns * 2)}},
            "$set": {"updatedAt": now},
        },
        upsert=True,
    )


def parse_response(raw_content):
    cleaned = str(raw_content or "").strip()
    candidates = [cleaned]

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence:
        candidates.append(fence.group(1).strip())

    braces = re.search(r"(\{[\s\S]*\})", cleaned)
    if braces:
        candidates.append(braces.group(1).strip())

    for candidate in candidates:
        try:
            return normalize_response(json.loads(candidate))
        except Exception:
            continue

    raise ValueError("LLM response did not contain valid education JSON")


def normalize_response(data):
    comparison = data.get("comparison") or []
    next_topics = data.get("next_topics") or []
    return {
        "title": str(data.get("title") or "Financial concept"),
        "definition": str(data.get("definition") or ""),
        "analogy": str(data.get("analogy") or ""),
        "example": str(data.get("example") or ""),
        "misconception": str(data.get("misconception") or ""),
        "comparison": comparison if isinstance(comparison, list) else [],
        "next_topics": [str(topic) for topic in next_topics[:3]],
    }


def format_response(data):
    lines = [
        data["title"].upper(),
        "",
        data["definition"],
        "",
        f"Analogy: {data['analogy']}",
        "",
        f"Example: {data['example']}",
        "",
        f"Misconception: {data['misconception']}",
    ]

    if data["comparison"]:
        lines.extend(["", "Comparison:", "Aspect | Option A | Option B"])
        for item in data["comparison"]:
            if isinstance(item, dict):
                lines.append(f"{item.get('aspect', '')} | {item.get('option_a', '')} | {item.get('option_b', '')}")

    return "\n".join(line for line in lines if line is not None)


def next_topic_buttons(data):
    return [[{"text": topic, "data": f"Explain {topic}"}] for topic in data.get("next_topics", [])[:3]]


def money_text(value, fallback):
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"Rs {amount:,.0f}" if amount else fallback


def humanize(value):
    return str(value or "").replace("_", " ").strip()


def reply(text, buttons=None):
    return {"reply": text, "buttons": buttons or []}
