"""Bot configuration parameters."""

import os
from typing import Any
import yaml
import dataclasses
from dataclasses import dataclass


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
        "persistence_path": old.get("persistence_path"),
        "shortcuts": old.get("shortcuts"),
    }
    config["telegram"] = {
        "token": old["telegram_token"],
        "usernames": old.get("telegram_usernames"),
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
    usernames: list
    admins: list
    chat_ids: list


@dataclass
class OpenAI:
    api_key: str
    model: str
    prompt: str
    params: dict

    default_model = "gpt-3.5-turbo"
    default_prompt = "Your primary goal is to answer my questions. This may involve writing code or providing helpful information. Be detailed and thorough in your responses."
    default_params = {
        "temperature": 0.7,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "max_tokens": 1000,
    }

    def __init__(self, api_key: str, model: str, prompt: str, params: dict) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        self.prompt = prompt or self.default_prompt
        self.params = self.default_params.copy()
        self.params.update(params)


class Config:
    """Config properties."""

    # Config schema version. Increments for backward-incompatible changes.
    schema_version = 2
    # Readonly properties.
    readonly = [
        "schema_version",
        "max_history_depth",
        "persistence_path",
    ]
    # Editable properties.
    editable = [
        "telegram",
        "openai",
        "imagine",
        "shortcuts",
    ]

    def __init__(self, filename: str, src: dict) -> None:
        # Config filename.
        self.filename = filename
        # Bot version.
        self.version = 125

        # Telegram settings.
        self.telegram = Telegram(
            token=src["telegram"]["token"],
            usernames=src["telegram"].get("usernames") or [],
            admins=src["telegram"].get("admins") or [],
            chat_ids=src["telegram"].get("chat_ids") or [],
        )

        # OpenAI settings.
        self.openai = OpenAI(
            api_key=src["openai"]["api_key"],
            model=src["openai"].get("model"),
            prompt=src["openai"].get("prompt"),
            params=src["openai"].get("params") or {},
        )

        # The maximum number of previous messages
        # the bot will remember when talking to a user.
        self.max_history_depth = src.get("max_history_depth") or 3

        # Enable/disable image generation.
        imagine = src.get("imagine", True)
        self.imagine = True if imagine is None else imagine

        # Where to store the chat context file.
        self.persistence_path = src.get("persistence_path") or "./data/persistence.pkl"

        # Custom AI commands (additional prompts).
        self.shortcuts = src.get("shortcuts") or {}

    def get_value(self, property: str) -> Any:
        """Returns a config property value."""
        names = property.split(".")
        if names[0] not in self.readonly and names[0] not in self.editable:
            raise ValueError(f"No such property: {property}")

        obj = self
        for name in names[:-1]:
            if not hasattr(obj, name):
                raise ValueError(f"No such property: {property}")
            obj = getattr(obj, name)

        name = names[-1]
        if isinstance(obj, dict):
            if name not in obj:
                raise ValueError(f"No such property: {property}")
            return obj[name]

        if isinstance(obj, object):
            if not hasattr(obj, name):
                raise ValueError(f"No such property: {property}")
            val = getattr(obj, name)
            if dataclasses.is_dataclass(val):
                return dataclasses.asdict(val)
            return val

        raise ValueError(f"No such property: {property}")

    def set_value(self, property: str, value: str) -> None:
        """Changes a config property value."""
        val = yaml.safe_load(value)
        if not isinstance(val, (list, str, int, float, bool)):
            raise ValueError("Cannot set composite value")

        names = property.split(".")
        if names[0] not in self.editable:
            raise ValueError(f"Property {property} is not editable")

        obj = self
        for name in names[:-1]:
            if not hasattr(obj, name):
                raise ValueError(f"No such property: {property}")
            obj = getattr(obj, name, val)

        name = names[-1]
        if isinstance(obj, dict):
            obj[name] = val
            return

        if isinstance(obj, object):
            if not hasattr(obj, name):
                raise ValueError(f"No such property: {property}")
            setattr(obj, name, val)
            return

        raise ValueError(f"No such property: {property}")

    def save(self) -> None:
        """Saves the config to disk."""
        data = {
            "schema_version": self.schema_version,
            "telegram": dataclasses.asdict(self.telegram),
            "openai": dataclasses.asdict(self.openai),
            "max_history_depth": self.max_history_depth,
            "imagine": self.imagine,
            "persistence_path": self.persistence_path,
            "shortcuts": self.shortcuts,
        }
        with open(self.filename, "w") as file:
            yaml.safe_dump(data, file, indent=4, allow_unicode=True)


filename = os.getenv("CONFIG", "config.yml")
_config = load(filename)
config = Config(filename, _config)
