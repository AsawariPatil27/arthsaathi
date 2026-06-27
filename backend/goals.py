from datetime import datetime

from pymongo import ReturnDocument

from db import goals


GOAL_TYPES = [
    "emergency_fund",
    "lean_season_reserve",
    "healthcare_fund",
    "education_fund",
    "other",
]


def goal_schema(telegram_id, goal_type, name, target_amount, monthly_saving=0, priority=5):
    return {
        "telegramId": str(telegram_id),
        "type": goal_type if goal_type in GOAL_TYPES else "other",
        "name": name,
        "targetAmount": round(float(target_amount or 0)),
        "currentAmount": 0,
        "monthlySaving": round(float(monthly_saving or 0)),
        "status": "active",
        "priority": priority,
        "createdAt": datetime.utcnow(),
    }


def save_goal(goal):
    goals.insert_one(goal)
    return goal


def user_goals(user):
    rows = goals.find({"telegramId": str(user["telegramId"]), "status": "active"}).sort("priority", 1)
    return [{**row, "_id": str(row["_id"])} for row in rows]


def add_goal_progress(user, goal_type, amount):
    result = goals.find_one_and_update(
        {"telegramId": str(user["telegramId"]), "type": goal_type, "status": "active"},
        {"$inc": {"currentAmount": float(amount or 0)}, "$set": {"updatedAt": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    if result:
        result["_id"] = str(result["_id"])
    return result


def create_goal(user, goal_data):
    goal_data["telegramId"] = str(user["telegramId"])
    goal_data["createdAt"] = datetime.utcnow()
    goal_data["updatedAt"] = datetime.utcnow()
    goal_data.setdefault("currentAmount", 0)
    goal_data.setdefault("status", "active")
    goals.update_one(
        {"telegramId": goal_data["telegramId"], "type": goal_data["type"], "name": goal_data["name"]},
        {"$set": goal_data},
        upsert=True,
    )
    return goal_data
