import csv
import os

from pymongo import UpdateOne

from db import schemes


FIELDS = ["scheme_name", "slug", "details", "benefits", "eligibility", "application", "documents", "level", "schemeCategory", "tags"]


def clean(row):
    return {field: str(row.get(field, "")).strip() for field in FIELDS}


def main():
    path = os.path.join("data", "schemes.csv")
    count = 0
    batch = []

    with open(path, encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            scheme = clean(row)
            if not scheme["scheme_name"] or not scheme["slug"]:
                continue
            batch.append(UpdateOne({"slug": scheme["slug"]}, {"$set": scheme}, upsert=True))
            count += 1
            if len(batch) == 500:
                schemes.bulk_write(batch, ordered=False)
                batch = []

    if batch:
        schemes.bulk_write(batch, ordered=False)

    print(f"Imported {count} schemes")


if __name__ == "__main__":
    main()
