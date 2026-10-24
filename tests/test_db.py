import datetime as dt
import os
import pickle
import tempfile
import unittest
from collections import deque

from bot import db
from bot.models import ChatData, UserData, UserMessage


class InitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "data", "pokitoki.db")

    def tearDown(self) -> None:
        db.close()
        self.dir.cleanup()

    def test_create(self):
        db.init(self.path)
        self.assertTrue(os.path.exists(self.path))
        tables = db.conn.execute("select name from sqlite_master where type = 'table'").fetchall()
        self.assertEqual({t[0] for t in tables}, {"chats", "users", "messages"})

    def test_reopen(self):
        db.init(self.path)
        ChatData(1).model = "gpt-5"
        db.close()
        db.init(self.path)
        self.assertEqual(ChatData(1).model, "gpt-5")


class ImportPickleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.pickle_path = os.path.join(self.dir.name, "persistence.pkl")
        self.db_path = os.path.join(self.dir.name, "pokitoki.db")
        data = {
            "user_data": {
                1: {
                    "messages": deque([UserMessage("Hello", "Hi")], maxlen=3),
                    "message_counter": {"value": 2, "timestamp": dt.datetime.now()},
                },
            },
            "chat_data": {
                1: {"model": "gpt-5", "prompt": "Laugh"},
                -100500: {"prompt": "Be serious"},
                2: {"model": "", "prompt": ""},
                3: {},
            },
            "bot_data": {},
            "callback_data": None,
            "conversations": {},
        }
        with open(self.pickle_path, "wb") as file:
            pickle.dump(data, file)

    def tearDown(self) -> None:
        self.dir.cleanup()

    def test_import(self):
        db.import_pickle(self.pickle_path, self.db_path)
        db.init(self.db_path)
        self.addCleanup(db.close)
        self.assertEqual(ChatData(1).model, "gpt-5")
        self.assertEqual(ChatData(1).prompt, "Laugh")
        self.assertEqual(ChatData(-100500).model, "")
        self.assertEqual(ChatData(-100500).prompt, "Be serious")
        (count,) = db.conn.execute("select count(*) from chats").fetchone()
        self.assertEqual(count, 2)
        # history and counters are not imported
        self.assertEqual(UserData(1).messages.as_list(), [])
        self.assertEqual(UserData(1).message_counter.value, 0)

    def test_no_pickle(self):
        db.import_pickle(os.path.join(self.dir.name, "missing.pkl"), self.db_path)
        self.assertFalse(os.path.exists(self.db_path))
