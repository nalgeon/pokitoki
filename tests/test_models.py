from collections import deque
import datetime as dt
import unittest

from bot import models
from bot.config import config
from bot.models import ExpiringCounter, TimestampedValue, UserData, UserMessage, UserMessages


class UserDataTest(unittest.TestCase):
    def test_init(self):
        data = {}
        user = UserData(data)
        self.assertEqual(user.messages.as_list(), [])
        self.assertEqual(data["messages"], deque([], maxlen=config.conversation.depth))
        self.assertEqual(user.message_counter.value, 0)
        self.assertEqual(data["message_counter"]["value"], 0)

    def test_messages(self):
        data = {}
        user = UserData(data)
        user.messages.add("question", "answer")
        user.messages.add("question", "answer")
        self.assertEqual(len(user.messages.as_list()), 2)
        self.assertEqual(len(data["messages"]), 2)

    def test_message_counter(self):
        data = {}
        user = UserData(data)
        user.message_counter.increment()
        user.message_counter.increment()
        self.assertEqual(user.message_counter.value, 2)
        self.assertEqual(data["message_counter"]["value"], 2)


class UserMessagesTest(unittest.TestCase):
    def test_init(self):
        um = UserMessages({}, maxlen=config.conversation.depth)
        self.assertIsInstance(um.messages, deque)
        self.assertEqual(um.messages.maxlen, config.conversation.depth)

        data = {"messages": deque([UserMessage("Hello", "Hi")])}
        um = UserMessages(data, maxlen=3)
        self.assertEqual(um.messages, data["messages"])

    def test_last(self):
        um = UserMessages({}, maxlen=3)
        self.assertIsNone(um.last)

        data = {
            "messages": deque(
                [UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")]
            )
        }
        um = UserMessages(data, maxlen=3)
        self.assertEqual(um.last, ("Is it cold today?", "Yep!"))

    def test_add(self):
        data = {"messages": deque([UserMessage("Hello", "Hi")])}
        um = UserMessages(data, maxlen=3)
        um.add("Is it cold today?", "Yep!")
        self.assertEqual(
            um.messages,
            deque([UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")]),
        )

    def test_pop(self):
        data = {"messages": deque([UserMessage("Hello", "Hi")])}
        um = UserMessages(data, maxlen=3)
        message = um.pop()
        self.assertEqual(message.question, "Hello")
        self.assertEqual(message.answer, "Hi")

        message = um.pop()
        self.assertIsNone(message)

    def test_clear(self):
        data = {"messages": deque([UserMessage("Hello", "Hi")])}
        um = UserMessages(data, maxlen=3)
        um.clear()
        self.assertEqual(len(um.messages), 0)

    def test_as_list(self):
        data = {
            "messages": deque(
                [UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")]
            )
        }
        um = UserMessages(data, maxlen=3)
        self.assertEqual(um.as_list(), [("Hello", "Hi"), ("Is it cold today?", "Yep!")])


class TimestampedValueTest(unittest.TestCase):
    def test_init(self):
        data = {}
        now = dt.datetime.now()
        counter = TimestampedValue(data, name="counter")
        self.assertEqual(data["counter"]["value"], None)
        self.assertGreaterEqual(data["counter"]["timestamp"], now)
        self.assertIsNone(counter.value)
        self.assertGreaterEqual(counter.timestamp, now)

    def test_init_initial(self):
        data = {}
        now = dt.datetime.now()
        counter = TimestampedValue(data, name="counter", initial=42)
        self.assertEqual(data["counter"]["value"], 42)
        self.assertGreaterEqual(data["counter"]["timestamp"], now)
        self.assertEqual(counter.value, 42)
        self.assertGreaterEqual(counter.timestamp, now)

    def test_value(self):
        data = {}
        counter = TimestampedValue(data, name="counter")

        counter.value = 11
        self.assertEqual(data["counter"]["value"], 11)
        self.assertEqual(counter.value, 11)

        counter.value = 21
        self.assertEqual(data["counter"]["value"], 21)
        self.assertEqual(counter.value, 21)

    def test_timestamp(self):
        data = {}
        counter = TimestampedValue(data, name="counter")

        now = dt.datetime.now()
        counter.value = 11
        self.assertGreaterEqual(data["counter"]["timestamp"], now)
        self.assertGreaterEqual(counter.timestamp, now)

        now = dt.datetime.now()
        counter.value = 21
        self.assertGreaterEqual(data["counter"]["timestamp"], now)
        self.assertGreaterEqual(counter.timestamp, now)


class ExpiringCounterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = TimestampedValue(data={}, name="counter", initial=0)
        self.counter = ExpiringCounter(self.data, period=dt.timedelta(hours=1))

    def test_increment(self):
        self.assertEqual(self.data.value, 0)
        self.counter.increment()
        self.assertEqual(self.data.value, 1)
        self.counter.increment()
        self.assertEqual(self.data.value, 2)

    def test_is_expired(self):
        self.assertFalse(self.counter.is_expired())
        self.data._data["timestamp"] = dt.datetime.now() - dt.timedelta(hours=2)
        self.assertTrue(self.counter.is_expired())

    def test_expires_after(self):
        self.assertGreater(self.counter.expires_after(), dt.timedelta(minutes=59))
        self.assertLessEqual(self.counter.expires_after(), dt.timedelta(minutes=60))

        self.data._data["timestamp"] = self.data._data["timestamp"] - dt.timedelta(minutes=30)
        self.assertGreater(self.counter.expires_after(), dt.timedelta(minutes=29))
        self.assertLessEqual(self.counter.expires_after(), dt.timedelta(minutes=30))

        self.data._data["timestamp"] = dt.datetime.now() - dt.timedelta(hours=2)
        self.assertEqual(self.counter.expires_after(), dt.timedelta(0))

    def test_increment_expired(self):
        self.counter.increment()
        self.counter.increment()
        self.counter.increment()
        self.assertEqual(self.data.value, 3)

        self.data._data["timestamp"] = dt.datetime.now() - dt.timedelta(hours=2)
        self.counter.increment()
        self.assertEqual(self.data.value, 1)


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
