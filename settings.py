import json
from pathlib import Path

APP_DIR = Path.home() / ".config" / "ops_console"
SETTINGS_PATH = APP_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "theme": "dark",
    "refresh_interval_ms": 1200,
    "known_processes": ["firefox", "chrome", "code", "discord", "steam"],
}


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)

    interval = merged.get("refresh_interval_ms", DEFAULT_SETTINGS["refresh_interval_ms"])
    if not isinstance(interval, int):
        interval = DEFAULT_SETTINGS["refresh_interval_ms"]
    merged["refresh_interval_ms"] = max(300, min(5000, interval))

    if not isinstance(merged.get("known_processes"), list):
        merged["known_processes"] = DEFAULT_SETTINGS["known_processes"]

    return merged


def save_settings(data: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
