import datetime as dt
import unittest
from telegram import Chat, Message, User
from telegram.ext import CallbackContext

from bot import askers
from bot.askers import ImagineAsker, TextAsker
from tests.mocks import FakeApplication, FakeBot, FakeDalle, FakeGPT


class TextAskerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.ai = FakeGPT()
        TextAsker.model = self.ai

    async def test_ask(self):
        asker = TextAsker()
        await asker.ask(question="What is your name?", history=[("Hello", "Hi")])
        self.assertEqual(self.ai.question, "What is your name?")
        self.assertEqual(self.ai.history, [("Hello", "Hi")])

    async def test_reply(self):
        message, context = _create_message()
        asker = TextAsker()
        await asker.reply(message, context, answer="My name is ChatGPT.")
        self.assertEqual(context.bot.text, "My name is ChatGPT.")


class ImagineAskerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.ai = FakeDalle()
        ImagineAsker.model = self.ai

    async def test_ask(self):
        asker = ImagineAsker()
        await asker.ask(question="a cat 256x256", history=[])
        self.assertEqual(self.ai.prompt, "a cat")
        self.assertEqual(self.ai.size, "256x256")

    async def test_reply(self):
        asker = ImagineAsker()
        await asker.ask(question="a cat 256x256", history=[])
        message, context = _create_message()
        await asker.reply(message, context, answer="https://image.url")
        self.assertEqual(context.bot.text, "a cat: https://image.url")

    def test_extract_size(self):
        asker = ImagineAsker()
        size = asker._extract_size(question="a cat 256x256")
        self.assertEqual(size, "256x256")
        size = asker._extract_size(question="a cat 512x512")
        self.assertEqual(size, "512x512")
        size = asker._extract_size(question="a cat 1024x1024")
        self.assertEqual(size, "1024x1024")
        size = asker._extract_size(question="a cat 256")
        self.assertEqual(size, "256x256")
        size = asker._extract_size(question="a cat 256px")
        self.assertEqual(size, "256x256")
        size = asker._extract_size(question="a cat 384")
        self.assertEqual(size, "512x512")

    def test_extract_caption(self):
        asker = ImagineAsker()
        caption = asker._extract_caption(question="a cat 256x256")
        self.assertEqual(caption, "a cat")
        caption = asker._extract_caption(question="a cat 512x512")
        self.assertEqual(caption, "a cat")
        caption = asker._extract_caption(question="a cat 1024x1024")
        self.assertEqual(caption, "a cat")
        caption = asker._extract_caption(question="a cat 256")
        self.assertEqual(caption, "a cat")
        caption = asker._extract_caption(question="a cat 256px")
        self.assertEqual(caption, "a cat")
        caption = asker._extract_caption(question="a cat 384")
        self.assertEqual(caption, "a cat 384")


class CreateTest(unittest.TestCase):
    def test_text_asker(self):
        asker = askers.create("What is your name?")
        self.assertIsInstance(asker, TextAsker)

    def test_imagine_asker(self):
        asker = askers.create("/imagine a cat")
        self.assertIsInstance(asker, ImagineAsker)


def _create_message() -> tuple[Message, CallbackContext]:
    bot = FakeBot("bot")
    chat = Chat(id=1, type=Chat.PRIVATE)
    chat.set_bot(bot)
    application = FakeApplication(bot)
    application.user_data[1] = {}
    context = CallbackContext(application, chat_id=1, user_id=1)
    user = User(id=1, first_name="Alice", is_bot=False, username="alice")
    message = Message(
        message_id=11,
        date=dt.datetime.now(),
        chat=chat,
        from_user=user,
    )
    message.set_bot(bot)
    return message, context
