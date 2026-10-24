"""SQLite database for chat and user data."""

import logging
import os
import pickle
import sqlite3
from contextlib import closing

logger = logging.getLogger(__name__)

SCHEMA = """
create table if not exists chats (
    id integer primary key,
    model text,
    prompt text
);

create table if not exists users (
    id integer primary key,
    message_count integer not null default 0,
    message_count_at text
);

create table if not exists messages (
    id integer primary key,
    user_id integer not null,
    question text not null,
    answer text not null,
    created_at text not null default (datetime('now'))
);

create index if not exists messages_user_id on messages (user_id, id);
"""

# The database connection, set by `init()`.
conn: sqlite3.Connection = None


def init(path: str) -> None:
    """Opens the database (creating it if necessary)."""
    global conn
    conn = _connect(path)


def close() -> None:
    """Closes the database."""
    conn.close()


def import_pickle(pickle_path: str, db_path: str) -> None:
    """
    Imports chat settings (model and prompt) from the PicklePersistence file
    used by older bot versions. Message history and counters are not imported.
    """
    if not os.path.exists(pickle_path):
        return
    with open(pickle_path, "rb") as file:
        data = _Unpickler(file).load()
    chats = [
        (chat_id, chat.get("model") or None, chat.get("prompt") or None)
        for chat_id, chat in (data.get("chat_data") or {}).items()
        if chat.get("model") or chat.get("prompt")
    ]
    with closing(_connect(db_path)) as db:
        db.executemany("insert or replace into chats (id, model, prompt) values (?, ?, ?)", chats)
    logger.info("Imported settings for %s chats from %s", len(chats), pickle_path)


def _connect(path: str) -> sqlite3.Connection:
    """Opens the database, creating the file and the schema if necessary."""
    if path != ":memory:":
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    db = sqlite3.connect(path, autocommit=True, check_same_thread=False)
    db.execute("pragma journal_mode = wal")
    db.executescript(SCHEMA)
    return db


class _Unpickler(pickle.Unpickler):
    """
    Loads plain data from the persistence file.
    Any other classes (e.g. old bot models) are replaced with a stub,
    so the file can be loaded even after these classes have changed.
    """

    allowed = frozenset({("collections", "deque"), ("datetime", "datetime")})

    def find_class(self, module: str, name: str):
        if (module, name) in self.allowed:
            return super().find_class(module, name)
        return _Stub

    def persistent_load(self, pid):
        return None


class _Stub:
    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        pass

    def __setstate__(self, state):
        pass
