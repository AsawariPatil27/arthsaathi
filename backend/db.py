import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=2000)
db = client.get_default_database()
users = db.users
goals = db.goals
transactions = db.transactions
merchant_categories = db.merchant_categories
schemes = db.schemes
glossary = db.glossary

try:
    users.create_index("telegramId", unique=True)
    goals.create_index([("telegramId", 1), ("type", 1)])
    transactions.create_index("telegramId")
    transactions.create_index("refHash", sparse=True)
    merchant_categories.create_index("merchant", unique=True)
    schemes.create_index("slug", unique=True)
    schemes.create_index([("scheme_name", "text"), ("details", "text"), ("eligibility", "text"), ("tags", "text")])
    glossary.create_index("term", unique=True)
except PyMongoError as error:
    print(f"[MongoDB] Index creation skipped: {error}")
