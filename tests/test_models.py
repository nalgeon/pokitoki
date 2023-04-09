from collections import deque
import unittest

from bot.config import config
from bot.models import UserMessage, UserMessages


class UserMessagesTest(unittest.TestCase):
    def test_init(self):
        um = UserMessages({})
        self.assertIsInstance(um.messages, deque)
        self.assertEqual(um.messages.maxlen, config.max_history_depth)

        data = {"messages": deque([UserMessage("Hello", "Hi")])}
        um = UserMessages(data)
        self.assertEqual(um.messages, data["messages"])

    def test_last(self):
        um = UserMessages({})
        self.assertIsNone(um.last)

        data = {
            "messages": deque(
                [UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")]
            )
        }
        um = UserMessages(data)
        self.assertEqual(um.last, ("Is it cold today?", "Yep!"))

    def test_add(self):
        data = {"messages": deque([UserMessage("Hello", "Hi")])}
        um = UserMessages(data)
        um.add("Is it cold today?", "Yep!")
        self.assertEqual(
            um.messages,
            deque([UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")]),
        )

    def test_pop(self):
        data = {"messages": deque([UserMessage("Hello", "Hi")])}
        um = UserMessages(data)
        message = um.pop()
        self.assertEqual(message.question, "Hello")
        self.assertEqual(message.answer, "Hi")

        message = um.pop()
        self.assertIsNone(message)

    def test_clear(self):
        data = {"messages": deque([UserMessage("Hello", "Hi")])}
        um = UserMessages(data)
        um.clear()
        self.assertEqual(len(um.messages), 0)

    def test_as_list(self):
        data = {
            "messages": deque(
                [UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")]
            )
        }
        um = UserMessages(data)
        self.assertEqual(um.as_list(), [("Hello", "Hi"), ("Is it cold today?", "Yep!")])
