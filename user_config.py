import json
import os
from typing import Any, Dict, Optional

CONFIG_FILE = "credentials/user_configs.json"


def _load_all() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f, indent=2)
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_all(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user_config(email: str, config_type: str) -> Optional[Dict[str, Any]]:
    if not email:
        return None
    data = _load_all()
    return data.get(email, {}).get(config_type)


def update_user_config(email: str, config_type: str, config_data: Dict[str, Any]) -> bool:
    if not email:
        return False
    data = _load_all()
    if email not in data:
        data[email] = {}
    data[email][config_type] = config_data
    _save_all(data)
    return True
