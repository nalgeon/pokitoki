import datetime as dt
import unittest

from telegram import Chat, Message, MessageEntity, MessageOriginHiddenUser, Update, User
from telegram.constants import ChatType
from telegram.ext import CallbackContext
from telegram.ext import filters as tg_filters

from bot import bot, commands, db, models
from bot.config import config
from bot.filters import Filters
from tests.mocks import FakeApplication, FakeBot, FakeGPT, mock_chat


class Helper:
    def _create_update(self, update_id: int, text: str | None = None, **kwargs) -> Update:
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
        mock_chat(FakeGPT())
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
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
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram.usernames = ["alice"]
        self.command = commands.Help()

    async def test_help(self):
        update = self._create_update(11)
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Send me a question"))
        self.assertTrue("within 5 minutes" in self.bot.text)

    async def test_help_no_timeout(self):
        config.conversation.timeout = 0
        try:
            update = self._create_update(11)
            await self.command(update, self.context)
            self.assertTrue("I don't remember chat context" in self.bot.text)
        finally:
            config.conversation.timeout = 5


class VersionTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.version = "2026.10.24"
        config.telegram.usernames = ["alice", "bob"]
        config.telegram.admins = ["alice"]
        config.telegram.chat_ids = [-100500]
        config.ai.provider = "openai"
        config.ai.url = "https://api.openai.com/v1"
        config.ai.model = "gpt-4"
        config.conversation.depth = 10
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
        self.assertTrue("- version: 2026.10.24" in self.bot.text)
        self.assertTrue("- usernames: 2 users" in self.bot.text)
        self.assertTrue("- admins: 1 users" in self.bot.text)
        self.assertTrue("- chat IDs: [-100500]" in self.bot.text)
        self.assertTrue("- access to messages: True" in self.bot.text)

        self.assertTrue("<pre>AI information:" in self.bot.text)
        self.assertTrue("- provider: openai (api.openai.com)" in self.bot.text)
        self.assertTrue("- model: gpt-4" in self.bot.text)
        self.assertTrue("- history depth: 10" in self.bot.text)
        self.assertTrue("- shortcuts: translate_en, translate_fr" in self.bot.text)


class ConfigTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
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
        config.ai.model = "gpt-3.5-turbo"
        update = self._create_update(11, "/config ai.model")
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "`gpt-3.5-turbo`")

    async def test_change(self):
        commands.config.editor.save = lambda: None
        config.ai.model = "gpt-3.5-turbo"
        update = self._create_update(11, "/config ai.model gpt-4")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("✓ Changed the `ai.model` property"))

    async def test_conversation_depth(self):
        commands.config.editor.save = lambda: None
        config.conversation.depth = 3
        user = models.UserData(1)
        assert user.messages.maxlen == 3
        update = self._create_update(11, "/config conversation.depth 5")
        await self.command(update, self.context)
        user = models.UserData(1)
        self.assertEqual(user.messages.maxlen, 5)

    async def test_not_changed(self):
        commands.config.editor.save = lambda: None
        config.ai.model = "gpt-3.5-turbo"
        update = self._create_update(11, "/config ai.model gpt-3.5-turbo")
        await self.command(update, self.context)
        self.assertEqual(
            self.bot.text,
            "✗ The `ai.model` property already equals to `gpt-3.5-turbo`",
        )

    async def test_delayed(self):
        commands.config.editor.save = lambda: None
        config.db_path = "./data/pokitoki.db"
        update = self._create_update(11, "/config db_path /tmp/data.db")
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


class ModelPrivateTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram.usernames = ["alice"]
        self.command = commands.Model()

    async def test_help(self):
        update = self._create_update(11, "/model")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Syntax:"))
        self.assertEqual(models.ChatData(1).model, "")

    async def test_set(self):
        update = self._create_update(11, text="/model gpt-5")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("✓ Set model"))
        self.assertEqual(models.ChatData(1).model, "gpt-5")

    async def test_show(self):
        update = self._create_update(11, text="/model gpt-5")
        await self.command(update, self.context)

        update = self._create_update(11, text="/model")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Using model"))
        self.assertEqual(models.ChatData(1).model, "gpt-5")

    async def test_reset(self):
        update = self._create_update(11, text="/model gpt-5")
        await self.command(update, self.context)

        update = self._create_update(11, text="/model reset")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("✓ Using default model"))
        self.assertEqual(models.ChatData(1).model, "")


class ModelGroupTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.GROUP)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.alice = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.bob = User(id=2, first_name="Bob", is_bot=False, username="bob")
        config.telegram.admins = ["alice"]
        self.command = commands.Model()

    async def test_allowed(self):
        update = self._create_update(11, "/model@bot gpt-5", user=self.alice)
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("✓ Set model"))
        self.assertEqual(models.ChatData(1).model, "gpt-5")

    async def test_not_allowed(self):
        update = self._create_update(11, "/model@bot gpt-5", user=self.bob)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "")
        self.assertEqual(models.ChatData(1).model, "")


class PromptPrivateTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram.usernames = ["alice"]
        self.command = commands.Prompt()

    async def test_not_set(self):
        update = self._create_update(11, "/prompt")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Syntax:"))
        self.assertEqual(models.ChatData(1).prompt, "")

    async def test_set_custom(self):
        update = self._create_update(11, text="/prompt Laugh")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("✓ Set custom prompt"))
        self.assertEqual(models.ChatData(1).prompt, "Laugh")

    async def test_show_custom(self):
        update = self._create_update(11, text="/prompt Laugh")
        await self.command(update, self.context)

        update = self._create_update(11, text="/prompt")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("Using custom prompt"))
        self.assertEqual(models.ChatData(1).prompt, "Laugh")

    async def test_reset(self):
        update = self._create_update(11, text="/prompt Laugh")
        await self.command(update, self.context)

        update = self._create_update(11, text="/prompt reset")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("✓ Using default prompt"))
        self.assertEqual(models.ChatData(1).prompt, "")


class PromptGroupTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.GROUP)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.alice = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.bob = User(id=2, first_name="Bob", is_bot=False, username="bob")
        config.telegram.admins = ["alice"]
        self.command = commands.Prompt()

    async def test_allowed(self):
        update = self._create_update(11, "/prompt@bot Laugh", user=self.alice)
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("✓ Set custom prompt"))
        self.assertEqual(models.ChatData(1).prompt, "Laugh")

    async def test_not_allowed(self):
        update = self._create_update(11, "/prompt@bot Laugh", user=self.bob)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "")
        self.assertEqual(models.ChatData(1).prompt, "")


class RetryTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        mock_chat(FakeGPT())
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.command = commands.Retry(bot.reply_to)
        config.telegram.usernames = ["alice"]

    async def test_retry(self):
        user_data = models.UserData(1)
        user_data.messages.add("What is your name?", "My name is AI.")
        update = self._create_update(11)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")

    async def test_nothing_to_retry(self):
        update = self._create_update(11)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "No message to retry 🤷‍♂️")

    async def test_seeded_reply(self):
        # a reply to an old message seeds the history with an answer without a question
        user_data = models.UserData(1)
        user_data.messages.add("", "My name is AI.")
        update = self._create_update(11)
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "No message to retry 🤷‍♂️")
        self.assertEqual(user_data.messages.as_list(), [("", "My name is AI.")])


class NewTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.ai = FakeGPT()
        mock_chat(self.ai)
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.command = commands.New(bot.reply_to)
        config.telegram.usernames = ["alice"]

    async def test_new(self):
        models.UserData(1).messages.add("What is your name?", "My name is AI.")
        context = CallbackContext(self.application, chat_id=1, user_id=1)
        context.args = []
        update = self._create_update(11, text="/new")
        await self.command(update, context)
        self.assertEqual(self.bot.text, "Started a new conversation.")
        self.assertEqual(models.UserData(1).messages.as_list(), [])

    async def test_new_with_question(self):
        models.UserData(1).messages.add("What is your name?", "My name is AI.")
        context = CallbackContext(self.application, chat_id=1, user_id=1)
        context.args = ["Where", "are", "you?"]
        update = self._create_update(11, text="/new Where are you?")
        await self.command(update, context)
        self.assertEqual(self.ai.question, "Where are you?")
        self.assertEqual(self.ai.history, [])
        self.assertEqual(
            models.UserData(1).messages.as_list(), [("/new Where are you?", "Where are you?")]
        )


class MessageTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        self.ai = FakeGPT()
        mock_chat(self.ai)
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        self.command = commands.Message(bot.reply_to)
        config.telegram.usernames = ["alice"]

    def _expire_history(self):
        db.conn.execute("update messages set created_at = datetime('now', '-6 minutes')")

    async def test_message(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self.assertEqual(self.bot.text, "What is your name?")
        self.assertEqual(self.ai.question, "What is your name?")
        self.assertEqual(self.ai.history, [])

    async def test_continue_within_timeout(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        update = self._create_update(12, text="And why is that?")
        await self.command(update, self.context)
        self.assertEqual(self.ai.history, [("What is your name?", "What is your name?")])

    async def test_new_after_timeout(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self._expire_history()
        update = self._create_update(12, text="Where are you?")
        await self.command(update, self.context)
        self.assertEqual(self.ai.history, [])
        self.assertEqual(
            models.UserData(1).messages.as_list(), [("Where are you?", "Where are you?")]
        )

    async def test_timeout_disabled(self):
        config.conversation.timeout = 0
        try:
            update = self._create_update(11, text="What is your name?")
            await self.command(update, self.context)
            update = self._create_update(12, text="Where are you?")
            await self.command(update, self.context)
            self.assertEqual(self.ai.history, [])
        finally:
            config.conversation.timeout = 5

    async def test_follow_up_after_timeout(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self._expire_history()
        update = self._create_update(12, text="+ And why is that?")
        await self.command(update, self.context)
        self.assertEqual(self.ai.history, [("What is your name?", "What is your name?")])

    async def test_reply_within_timeout(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        answer = self._create_update(12, text="My name is AI.", user=self.bot.user).message
        update = self._create_update(13, text="And why is that?", reply_to_message=answer)
        await self.command(update, self.context)
        self.assertEqual(self.ai.history, [("What is your name?", "What is your name?")])

    async def test_reply_after_timeout(self):
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self._expire_history()
        answer = self._create_update(5, text="I'm in the cloud.", user=self.bot.user).message
        update = self._create_update(12, text="Which one?", reply_to_message=answer)
        await self.command(update, self.context)
        self.assertEqual(self.ai.question, "Which one?")
        self.assertEqual(self.ai.history, [("", "I'm in the cloud.")])

        # the next question continues the conversation started from the reply
        update = self._create_update(13, text="Is it cold there?")
        await self.command(update, self.context)
        self.assertEqual(
            self.ai.history, [("", "I'm in the cloud."), ("+ Which one?", "Which one?")]
        )

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
        origin = MessageOriginHiddenUser(date=dt.datetime.now(), sender_user_name="Bob")
        update = self._create_update(11, text="What is your name?", forward_origin=origin)
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("This is a forwarded message"))

    async def test_document(self):
        update = self._create_update(11, text="I have so much to say" + "." * 5000)
        await self.command(update, self.context)
        self.assertEqual(
            self.bot.text, "I have so much to... (see attachment for the rest): 11.txt"
        )

    async def test_exception(self):
        ai = FakeGPT(error=Exception("connection timeout"))
        mock_chat(ai)
        update = self._create_update(11, text="What is your name?")
        await self.command(update, self.context)
        self.assertTrue(self.bot.text.startswith("⚠️ builtins.Exception:"))
        self.assertTrue("connection timeout" in self.bot.text)


class MessageGroupTest(unittest.IsolatedAsyncioTestCase, Helper):
    def setUp(self):
        mock_chat(FakeGPT())
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.GROUP)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
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
        mock_chat(self.ai)
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
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
        expired_at = dt.datetime.now() - dt.timedelta(hours=1)
        db.conn.execute(
            "insert into users (id, message_count, message_count_at) values (?, ?, ?)",
            (user.id, 3, expired_at.isoformat()),
        )
        context = CallbackContext(self.application, chat_id=1, user_id=user.id)

        update = self._create_update(11, text="What is your name?", user=user)
        await self.command(update, context)
        self.assertEqual(self.bot.text, "What is your name?")
        self.assertEqual(models.UserData(user.id).message_counter.value, 1)

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
        mock_chat(FakeGPT())
        self.bot = FakeBot("bot")
        self.chat = Chat(id=1, type=ChatType.PRIVATE)
        self.chat.set_bot(self.bot)
        self.application = FakeApplication(self.bot)
        self.context = CallbackContext(self.application, chat_id=1, user_id=1)
        self.user = User(id=1, first_name="Alice", is_bot=False, username="alice")
        config.telegram.usernames = ["alice"]

    async def test_error(self):
        self.context.error = Exception("Something went wrong")
        command = commands.Error()
        update = self._create_update(11, "Something went wrong")
        update._effective_chat = self.chat
        await command(update, self.context)
        self.assertEqual(self.bot.text, "⚠️ builtins.Exception: Something went wrong")
