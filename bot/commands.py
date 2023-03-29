"""
Working with custom commands.
A custom command is an action that preprocesses a question before asking it of the AI.
"""

import re
from bot import config

command_re = re.compile(r"^!(\w+)\s")


def extract(question: str) -> tuple[str, str]:
    """Extracts a custom command from the question."""
    match = command_re.match(question)
    if not match:
        raise ValueError("failed to parse command")
    cmd_name = match.group(1)
    question = question.removeprefix(match.group(0)).strip()
    return cmd_name, question


def apply(name: str, question: str) -> str:
    """Applies a given command to a text."""
    prompt = config.commands.get(name)
    if not prompt:
        raise ValueError(f"unknown command: {name}")
    return f"{prompt}\n\n{question}"
