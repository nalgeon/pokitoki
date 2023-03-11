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

    @property
    def messages(self) -> deque[UserMessage]:
        """Collection of past chat messages."""
        if "messages" not in self.data:
            self.data["messages"] = deque([], MAX_HISTORY_DEPTH)
        return self.data["messages"]

    @property
    def last_message(self) -> Optional[UserMessage]:
        """The latest chat message (if any)."""
        if not self.messages:
            return None
        return self.messages[-1]

    def add_message(self, question: str, answer: str):
        """Adds a message to the message history."""
        self.messages.append(UserMessage(question, answer))

    def clear_messages(self):
        """Cleares messages history."""
        self.data["messages"] = deque([], MAX_HISTORY_DEPTH)
