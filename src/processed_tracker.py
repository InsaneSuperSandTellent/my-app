import json
import os

PROCESSED_FILE = "./logs/processed.json"


def load_processed() -> list[str]:
    if not os.path.exists(PROCESSED_FILE):
        return []
    with open(PROCESSED_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_processed(filenames: list[str]) -> None:
    os.makedirs(os.path.dirname(PROCESSED_FILE), exist_ok=True)
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(filenames, f)
