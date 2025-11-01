# state_manager.py
import json
from config import STATE_FILE
from datetime import datetime

def save_state(obj: dict):
    try:
        with open(STATE_FILE, "w") as fh:
            json.dump(obj, fh, default=str)
    except Exception as e:
        print("Failed to save state:", e)

def load_state():
    try:
        with open(STATE_FILE, "r") as fh:
            return json.load(fh)
    except Exception:
        return {}
