import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

def load_rules_v3() -> dict:
    path = DATA / "substitution_rules_v3.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
