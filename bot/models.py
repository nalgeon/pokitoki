from collections import deque
from typing import Mapping, NamedTuple, Optional

MAX_HISTORY_DEPTH = 3


class UserMessage(NamedTuple):
    question: str
    answer: str


class UserData:
    def __init__(self, data: Mapping):
        self.data = data

    @property
    def messages(self) -> deque[UserMessage]:
        if "messages" not in self.data:
            self.data["messages"] = deque([], MAX_HISTORY_DEPTH)
        return self.data["messages"]

    @property
    def last_message(self) -> Optional[UserMessage]:
        if not self.messages:
            return None
        return self.messages[-1]

    def add_message(self, question: str, answer: str):
        self.messages.append(UserMessage(question, answer))

    def clear_messages(self):
        self.data["messages"] = deque([], MAX_HISTORY_DEPTH)

    def build_history(self) -> deque[UserMessage]:
        messages = self.messages
        history = []
        depth = min(len(messages), messages.maxlen)
        for idx in range(depth, 0, -1):
            message = messages[-idx]
            history.append(message)
        return history
