import datetime as dt
import unittest

from telegram import Chat, Message, User
from telegram.constants import MessageLimit
from telegram.ext import CallbackContext

from bot import bot
from tests.mocks import FakeApplication, FakeBot


class SendAnswerTest(unittest.IsolatedAsyncioTestCase):
    async def test_message(self):
        message, context = _create_message()
        await bot._send_answer(message, context, answer="My name is **AI**.")
        self.assertEqual(context.bot.text, "My name is <b>AI</b>.")

    async def test_document(self):
        message, context = _create_message()
        answer = "word " * MessageLimit.MAX_TEXT_LENGTH
        await bot._send_answer(message, context, answer=answer)
        self.assertTrue(context.bot.text.endswith("(see attachment for the rest): 11.md"))


def _create_message() -> tuple[Message, CallbackContext]:
    fake_bot = FakeBot("bot")
    chat = Chat(id=1, type=Chat.PRIVATE)
    chat.set_bot(fake_bot)
    application = FakeApplication(fake_bot)
    context = CallbackContext(application, chat_id=1, user_id=1)
    user = User(id=1, first_name="Alice", is_bot=False, username="alice")
    message = Message(message_id=11, date=dt.datetime.now(), chat=chat, from_user=user)
    message.set_bot(fake_bot)
    return message, context
