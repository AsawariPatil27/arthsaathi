import os
from datetime import datetime
from uuid import uuid4

from db import transactions


def insights_agent(user, message):
    data = monthly_spending(user["telegramId"])
    if not data:
        return {"reply": "No spending found for this month yet.", "buttons": []}

    reply = summary(data)
    if user.get("interactionMode") == "voice":
        return {"reply": reply, "buttons": []}

    return {"reply": reply, "buttons": [], "imagePath": chart(data)}


def monthly_spending(telegram_id):
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = transactions.aggregate([
        {"$match": {"telegramId": str(telegram_id), "type": "debit", "createdAt": {"$gte": start}}},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}},
    ])
    return {row["_id"] or "other": round(row["total"], 2) for row in rows}


def summary(data):
    total = sum(data.values())
    lines = [f"This month you spent Rs {total:.2f}."]
    lines += [f"{category}: Rs {amount:.2f}" for category, amount in data.items()]
    return "\n".join(lines)


def chart(data):
    import matplotlib.pyplot as plt

    os.makedirs("charts", exist_ok=True)
    path = os.path.abspath(os.path.join("charts", f"{uuid4().hex}.png"))

    plt.figure(figsize=(5, 5))
    plt.pie(data.values(), labels=data.keys(), autopct="%1.0f%%")
    plt.title("This Month's Spending")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path
