from db import users


def default_user(telegram_id):
    return {
        "telegramId": str(telegram_id),
        "interactionMode": "",
        "language": "",
        "currentStep": "start",
        "profileCompleted": False,
        "incomeType": "",
        "occupation": "",
        "monthlyIncome": 0,
        "thisMonthIncome": 0,
        "lowestMonthIncome": 0,
        "monthlyExpense": 0,
        "familySize": 0,
        "earningMembers": 0,
        "hasInsurance": False,
        "hasEmergencyFund": False,
        "emergencyFundAmount": 0,
        "state": "",
        "district": "",
        # Farmer-specific
        "harvestIncome": 0,
        "harvestMonth": "",
        "leanDurationMonths": 0,
        "leanMonthlyExpense": 0,
        # Planner state
        "pendingGoal": None,
        "pendingGoals": [],
        "pendingAction": "",
    }


def save_user(user):
    users.update_one({"telegramId": user["telegramId"]}, {"$set": user}, upsert=True)
    return user


def get_or_create_user(telegram_id, username="", first_name=""):
    tid = str(telegram_id)
    user = users.find_one({"telegramId": tid})
    if not user:
        user = default_user(tid)
        save_user(user)
        print("[NEW USER]", tid)
        return user
    user.pop("_id", None)
    return user
