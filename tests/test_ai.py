import unittest
from bot.config import config
from bot.ai import chatgpt
from bot.models import UserMessage


class ModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = chatgpt.Model(config.openai.model)

    def test_generate_messages(self):
        history = [UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")]
        messages = self.model._generate_messages("What's your name?", history)
        self.assertEqual(len(messages), 6)

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], config.openai.prompt)

        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Hello")

        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[2]["content"], "Hi")

        self.assertEqual(messages[3]["role"], "user")
        self.assertEqual(messages[3]["content"], "Is it cold today?")

        self.assertEqual(messages[4]["role"], "assistant")
        self.assertEqual(messages[4]["content"], "Yep!")

        self.assertEqual(messages[5]["role"], "user")
        self.assertEqual(messages[5]["content"], "What's your name?")


class ShortenTest(unittest.TestCase):
    def test_do_not_shorten(self):
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "Hello"},
        ]
        shortened = chatgpt.shorten(messages, length=11)
        self.assertEqual(shortened, messages)

    def test_remove_messages_1(self):
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "What is your name?"},
            {"role": "assistant", "content": "My name is Alice."},
            {"role": "user", "content": "Is it cold today?"},
        ]
        shortened = chatgpt.shorten(messages, length=11)
        self.assertEqual(
            shortened,
            [
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "user", "content": "Is it cold today?"},
            ],
        )

    def test_remove_messages_2(self):
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "What is your name?"},
            {"role": "assistant", "content": "My name is Alice."},
            {"role": "user", "content": "Is it cold today?"},
        ]
        shortened = chatgpt.shorten(messages, length=20)
        self.assertEqual(
            shortened,
            [
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "assistant", "content": "My name is Alice."},
                {"role": "user", "content": "Is it cold today?"},
            ],
        )

    def test_shorten_question(self):
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "Is it cold today? I think it's rather cold"},
        ]
        shortened = chatgpt.shorten(messages, length=11)
        self.assertEqual(
            shortened,
            [
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "user", "content": "Is it cold today?"},
            ],
        )
