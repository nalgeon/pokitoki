import datetime as dt
import unittest
from telegram import Chat, Message, Update, User
from telegram.constants import ChatType
from telegram.ext import CallbackContext

from bot import bot
from bot import config
from bot import models
from tests.mocks import FakeAI, FakeApplication, FakeBot


class PrivateChatTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        bot.model = FakeAI()
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram_usernames = ["alice"]

    async def test_start(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            from_user=self.user,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.start_handle(update, self.context)
        self.assertTrue(self.bot.text.startswith("Hi! I'm a humble AI-driven chat bot."))

    async def test_start_unknown(self):
        user = User(id=2, first_name="Bob", is_bot=False, username="bob")
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            from_user=user,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.start_handle(update, self.context)
        self.assertTrue(self.bot.text.startswith("Sorry, I don't know you"))

    async def test_retry(self):
        user_data = models.UserData(self.context.user_data)
        user_data.messages.add("What is your name?", "My name is AI.")
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            from_user=self.user,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.retry_handle(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")

    async def test_message(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="What is your name?",
            from_user=self.user,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.message_handle(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")

    async def test_forward(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            forward_date=dt.datetime.now(),
            chat=self.chat,
            text="What is your name?",
            from_user=self.user,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.message_handle(update, self.context)
        self.assertTrue(self.bot.text.startswith("This is a forwarded message"))

    async def test_document(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="I have so much to say" + "." * 5000,
            from_user=self.user,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.message_handle(update, self.context)
        self.assertEqual(self.bot.text, "I have so much to... (see attachment for the rest): 11.md")

    async def test_exception(self):
        bot.model = FakeAI(error=Exception("connection timeout"))
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="What is your name?",
            from_user=self.user,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.message_handle(update, self.context)
        self.assertTrue(self.bot.text.startswith("Failed to answer"))
        self.assertTrue("connection timeout" in self.bot.text)

    async def test_error(self):
        self.context.error = Exception("Something went wrong")
        update = Update(update_id=11)
        update._effective_chat = self.chat
        await bot.error_handler(update, self.context)
        self.assertEqual(self.bot.text, "⚠️ Something went wrong")


class GroupChatTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        bot.model = FakeAI()
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.GROUP)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.application.user_data[2] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user_alice = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.user_erik = User(id=2, first_name="Erik", is_bot=False, username="erik")
        self.user_bot = User(id=42, first_name="Bot", is_bot=True, username="bot")
        config.telegram_usernames = ["alice"]

    async def test_message(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="@bot What is your name?",
            from_user=self.user_alice,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.message_handle(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")

    async def test_no_mention(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="What is your name?",
            from_user=self.user_alice,
        )
        message.set_bot(self.bot)
        update = Update(update_id=11, message=message)
        await bot.message_handle(update, self.context)
        self.assertEqual(self.bot.text, "")
