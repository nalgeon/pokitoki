"""Bot data models, stored in the database."""

import datetime as dt
from typing import NamedTuple

from bot import db
from bot.config import config


class ChatData:
    """Represents data associated with a specific chat."""

    def __init__(self, chat_id: int):
        self.chat_id = chat_id

    @property
    def model(self) -> str:
        row = db.conn.execute("select model from chats where id = ?", (self.chat_id,)).fetchone()
        return (row and row[0]) or ""

    @model.setter
    def model(self, value: str) -> None:
        db.conn.execute(
            "insert into chats (id, model) values (?, ?) "
            "on conflict (id) do update set model = excluded.model",
            (self.chat_id, value or None),
        )

    @property
    def prompt(self) -> str:
        row = db.conn.execute("select prompt from chats where id = ?", (self.chat_id,)).fetchone()
        return (row and row[0]) or ""

    @prompt.setter
    def prompt(self, value: str) -> None:
        db.conn.execute(
            "insert into chats (id, prompt) values (?, ?) "
            "on conflict (id) do update set prompt = excluded.prompt",
            (self.chat_id, value or None),
        )


class UserData:
    """Represents data associated with a specific user."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.messages = UserMessages(user_id, maxlen=config.conversation.depth)
        period = parse_period(value=1, period=config.conversation.message_limit.period)
        self.message_counter = ExpiringCounter(user_id, period=period)


class UserMessage(NamedTuple):
    """Represents a question and an answer to it."""

    question: str
    answer: str


class UserMessages:
    """Represents user message history (up to `maxlen` latest messages)."""

    def __init__(self, user_id: int, maxlen: int) -> None:
        self.user_id = user_id
        self.maxlen = maxlen

    @property
    def last(self) -> UserMessage | None:
        """The latest chat message (if any)."""
        row = db.conn.execute(
            "select question, answer from messages where user_id = ? order by id desc limit 1",
            (self.user_id,),
        ).fetchone()
        return UserMessage(*row) if row else None

    def add(self, question: str, answer: str):
        """Adds a message to the message history, removing the oldest ones beyond `maxlen`."""
        db.conn.execute(
            "insert into messages (user_id, question, answer) values (?, ?, ?)",
            (self.user_id, question, answer),
        )
        db.conn.execute(
            "delete from messages where user_id = ? and id not in "
            "(select id from messages where user_id = ? order by id desc limit ?)",
            (self.user_id, self.user_id, self.maxlen),
        )

    def pop(self) -> UserMessage | None:
        """Removes the last message from the message history and returns it."""
        row = db.conn.execute(
            "select id, question, answer from messages where user_id = ? order by id desc limit 1",
            (self.user_id,),
        ).fetchone()
        if not row:
            return None
        db.conn.execute("delete from messages where id = ?", (row[0],))
        return UserMessage(row[1], row[2])

    def clear(self):
        """Cleares messages history."""
        db.conn.execute("delete from messages where user_id = ?", (self.user_id,))

    def as_list(self) -> list[UserMessage]:
        rows = db.conn.execute(
            "select question, answer from "
            "(select id, question, answer from messages where user_id = ? order by id desc limit ?) "
            "order by id",
            (self.user_id, self.maxlen),
        ).fetchall()
        return [UserMessage(*row) for row in rows]

    def __str__(self) -> str:
        return str(self.as_list())

    def __repr__(self) -> str:
        return repr(self.as_list())


class ExpiringCounter:
    """A user message counter that expires after a given period of time."""

    def __init__(self, user_id: int, period: dt.timedelta) -> None:
        self.user_id = user_id
        self.period = period

    @property
    def value(self) -> int:
        """Counter value."""
        return self._load()[0]

    @property
    def timestamp(self) -> dt.datetime | None:
        """The date and time of the last modification (None if never modified)."""
        return self._load()[1]

    def is_expired(self) -> bool:
        """Checks if the counter value has expired."""
        timestamp = self.timestamp
        return timestamp is None or dt.datetime.now() > timestamp + self.period

    def expires_after(self) -> dt.timedelta:
        """
        Returns the timedelta after which the counter will expire
        (with respect to the current time).
        If the counter has already expired, returns zero timedelta.
        """
        if self.is_expired():
            return dt.timedelta(0)
        return self.timestamp + self.period - dt.datetime.now()

    def increment(self) -> int:
        """Increments and returns the counter value."""
        value = 1 if self.is_expired() else self.value + 1
        db.conn.execute(
            "insert into users (id, message_count, message_count_at) values (?, ?, ?) "
            "on conflict (id) do update set "
            "message_count = excluded.message_count, message_count_at = excluded.message_count_at",
            (self.user_id, value, dt.datetime.now().isoformat()),
        )
        return value

    def _load(self) -> tuple[int, dt.datetime | None]:
        row = db.conn.execute(
            "select message_count, message_count_at from users where id = ?", (self.user_id,)
        ).fetchone()
        if not row or not row[1]:
            return 0, None
        return row[0], dt.datetime.fromisoformat(row[1])


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
        return f"{seconds // 60} minutes"
    if seconds < 2 * 3600:
        hours = round(seconds / 3600, 1)
        return f"{hours} hours"
    return f"{seconds // 3600} hours"
