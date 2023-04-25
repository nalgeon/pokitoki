import datetime as dt
import unittest
from telegram import Chat, Message, MessageEntity, Update, User
from telegram.constants import ChatType
from telegram.ext import CallbackContext
from telegram.ext import filters as tg_filters

from bot import askers
from bot import bot
from bot import commands
from bot import models
from bot.config import config
from bot.filters import Filters
from tests.mocks import FakeGPT, FakeDalle, FakeApplication, FakeBot


class Helper:
    def _create_update(self, update_id: int, text: str = None, **kwargs) -> Update:
        if "user" in kwargs:
            user = kwargs["user"]
            del kwargs["user"]
        else:
            user = self.user
        message = Message(
            message_id=update_id,
            date=dt.datetime.now(),
            chat=self.chat,
            text=text,
            from_user=user,
            **kwargs,
        )
        message.set_bot(self.bot)
        return Update(update_id=update_id, message=message)


class StartTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        askers.TextAsker.model = FakeGPT()
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram.usernames = ["alice"]
        self.command = commands.Start()

    async def test_start(self):
        update = self._create_update(11)
        await self.command(update, self.context)
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
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Sorry, I don't know you"))


class HelpTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram.usernames = ["alice"]
        self.command = commands.Help()

    async def test_help(self):
        update = self._create_update(11)
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Send me a question"))


class VersionTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.version = 101
        config.telegram.usernames = ["alice", "bob"]
        config.telegram.admins = ["alice"]
        config.telegram.chat_ids = [-100500]
        config.openai.model = "gpt-4"
        config.conversation.depth = 10
        config.imagine.enabled = "none"
        config.shortcuts = {
            "translate_en": "Translate into English",
            "translate_fr": "Translate into French",
        }
        self.command = commands.Version()

    async def test_version(self):
        update = self._create_update(11)
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("<pre>Chat information:"))
        self.assertTrue("- name: @bot" in self.bot.text)
        self.assertTrue("- version: 101" in self.bot.text)
        self.assertTrue("- usernames: 2 users" in self.bot.text)
        self.assertTrue("- admins: 1 users" in self.bot.text)
        self.assertTrue("- chat IDs: [-100500]" in self.bot.text)
        self.assertTrue("- access to messages: True" in self.bot.text)

        self.assertTrue("<pre>AI information:" in self.bot.text)
        self.assertTrue("- model: gpt-4" in self.bot.text)
        self.assertTrue("- history depth: 10" in self.bot.text)
        self.assertTrue("- imagine: none" in self.bot.text)
        self.assertTrue("- shortcuts: translate_en, translate_fr" in self.bot.text)


class ConfigTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram.usernames = ["alice"]
        config.telegram.admins = ["alice"]
        self.filters = Filters()
        self.command = commands.Config(self.filters)

    async def test_help(self):
        update = self._create_update(11, "/config")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Syntax:"))

    async def test_view(self):
        config.openai.model = "gpt-3.5-turbo"
        update = self._create_update(11, "/config openai.model")
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "`gpt-3.5-turbo`")

    async def test_change(self):
        commands.config.editor.save = lambda: None
        config.openai.model = "gpt-3.5-turbo"
        update = self._create_update(11, "/config openai.model gpt-4")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("✓ Changed the `openai.model` property"))

    async def test_conversation_depth(self):
        commands.config.editor.save = lambda: None
        config.conversation.depth = 3
        user = models.UserData(self.context.user_data)
        assert user.messages.messages.maxlen == 3
        update = self._create_update(11, "/config conversation.depth 5")
        await self.command(update, self.context)
        user = models.UserData(self.context.user_data)
        self.assertEqual(user.messages.messages.maxlen, 5)

    async def test_not_changed(self):
        commands.config.editor.save = lambda: None
        config.openai.model = "gpt-3.5-turbo"
        update = self._create_update(11, "/config openai.model gpt-3.5-turbo")
        await self.command(update, self.context)
        self.assertEqual(
            self.bot.text, "✗ The `openai.model` property already equals to `gpt-3.5-turbo`"
        )

    async def test_delayed(self):
        commands.config.editor.save = lambda: None
        config.persistence_path = "./data/persistence.pkl"
        update = self._create_update(11, "/config persistence_path /tmp/data.pkl")
        await self.command(update, self.context)
        self.assertTrue("Restart the bot" in self.bot.text)

    async def test_telegram_usernames(self):
        update = self._create_update(11, '/config telegram.usernames ["alice", "bob"]')
        await self.command(update, self.context)
        self.assertEqual(self.filters.users.usernames, frozenset(["alice", "bob"]))

    async def test_telegram_admins(self):
        update = self._create_update(11, '/config telegram.admins ["alice", "bob"]')
        await self.command(update, self.context)
        self.assertEqual(self.filters.admins.usernames, frozenset(["alice", "bob"]))

    async def test_telegram_chat_ids(self):
        update = self._create_update(11, "/config telegram.chat_ids [-100500]")
        await self.command(update, self.context)
        self.assertEqual(self.filters.chats.chat_ids, frozenset([-100500]))


class RetryTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        askers.TextAsker.model = FakeGPT()
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.command = commands.Retry(bot.reply_to)
        config.telegram.usernames = ["alice"]

    async def test_retry(self):
        user_data = models.UserData(self.context.user_data)
        user_data.messages.add("What is your name?", "My name is AI.")
        update = self._create_update(11)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")


class ImagineTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        askers.ImagineAsker.model = FakeDalle()
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.command = commands.Imagine(bot.reply_to)
        config.telegram.usernames = ["alice"]

    async def test_imagine(self):
        config.imagine.enabled = "users_only"
        update = self._create_update(11, "/imagine a cat")
        self.context.args = ["a", "cat"]
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "a cat: image")

    async def test_disabled(self):
        config.imagine.enabled = "none"
        update = self._create_update(11, "/imagine a cat")
        self.context.args = ["a", "cat"]
        await self.command(update, self.context)
        self.assertTrue("command is disabled" in self.bot.text)

    async def test_users_only(self):
        config.imagine.enabled = "users_only"
        user = User(id=2, first_name="Bob", is_bot=False, username="bob")
        update = self._create_update(11, "/imagine a cat", user=user)
        self.context.args = ["a", "cat"]
        await self.command(update, self.context)
        self.assertTrue("command is disabled" in self.bot.text)

    async def test_users_and_groups(self):
        config.imagine.enabled = "users_and_groups"
        user = User(id=2, first_name="Bob", is_bot=False, username="bob")
        update = self._create_update(11, "/imagine a cat", user=user)
        self.context.args = ["a", "cat"]
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "a cat: image")


class MessageTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.ai = FakeGPT()
        askers.TextAsker.model = self.ai
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.command = commands.Message(bot.reply_to)
        config.telegram.usernames = ["alice"]

    async def test_message(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")
        self.assertEqual(self.ai.question, "What is your name?")
        self.assertEqual(self.ai.history, [])

    async def test_follow_up(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self.assertEqual(self.ai.question, "What is your name?")
        self.assertEqual(self.ai.history, [])

        update = self._create_update(12, text="+ And why is that?")
        await self.command(update, self.context)
        self.assertEqual(self.ai.question, "And why is that?")
        self.assertEqual(self.ai.history, [("What is your name?", "What is your name?")])

        update = self._create_update(13, text="+ Where are you?")
        await self.command(update, self.context)
        self.assertEqual(self.ai.question, "Where are you?")
        self.assertEqual(
            self.ai.history,
            [
                ("What is your name?", "What is your name?"),
                ("+ And why is that?", "And why is that?"),
            ],
        )

    async def test_forward(self):
        update = self._create_update(11, text="What is your name?", forward_date=dt.datetime.now())
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("This is a forwarded message"))

    async def test_document(self):
        update = self._create_update(11, text="I have so much to say" + "." * 5000)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "I have so much to... (see attachment for the rest): 11.md")

    async def test_exception(self):
        askers.TextAsker.model = FakeGPT(error=Exception("connection timeout"))
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Failed to answer"))
        self.assertTrue("connection timeout" in self.bot.text)


class MessageGroupTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        askers.TextAsker.model = FakeGPT()
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.GROUP)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.application.user_data[2] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.user_erik = User(id=2, first_name="Erik", is_bot=False, username="erik")
        self.user_bot = User(id=42, first_name="Bot", is_bot=True, username="bot")
        self.command = commands.Message(bot.reply_to)
        config.telegram.usernames = ["alice"]

    async def test_message(self):
        mention = MessageEntity(type=MessageEntity.MENTION, offset=0, length=4)
        update = self._create_update(11, text="@bot What is your name?", entities=(mention,))
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")

    async def test_no_mention(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "")


class MessageLimitTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.ai = FakeGPT()
        askers.TextAsker.model = self.ai
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.command = commands.Message(bot.reply_to)
        config.telegram.usernames = ["alice"]
        config.conversation.message_limit.count = 1
        config.conversation.message_limit.period = "minute"
        # a hack for testing purposes only
        bot.filters.users = tg_filters.User(username=config.telegram.usernames)

    async def test_known_user(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")

        update = self._create_update(12, text="Where are you from?")
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "Where are you from?")

    async def test_unknown_user(self):
        other_user = User(id=2, first_name="Bob", is_bot=False, username="bob")

        update = self._create_update(11, text="What is your name?", user=other_user)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")

        update = self._create_update(12, text="Where are you from?", user=other_user)
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Please wait"))

    async def test_expired(self):
        config.conversation.message_limit.count = 3

        user = User(id=2, first_name="Bob", is_bot=False, username="bob")
        # the counter has reached the limit, but the value has expired
        user_data = {
            "message_counter": {"value": 3, "timestamp": dt.datetime.now() - dt.timedelta(hours=1)}
        }
        self.application.user_data[user.id] = user_data
        context = CallbackContext(self.application, chat_id=1, user_id=user.id)

        update = self._create_update(11, text="What is your name?", user=user)
        await self.command(update, context)
        self.assertEqual(self.bot.text, "What is your name?")
        self.assertEqual(user_data["message_counter"]["value"], 1)

    async def test_unlimited(self):
        config.conversation.message_limit.count = 0
        other_user = User(id=2, first_name="Bob", is_bot=False, username="bob")

        update = self._create_update(11, text="What is your name?", user=other_user)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")

        update = self._create_update(12, text="Where are you from?", user=other_user)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "Where are you from?")


class ErrorTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        askers.TextAsker.model = FakeGPT()
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.application.user_data[1] = {}
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram.usernames = ["alice"]

    async def test_error(self):
        self.context.error = Exception("Something went wrong")
        command = commands.Error()
        update = self._create_update(11, "Something went wrong")
        update._effective_chat = self.chat
        await command(update, self.context)
        self.assertEqual(self.bot.text, "⚠️ Something went wrong")
