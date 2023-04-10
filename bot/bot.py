"""Telegram chat bot built using the language model from OpenAI."""

import logging
import sys
import time
from typing import Optional

from telegram import Chat, Message, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)
from telegram.constants import ParseMode

from bot.config import config
from bot import questions
from bot import askers
from bot.fetcher import Fetcher
from bot.models import UserData

HELP_MESSAGE = """Send me a question, and I will do my best to answer it. Please be specific, as I'm not very clever.

I don't remember chat context by default. To ask follow-up questions, reply to my messages or start your questions with a '+' sign.

Built-in commands:
{commands}{admin_commands}

AI shortcuts:
{shortcuts}

[More features →](https://github.com/nalgeon/pokitoki#readme)
"""

PRIVACY_MESSAGE = (
    "⚠️ The bot does not have access to group messages, "
    "so it cannot reply in groups. Use @botfather "
    "to give the bot access (Bot Settings > Group Privacy > Turn off)"
)

BOT_COMMANDS = [
    ("retry", "retry the last question"),
    ("imagine", "generate described image"),
    ("version", "show debug information"),
    ("help", "show help"),
]

ADMIN_COMMANDS = {
    "config": "view or edit the config",
}

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("bot.ai.chatgpt").setLevel(logging.INFO)
logging.getLogger("bot.questions").setLevel(logging.INFO)
logging.getLogger("__main__").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# retrieves remote content
fetcher = Fetcher()


class Filters:
    """Filters for the incoming Telegram messages."""

    user: filters.BaseFilter
    admin: filters.BaseFilter
    chat: filters.BaseFilter

    user_or_chat: filters.BaseFilter
    admin_private: filters.BaseFilter
    message: filters.BaseFilter

    @classmethod
    def init(cls):
        """Defines users and chats that are allowed to use the bot."""
        if config.telegram.usernames:
            cls.user = filters.User(username=config.telegram.usernames)
            cls.chat = filters.Chat(chat_id=config.telegram.chat_ids)
        else:
            cls.user = filters.ALL
            cls.chat = filters.ALL

        if config.telegram.admins:
            cls.admin = filters.User(username=config.telegram.admins)
        else:
            cls.admin = filters.User(username=[])

        cls.user_or_chat = cls.user | cls.chat
        cls.admin_private = cls.admin & filters.ChatType.PRIVATE
        cls.message = filters.TEXT & ~filters.COMMAND & cls.user_or_chat

    @classmethod
    def reload(cls):
        """Reloads users and chats from config."""
        if cls.user == filters.ALL and config.telegram.usernames:
            # cannot update the filter from ALL to specific usernames without a restart
            raise Exception("Restart the bot for changes to take effect")
        cls.user.usernames = config.telegram.usernames
        cls.chat.chat_ids = config.telegram.chat_ids
        cls.admin.usernames = config.telegram.admins


def main():
    # chat context persistence
    persistence = PicklePersistence(filepath=config.persistence_path)
    application = (
        ApplicationBuilder()
        .token(config.telegram.token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .persistence(persistence)
        .concurrent_updates(True)
        .get_updates_http_version("1.1")
        .http_version("1.1")
        .build()
    )

    # allow bot only for the selected users
    Filters.init()

    # these commands are only allowed for selected users
    application.add_handler(CommandHandler("start", start_handle))
    application.add_handler(CommandHandler("help", help_handle, filters=Filters.user))
    application.add_handler(CommandHandler("version", version_handle, filters=Filters.user))
    # these commands are allowed for both selected users and group members
    application.add_handler(CommandHandler("retry", retry_handle, filters=Filters.user_or_chat))
    application.add_handler(CommandHandler("imagine", imagine_handle, filters=Filters.user_or_chat))
    # admin-only commands
    application.add_handler(CommandHandler("config", config_handle, filters=Filters.admin_private))
    # default action is to reply to a message
    application.add_handler(MessageHandler(Filters.message, message_handle))
    application.add_error_handler(error_handler)

    # start the bot
    application.run_polling()


async def post_init(application: Application) -> None:
    """Defines bot settings."""
    bot = application.bot
    logging.info(f"config: file={config.filename}, version={config.version}")
    logging.info(f"allowed users: {config.telegram.usernames}")
    logging.info(f"allowed chats: {config.telegram.chat_ids}")
    logging.info(f"admins: {config.telegram.admins}")
    logging.info(f"model name: {config.openai.model}")
    logging.info(f"bot: username={bot.username}, id={bot.id}")
    await bot.set_my_commands(BOT_COMMANDS)


async def post_shutdown(application: Application) -> None:
    """Frees acquired resources."""
    await fetcher.close()


async def start_handle(update: Update, context: CallbackContext):
    """Answers the `start` command."""
    if update.effective_user.username not in config.telegram.usernames:
        text = (
            "Sorry, I don't know you. To setup your own bot, "
            "visit https://github.com/nalgeon/pokitoki"
        )
        await update.message.reply_text(text)
        return

    text = "Hi! I'm a humble AI-driven chat bot.\n\n"
    text += _generate_help_message(update.effective_user.username)
    if not context.bot.can_read_all_group_messages:
        text += f"\n\n{PRIVACY_MESSAGE}"
    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )


async def help_handle(update: Update, context: CallbackContext):
    """Answers the `help` command."""
    text = _generate_help_message(update.effective_user.username)
    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )


async def version_handle(update: Update, context: CallbackContext):
    """Answers the `version` command."""
    chat = update.message.chat
    # chat information
    text = (
        "<pre>"
        "Chat information:\n"
        f"- id: {chat.id}\n"
        f"- title: {chat.title}\n"
        f"- type: {chat.type}"
        "</pre>"
    )
    bot = await context.bot.get_me()
    usernames = (
        "all" if not config.telegram.usernames else f"{len(config.telegram.usernames)} users"
    )
    admins = "none" if not config.telegram.admins else f"{len(config.telegram.admins)} users"

    # bot information
    text += (
        "\n\n<pre>"
        "Bot information:\n"
        f"- id: {bot.id}\n"
        f"- name: {bot.name}\n"
        f"- version: {config.version}\n"
        f"- usernames: {usernames}\n"
        f"- admins: {admins}\n"
        f"- chat IDs: {config.telegram.chat_ids}\n"
        f"- access to messages: {bot.can_read_all_group_messages}"
        "</pre>"
    )
    if not bot.can_read_all_group_messages:
        text += f"\n\n{PRIVACY_MESSAGE}"

    # AI information
    text += (
        "\n\n<pre>"
        "AI information:\n"
        f"- model: {config.openai.model}\n"
        f"- history depth: {config.max_history_depth}\n"
        f"- imagine: {config.imagine}\n"
        f"- shortcuts: {', '.join(config.shortcuts.keys())}"
        "</pre>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def config_handle(update: Update, context: CallbackContext):
    """Displays or changes config properties."""
    message = update.message or update.edited_message

    parts = message.text.split()
    if len(parts) == 1:
        # /config without arguments
        text = (
            "Syntax:\n<code>/config property [value]</code>\n\n"
            "E.g. to view the property value:\n<code>/config openai.prompt</code>\n\n"
            "E.g. to change the property value:\n<code>/config openai.prompt You are an AI assistant</code>"
        )
        await message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    if len(parts) == 2:
        # view config property (`/config {property}`)
        property = parts[1]
        value = config.get_value(property) or "(empty)"
        await message.reply_text(f"`{value}`", parse_mode=ParseMode.MARKDOWN)
        return

    # change config property (`/config {property} {value}`)
    property = parts[1]
    old_value = config.get_value(property) or "(empty)"
    value = " ".join(parts[2:])
    has_changed, is_immediate = config.set_value(property, value)

    if not has_changed:
        text = f"✗ The `{property}` property already equals to `{value}`"
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    config.save()
    Filters.reload()
    text = f"✓ Changed the `{property}` property: `{old_value}` → `{value}`"
    if not is_immediate:
        text += "\n❗️Restart the bot for changes to take effect."
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def imagine_handle(update: Update, context: CallbackContext):
    """Generates an image according to the description."""
    if not config.imagine:
        await update.message.reply_text(
            f"The `imagine` command is disabled. You can enable it in the `{config.filename}` file.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    if not context.args:
        await update.message.reply_text(
            "Please describe an image. For example:\n<code>/imagine a lazy cat on a sunny day</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    await message_handle(update, context)


async def retry_handle(update: Update, context: CallbackContext):
    """Retries asking the last question (if any)."""
    user = UserData(context.user_data)
    last_message = user.messages.pop()
    if not last_message:
        await update.message.reply_text("No message to retry 🤷‍♂️")
        return
    await _reply_to(update.message, context, question=last_message.question)


async def message_handle(update: Update, context: CallbackContext):
    """Answers a question from the user."""
    message = update.message or update.edited_message
    logger.debug(update)

    # the bot is meant to answer questions in private chats,
    # but it can also answer a specific question in a group when mentioned
    if message.chat.type == Chat.PRIVATE:
        question = questions.extract_private(message, context)
    else:
        question, message = questions.extract_group(message, context)

    if not question:
        # this is not a question to the bot, so ignore it
        return

    await _reply_to(message, context, question=question)


async def error_handler(update: Update, context: CallbackContext) -> None:
    """If the bot failed to answer, prints the error and the stack trace (if any)."""
    if not update:
        # telegram.error.NetworkError or a similar error, there is no chat to respond to.
        # Not sure if we should completely silence such errors.
        logger.warning("General exception: %s:", context.error)
        return
    class_name = f"{context.error.__class__.__module__}.{context.error.__class__.__qualname__}"
    error_text = f"{class_name}: {context.error}"
    logger.warning("Exception while handling an update %s: %s", update, error_text)
    text = f"⚠️ {context.error}"
    await context.bot.send_message(
        update.effective_chat.id, text, reply_to_message_id=_get_reply_message_id(update.message)
    )


async def _reply_to(message: Message, context: CallbackContext, question: str):
    """Replies to a specific question."""
    await message.chat.send_action(action="typing", message_thread_id=message.message_thread_id)

    try:
        asker = askers.create(question)
        if message.chat.type == Chat.PRIVATE and message.forward_date:
            # this is a forwarded message, don't answer yet
            answer = "This is a forwarded message. What should I do with it?"
        else:
            answer = await _ask_question(message, context, question, asker)

        user = UserData(context.user_data)
        user.messages.add(question, answer)
        logger.debug(user.messages)
        await asker.reply(message, context, answer)

    except Exception as exc:
        class_name = f"{exc.__class__.__module__}.{exc.__class__.__qualname__}"
        error_text = f"Failed to answer. Reason: {class_name}: {exc}"
        logger.error(error_text)
        await message.reply_text(error_text)


async def _ask_question(
    message: Message, context: CallbackContext, question: str, asker: askers.Asker
) -> str:
    """Answers a question using the OpenAI model."""
    logger.info(
        f"-> question id={message.id}, user={message.from_user.username}, n_chars={len(question)}"
    )

    question, is_follow_up = questions.prepare(question)
    question = await fetcher.substitute_urls(question)
    logger.debug(f"Prepared question: {question}")

    user = UserData(context.user_data)
    if is_follow_up:
        # this is a follow-up question,
        # so the bot should retain the previous history
        history = user.messages.as_list()
    else:
        # user is asking a question 'from scratch',
        # so the bot should forget the previous history
        user.messages.clear()
        history = []

    start = time.perf_counter_ns()
    answer = await asker.ask(question, history)
    elapsed = int((time.perf_counter_ns() - start) / 1e6)

    logger.info(
        f"<- answer id={message.id}, user={message.from_user.username}, "
        f"n_chars={len(question)}, len_history={len(history)}, took={elapsed}ms"
    )
    return answer


def _generate_help_message(username) -> str:
    """Generates a help message, including a list of allowed commands."""
    # user commands
    commands = "\n".join(f"/{cmd} - {descr}" for cmd, descr in BOT_COMMANDS)

    # admin commands
    admin_commands = ""
    if username in config.telegram.admins:
        admin_commands += "\n\nAdmin-only commads:\n"
        admin_commands += f'/config - {ADMIN_COMMANDS["config"]}\n'
    admin_commands = admin_commands.rstrip()

    # shortcuts
    if config.shortcuts:
        shortcuts = "\n".join(f"`!{shortcut}`" for shortcut in config.shortcuts)
    else:
        shortcuts = "none"

    return HELP_MESSAGE.format(
        commands=commands, admin_commands=admin_commands, shortcuts=shortcuts
    )


def _get_reply_message_id(message: Message) -> Optional[int]:
    """Returns message id for group chats and None for private chats."""
    if not message or message.chat.type == Chat.PRIVATE:
        return None
    return message.id


if __name__ == "__main__":
    main()
