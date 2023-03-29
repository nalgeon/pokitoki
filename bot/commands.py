"""
Working with custom commands.
A custom command is an action that preprocesses a question before asking it of the AI.
"""

import re
from typing import Callable, NamedTuple, Optional
from bot import config

command_re = re.compile(r"^!(\w+)\s")


class Command(NamedTuple):
    """Custom command."""

    name: str
    action: Optional[Callable] = None
    arg: Optional[str] = None


class Actions:
    """Custom command actions."""

    @staticmethod
    def prefix(text: str, prefix: str) -> str:
        """Prepends a given prefix to a text."""
        return f"{prefix}\n\n{text}"

    @classmethod
    def get(cls, name) -> Optional[Callable]:
        """Returns an action by its name."""
        return getattr(cls, name, None)


def extract(question: str) -> tuple[Command, str]:
    """Extracts a custom command from the question."""
    match = command_re.match(question)
    if not match:
        return Command(name=""), question
    cmd_name = match.group(1)
    question = question.removeprefix(match.group(0)).strip()
    command = get(cmd_name)
    return command, question


def get(name: str) -> Command:
    """Returns a custom command by name."""
    command = config.commands.get(name)
    if not command:
        return Command(name=name)
    action = Actions.get(command.get("action"))
    if not action:
        return Command(name=name)
    return Command(name=name, action=action, arg=command.get("arg"))
