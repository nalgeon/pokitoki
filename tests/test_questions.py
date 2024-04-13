import datetime as dt
import unittest
from telegram import Chat, Document, Message, MessageEntity, User
from telegram.constants import ChatType
from telegram.ext import CallbackContext

from bot import questions
from bot.config import config
from tests.mocks import FakeApplication, FakeBot


class ExtractPrivateTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        bot = FakeBot("bot")
        self.context = CallbackContext(FakeApplication(bot))

    async def test_text(self):
        message = Message(
            message_id=123,
            date=dt.datetime.now(),
            chat=self.chat,
            text="What is the capital of France?",
        )
        result = await questions.extract_private(message, self.context)
        self.assertEqual(result, "What is the capital of France?")

    async def test_document(self):
        message = Message(
            message_id=123,
            date=dt.datetime.now(),
            chat=self.chat,
            caption="What is this?",
            document=Document(
                file_id="f1234", file_unique_id="f1234", file_name="file.txt", file_size=1234
            ),
        )
        result = await questions.extract_private(message, self.context)
        self.assertEqual(result, "What is this?\n\nfile.txt:\n```\nfile content\n```")

    async def test_reply(self):
        reply_message = Message(
            message_id=124, date=dt.datetime.now(), chat=self.chat, text="It is Paris."
        )
        message = Message(
            message_id=123,
            date=dt.datetime.now(),
            chat=self.chat,
            text="Isn't it London?",
            reply_to_message=reply_message,
        )
        result = await questions.extract_private(message, self.context)
        self.assertEqual(result, "+ Isn't it London?")


class ExtractGroupTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.chat = Chat(id=1, type=ChatType.GROUP)
        self.bot = FakeBot("bot")
        self.context = CallbackContext(FakeApplication(self.bot))
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")

    async def test_message(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="How are you?",
            reply_to_message=None,
        )
        result = await questions.extract_group(message, self.context)
        self.assertEqual(result, ("", message))

    async def test_reply_to_bot(self):
        bot_user = User(id=2, first_name="Bot", is_bot=True, username=self.bot.username)
        bot_message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="It's cold today.",
            from_user=bot_user,
        )
        message = Message(
            message_id=12,
            date=dt.datetime.now(),
            chat=self.chat,
            text="Is it?",
            reply_to_message=bot_message,
        )
        result = await questions.extract_group(message, self.context)
        self.assertEqual(result, ("+ Is it?", message))

    async def test_reply_to_other_user(self):
        other_message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="It's cold today.",
            from_user=self.user,
        )
        message = Message(
            message_id=12,
            date=dt.datetime.now(),
            chat=self.chat,
            text="Is it?",
            reply_to_message=other_message,
        )
        result = await questions.extract_group(message, self.context)
        self.assertEqual(result, ("", message))

    async def test_mention(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="@bot How are you?",
            entities=(MessageEntity(type=MessageEntity.MENTION, offset=0, length=4),),
            reply_to_message=None,
        )
        result = await questions.extract_group(message, self.context)
        self.assertEqual(result, ("How are you?", message))

    async def test_mention_case_insensitive(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="@Bot How are you?",
            entities=(MessageEntity(type=MessageEntity.MENTION, offset=0, length=4),),
            reply_to_message=None,
        )
        result = await questions.extract_group(message, self.context)
        self.assertEqual(result, ("How are you?", message))

    async def test_mention_in_the_middle(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="How are you @bot?",
            entities=(MessageEntity(type=MessageEntity.MENTION, offset=12, length=4),),
            reply_to_message=None,
        )
        result = await questions.extract_group(message, self.context)
        self.assertEqual(result, ("How are you ?", message))

    async def test_mention_other_user(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="@bob How are you?",
            entities=(MessageEntity(type=MessageEntity.MENTION, offset=0, length=4),),
            reply_to_message=None,
        )
        result = await questions.extract_group(message, self.context)
        self.assertEqual(result, ("", message))

    async def test_mention_in_reply(self):
        original = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="What time is it now?",
            from_user=self.user,
        )
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            text="@bot help",
            entities=(MessageEntity(type=MessageEntity.MENTION, offset=0, length=4),),
            reply_to_message=original,
        )
        result = await questions.extract_group(message, self.context)
        self.assertEqual(result, ("help: What time is it now?", original))

    async def test_mention_document(self):
        message = Message(
            message_id=11,
            date=dt.datetime.now(),
            chat=self.chat,
            caption_entities=(MessageEntity(type=MessageEntity.MENTION, offset=0, length=4),),
            caption="@bot What is this?",
            document=Document(
                file_id="f1234", file_unique_id="f1234", file_name="file.txt", file_size=1234
            ),
        )
        result, _ = await questions.extract_group(message, self.context)
        self.assertEqual(result, "What is this?\n\nfile.txt:\n```\nfile content\n```")


class TestPrepare(unittest.TestCase):
    def test_ordinary(self):
        question, is_follow_up = questions.prepare("How are you?")
        self.assertEqual(question, "How are you?")
        self.assertFalse(is_follow_up)

    def test_follow_up(self):
        question, is_follow_up = questions.prepare("+ How are you?")
        self.assertEqual(question, "How are you?")
        self.assertTrue(is_follow_up)

    def test_shortcut(self):
        config.shortcuts["translate"] = "Translate into English."
        question, is_follow_up = questions.prepare("!translate Ciao")
        self.assertEqual(question, "Translate into English.\n\nCiao")
        self.assertFalse(is_follow_up)
