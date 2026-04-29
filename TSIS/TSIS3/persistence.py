"""
persistence.py — Save/load settings and leaderboard JSON files.
"""

import json
import os

LEADERBOARD_FILE = "leaderboard.json"
SETTINGS_FILE    = "settings.json"

DEFAULT_SETTINGS = {
    "sound":      True,
    "car_color":  "red",
    "difficulty": "normal",
}


# ── Settings ──────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    """Return merged settings; any missing keys fall back to defaults."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


# ── Leaderboard ───────────────────────────────────────────────────────────────

def load_leaderboard() -> list:
    """Return list of entry dicts sorted by score desc (top 10)."""
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def save_leaderboard(leaderboard: list) -> None:
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2)


def add_score(name: str, score: int, distance: int, coins: int) -> list:
    """Append entry, sort, trim to top 10, save, return updated list."""
    lb = load_leaderboard()
    lb.append({"name": name, "score": score,
                "distance": distance, "coins": coins})
    lb.sort(key=lambda e: e["score"], reverse=True)
    lb = lb[:10]
    save_leaderboard(lb)
    return lb
