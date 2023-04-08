"""Bot configuration parameters."""

import os
import yaml
from dataclasses import dataclass

# Config schema version. Increments for backward-incompatible changes.
SCHEMA_VERSION = 2


def load(filename) -> dict:
    """Loads the cofiguration from a file."""
    with open(filename, "r") as f:
        config = yaml.safe_load(f)

    config, has_changed = migrate(config)
    if has_changed:
        with open(filename, "w") as f:
            yaml.safe_dump(config, f, indent=4, allow_unicode=True)
    return config


def migrate(config: dict) -> tuple[dict, bool]:
    """Migrates the configuration to the latest schema version."""
    schema_version = config.get("schema_version", 1)
    has_changed = False
    if schema_version == 1:
        has_changed = True
        config = _migrate_v1(config)
    return config, has_changed


def _migrate_v1(old: dict) -> dict:
    config = {
        "schema_version": 2,
        "telegram": None,
        "openai": None,
        "max_history_depth": old.get("max_history_depth"),
        "imagine": old.get("imagine"),
        "persistence_path": old["persistence_path"],
        "shortcuts": old.get("shortcuts"),
    }
    config["telegram"] = {
        "token": old["telegram_token"],
        "usernames": old["telegram_usernames"],
        "chat_ids": old.get("telegram_chat_ids"),
    }
    config["openai"] = {
        "api_key": old["openai_api_key"],
        "model": old.get("openai_model"),
    }
    return config


@dataclass
class Telegram:
    token: str
    usernames: set
    chat_ids: list


@dataclass
class OpenAI:
    api_key: str
    model: str


filename = os.getenv("CONFIG", "config.yml")
_config = load(filename)

# Bot version.
version = 104

# Telegram settings.
telegram = Telegram(
    token=_config["telegram"]["token"],
    usernames=set(_config["telegram"]["usernames"]),
    chat_ids=_config["telegram"].get("chat_ids") or [],
)

# OpenAI settings.
openai = OpenAI(
    api_key=_config["openai"]["api_key"],
    model=_config["openai"].get("model") or "gpt-3.5-turbo",
)

# The maximum number of previous messages
# the bot will remember when talking to a user.
max_history_depth = _config.get("max_history_depth") or 3

# Enable/disable image generation.
imagine = _config.get("imagine") or True

# Where to store the chat context file.
persistence_path = _config["persistence_path"]

# Custom AI commands (additional prompts)
shortcuts = _config.get("shortcuts") or {}
