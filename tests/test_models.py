import datetime as dt
import unittest

from bot import db, models
from bot.config import config
from bot.models import ChatData, ExpiringCounter, UserData, UserMessage, UserMessages


class ChatDataTest(unittest.TestCase):
    def setUp(self) -> None:
        db.init(":memory:")

    def test_init(self):
        chat = ChatData(1)
        self.assertEqual(chat.model, "")
        self.assertEqual(chat.prompt, "")

    def test_set(self):
        chat = ChatData(1)
        chat.model = "gpt-5"
        chat.prompt = "Laugh"
        self.assertEqual(ChatData(1).model, "gpt-5")
        self.assertEqual(ChatData(1).prompt, "Laugh")
        self.assertEqual(ChatData(2).model, "")
        row = db.conn.execute("select model, prompt from chats where id = 1").fetchone()
        self.assertEqual(row, ("gpt-5", "Laugh"))

    def test_reset(self):
        chat = ChatData(1)
        chat.model = "gpt-5"
        chat.model = ""
        self.assertEqual(chat.model, "")
        row = db.conn.execute("select model from chats where id = 1").fetchone()
        self.assertEqual(row, (None,))


class UserDataTest(unittest.TestCase):
    def setUp(self) -> None:
        db.init(":memory:")

    def test_init(self):
        user = UserData(1)
        self.assertEqual(user.messages.as_list(), [])
        self.assertEqual(user.messages.maxlen, config.conversation.depth)
        self.assertEqual(user.message_counter.value, 0)

    def test_messages(self):
        user = UserData(1)
        user.messages.add("question", "answer")
        user.messages.add("question", "answer")
        self.assertEqual(len(user.messages.as_list()), 2)
        self.assertEqual(len(UserData(1).messages.as_list()), 2)
        self.assertEqual(UserData(2).messages.as_list(), [])

    def test_message_counter(self):
        user = UserData(1)
        user.message_counter.increment()
        user.message_counter.increment()
        self.assertEqual(user.message_counter.value, 2)
        self.assertEqual(UserData(1).message_counter.value, 2)


class UserMessagesTest(unittest.TestCase):
    def setUp(self) -> None:
        db.init(":memory:")
        self.um = UserMessages(1, maxlen=3)

    def test_last(self):
        self.assertIsNone(self.um.last)
        self.um.add("Hello", "Hi")
        self.um.add("Is it cold today?", "Yep!")
        self.assertEqual(self.um.last, ("Is it cold today?", "Yep!"))

    def test_add(self):
        self.um.add("Hello", "Hi")
        self.um.add("Is it cold today?", "Yep!")
        self.assertEqual(
            self.um.as_list(),
            [UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")],
        )

    def test_add_maxlen(self):
        for i in range(5):
            self.um.add(f"q{i}", f"a{i}")
        self.assertEqual([m.question for m in self.um.as_list()], ["q2", "q3", "q4"])
        (count,) = db.conn.execute("select count(*) from messages").fetchone()
        self.assertEqual(count, 3)

    def test_pop(self):
        self.um.add("Hello", "Hi")
        message = self.um.pop()
        self.assertEqual(message.question, "Hello")
        self.assertEqual(message.answer, "Hi")

        message = self.um.pop()
        self.assertIsNone(message)

    def test_clear(self):
        self.um.add("Hello", "Hi")
        UserMessages(2, maxlen=3).add("Hello", "Hi")
        self.um.clear()
        self.assertEqual(self.um.as_list(), [])
        self.assertEqual(len(UserMessages(2, maxlen=3).as_list()), 1)

    def test_as_list(self):
        self.um.add("Hello", "Hi")
        self.um.add("Is it cold today?", "Yep!")
        self.assertEqual(self.um.as_list(), [("Hello", "Hi"), ("Is it cold today?", "Yep!")])


class ExpiringCounterTest(unittest.TestCase):
    def setUp(self) -> None:
        db.init(":memory:")
        self.counter = ExpiringCounter(1, period=dt.timedelta(hours=1))

    def _shift(self, delta: dt.timedelta) -> None:
        timestamp = self.counter.timestamp + delta
        db.conn.execute(
            "update users set message_count_at = ? where id = 1", (timestamp.isoformat(),)
        )

    def test_init(self):
        self.assertEqual(self.counter.value, 0)
        self.assertIsNone(self.counter.timestamp)
        self.assertTrue(self.counter.is_expired())
        self.assertEqual(self.counter.expires_after(), dt.timedelta(0))

    def test_increment(self):
        now = dt.datetime.now()
        self.assertEqual(self.counter.increment(), 1)
        self.assertEqual(self.counter.value, 1)
        self.assertGreaterEqual(self.counter.timestamp, now)
        self.assertEqual(self.counter.increment(), 2)
        self.assertEqual(self.counter.value, 2)

    def test_is_expired(self):
        self.counter.increment()
        self.assertFalse(self.counter.is_expired())
        self._shift(-dt.timedelta(hours=2))
        self.assertTrue(self.counter.is_expired())

    def test_expires_after(self):
        self.counter.increment()
        self.assertGreater(self.counter.expires_after(), dt.timedelta(minutes=59))
        self.assertLessEqual(self.counter.expires_after(), dt.timedelta(minutes=60))

        self._shift(-dt.timedelta(minutes=30))
        self.assertGreater(self.counter.expires_after(), dt.timedelta(minutes=29))
        self.assertLessEqual(self.counter.expires_after(), dt.timedelta(minutes=30))

        self._shift(-dt.timedelta(hours=2))
        self.assertEqual(self.counter.expires_after(), dt.timedelta(0))

    def test_increment_expired(self):
        self.counter.increment()
        self.counter.increment()
        self.counter.increment()
        self.assertEqual(self.counter.value, 3)

        self._shift(-dt.timedelta(hours=2))
        self.counter.increment()
        self.assertEqual(self.counter.value, 1)


class ParsePeriodTest(unittest.TestCase):
    def test_parse(self):
        delta = models.parse_period(5, "minute")
        self.assertEqual(delta, dt.timedelta(minutes=5))
        delta = models.parse_period(3, "hour")
        self.assertEqual(delta, dt.timedelta(hours=3))
        delta = models.parse_period(1, "day")
        self.assertEqual(delta, dt.timedelta(days=1))

    def test_zero(self):
        delta = models.parse_period(0, "minute")
        self.assertEqual(delta, dt.timedelta(0))
        delta = models.parse_period(0, "hour")
        self.assertEqual(delta, dt.timedelta(0))
        delta = models.parse_period(0, "day")
        self.assertEqual(delta, dt.timedelta(0))

    def test_invalid_value(self):
        with self.assertRaises(ValueError):
            models.parse_period(-5, "minute")

    def test_invalid_period(self):
        with self.assertRaises(ValueError):
            models.parse_period(1, "month")


class FormatTimedeltaTest(unittest.TestCase):
    def test_zero(self):
        val = models.format_timedelta(dt.timedelta(0))
        self.assertEqual(val, "now")

    def test_seconds(self):
        val = models.format_timedelta(dt.timedelta(seconds=30))
        self.assertEqual(val, "30 seconds")

    def test_minutes(self):
        val = models.format_timedelta(dt.timedelta(minutes=42))
        self.assertEqual(val, "42 minutes")

    def test_one_hour(self):
        val = models.format_timedelta(dt.timedelta(minutes=90))
        self.assertEqual(val, "1.5 hours")

    def test_hours(self):
        val = models.format_timedelta(dt.timedelta(hours=5))
        self.assertEqual(val, "5 hours")
