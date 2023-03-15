"""Bot data models."""

from collections import deque
from typing import Mapping, NamedTuple, Optional

MAX_HISTORY_DEPTH = 3


class UserMessage(NamedTuple):
    """Represents a question and an answer to it."""

    question: str
    answer: str


class UserData:
    """Represents data associated with a specific user."""

    def __init__(self, data: Mapping):
        # data should be a 'user data' mapping from the chat context
        self.data = data
        self.messages = UserMessages(data)


class UserMessages:
    """Represents user message history."""

    def __init__(self, data: Mapping) -> None:
        if "messages" not in data:
            data["messages"] = deque([], MAX_HISTORY_DEPTH)
        self.messages = data["messages"]

    @property
    def last(self) -> Optional[UserMessage]:
        """The latest chat message (if any)."""
        if not self.messages:
            return None
        return self.messages[-1]

    def add(self, question: str, answer: str):
        """Adds a message to the message history."""
        self.messages.append(UserMessage(question, answer))

    def pop(self) -> Optional[UserMessage]:
        """Removes the last message from the message history and returns it."""
        if not self.messages:
            return None
        return self.messages.pop()

    def clear(self):
        """Cleares messages history."""
        self.messages.clear()

    def as_list(self):
        return list(self.messages)

    def __str__(self) -> str:
        return str(self.messages)

    def __repr__(self) -> str:
        return repr(self.messages)
