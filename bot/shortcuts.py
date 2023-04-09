"""
Working with shortcuts.
A shortcut is an action that preprocesses a question before asking it of the AI.
"""

import re
from bot.config import config

shortcut_re = re.compile(r"^!(\w+)\b")


def extract(question: str) -> tuple[str, str]:
    """Extracts a shortcut from the question."""
    match = shortcut_re.match(question)
    if not match:
        raise ValueError("failed to extract shortcut")
    name = match.group(1)
    question = question.removeprefix(match.group(0)).strip()
    return name, question


def apply(name: str, question: str) -> str:
    """Applies a given shortcut to a text."""
    prompt = config.shortcuts.get(name)
    if not prompt:
        raise ValueError(f"unknown shortcut: {name}")
    return f"{prompt}\n\n{question}"
