import json
import os

from pymongo import UpdateOne

from db import schemes


FIELDS = ["scheme_name", "slug", "details", "benefits", "eligibility", "application", "documents", "level", "schemeCategory", "tags"]


def clean(row):
    return {field: str(row.get(field, "")).strip() for field in FIELDS}


def main():
    path = os.path.join("data", "schemes.json")
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    batch = []
    for row in data:
        scheme = clean(row)
        if not scheme["scheme_name"] or not scheme["slug"]:
            continue
        batch.append(UpdateOne({"slug": scheme["slug"]}, {"$set": scheme}, upsert=True))

    if batch:
        schemes.bulk_write(batch, ordered=False)

    print(f"Imported {len(batch)} schemes")


if __name__ == "__main__":
    main()
