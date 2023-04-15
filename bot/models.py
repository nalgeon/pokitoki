"""Bot data models."""

from collections import deque
import datetime as dt
from typing import Generic, Mapping, NamedTuple, Optional, TypeVar
from bot.config import config

T = TypeVar("T")


class UserData:
    """Represents data associated with a specific user."""

    def __init__(self, data: Mapping):
        # data should be a 'user data' mapping from the chat context
        self.data = data
        self.messages = UserMessages(data, maxlen=config.conversation.depth)
        period = parse_period(value=1, period=config.conversation.message_limit.period)
        message_count = TimestampedValue(data, name="message_counter", initial=0)
        self.message_counter = ExpiringCounter(message_count, period=period)


class UserMessage(NamedTuple):
    """Represents a question and an answer to it."""

    question: str
    answer: str


class UserMessages:
    """Represents user message history."""

    def __init__(self, data: Mapping, maxlen: int) -> None:
        messages = data.get("messages") or []
        data["messages"] = deque(messages, maxlen)
        self.data = data
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


class TimestampedValue(Generic[T]):
    """A value with a 'last modified' timestamp."""

    def __init__(self, data: Mapping, name: str, initial: Optional[T] = None) -> None:
        if name not in data:
            data[name] = {"value": initial, "timestamp": dt.datetime.now()}
        self._data = data[name]

    @property
    def value(self) -> T:
        """Returns the value."""
        return self._data["value"]

    @value.setter
    def value(self, value: T) -> None:
        """Sets the value."""
        self._data["value"] = value
        self._data["timestamp"] = dt.datetime.now()

    @property
    def timestamp(self) -> dt.datetime:
        """Returns the date and time of the last modification."""
        return self._data["timestamp"]


class ExpiringCounter:
    """A counter that expires after a given period of time."""

    def __init__(self, data: TimestampedValue, period: dt.timedelta) -> None:
        self._data = data
        self.period = period

    @property
    def value(self) -> int:
        """Counter value."""
        return self._data.value

    def is_expired(self) -> bool:
        """Checks if the counter value has expired."""
        return dt.datetime.now() > self._data.timestamp + self.period

    def expires_after(self) -> dt.timedelta:
        """
        Returns the timedelta after which the counter will expire
        (with respect to the current time).
        If the counter has already expired, returns zero timedelta.
        """
        if self.is_expired():
            return dt.timedelta(0)
        return self._data.timestamp + self.period - dt.datetime.now()

    def increment(self) -> int:
        """Increments and returns the counter value."""
        if self.is_expired():
            self._data.value = 0
        self._data.value += 1
        return self._data.value


def parse_period(value: int, period: str) -> dt.timedelta:
    """Creates a timedelta from a time period description."""
    if value < 0:
        raise ValueError(f"Invalid value: {value}")
    if period not in ("second", "minute", "hour", "day", "week"):
        raise ValueError(f"Invalid period: {period}")
    kwargs = {}
    kwargs[f"{period}s"] = value
    return dt.timedelta(**kwargs)


def format_timedelta(delta: dt.timedelta) -> str:
    """Returns a string representation of a timedelta."""
    if delta == dt.timedelta(0):
        return "now"
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        return f"{seconds//60} minutes"
    if seconds < 2 * 3600:
        hours = round(seconds / 3600, 1)
        return f"{hours} hours"
    return f"{seconds//3600} hours"
