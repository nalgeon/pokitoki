"""Telegram chat bot built using the language model from OpenAI."""

import logging
import sys
import time

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

from bot import config
from bot import questions
from bot import askers
from bot.fetcher import Fetcher
from bot.models import UserData

HELP_MESSAGE = """Send me a question, and I will do my best to answer it. Please be specific, as I'm not very clever.

I don't remember chat context by default. To ask follow-up questions, reply to my messages or start your questions with a '+' sign.

Supported commands:

{commands}
"""

PRIVACY_MESSAGE = (
    "⚠️ The bot does not have access to group messages, "
    "so it cannot reply in groups. Use @botfather "
    "to give the bot access (Bot Settings > Group Privacy > Turn off)"
)

BOT_COMMANDS = [
    ("help", "show help"),
    ("imagine", "generate described image"),
    ("retry", "retry the last question"),
    ("version", "show debug information"),
]

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


def main():
    # chat context persistence
    persistence = PicklePersistence(filepath=config.persistence_path)
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .persistence(persistence)
        .get_updates_http_version("1.1")
        .http_version("1.1")
        .build()
    )

    # allow bot only for the selected users
    if len(config.telegram_usernames) == 0:
        user_filter = filters.ALL
        chat_filter = filters.ALL
    else:
        user_filter = filters.User(username=config.telegram_usernames)
        chat_filter = filters.Chat(chat_id=config.telegram_chat_ids)

    # available commands: start, help, retry
    application.add_handler(CommandHandler("start", start_handle))
    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))
    application.add_handler(CommandHandler("version", version_handle, filters=user_filter))
    application.add_handler(CommandHandler("imagine", imagine_handle, filters=user_filter))
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))
    # default action is to reply to a message
    message_filter = filters.TEXT & ~filters.COMMAND & (user_filter | chat_filter)
    application.add_handler(MessageHandler(message_filter, message_handle))
    application.add_error_handler(error_handler)

    # start the bot
    bot_id, _, _ = config.telegram_token.partition(":")
    logging.info(f"bot id: {bot_id}, version: {config.version}")
    logging.info(f"allowed users: {config.telegram_usernames}")
    logging.info(f"allowed chats: {config.telegram_chat_ids}")
    logging.info(f"model name: {config.openai_model}")
    application.run_polling()


async def post_init(application: Application) -> None:
    """Defines bot settings."""
    await application.bot.set_my_commands(BOT_COMMANDS)


async def post_shutdown(application: Application) -> None:
    """Frees acquired resources."""
    await fetcher.close()


async def start_handle(update: Update, context: CallbackContext):
    """Answers the `start` command."""
    if update.effective_user.username not in config.telegram_usernames:
        text = (
            "Sorry, I don't know you. To setup your own bot, "
            "visit https://github.com/nalgeon/pokitoki"
        )
        await update.message.reply_text(text)
        return

    text = "Hi! I'm a humble AI-driven chat bot.\n\n"
    text += _generate_help_message()
    text += "\nLet's go!"
    if not context.bot.can_read_all_group_messages:
        text += f"\n\n{PRIVACY_MESSAGE}"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_handle(update: Update, context: CallbackContext):
    """Answers the `help` command."""
    message = _generate_help_message()
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


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
        "all" if not config.telegram_usernames else f"{len(config.telegram_usernames)} users"
    )

    # bot information
    text += (
        "\n\n<pre>"
        "Bot information:\n"
        f"- id: {bot.id}\n"
        f"- name: {bot.name}\n"
        f"- version: {config.version}\n"
        f"- usernames: {usernames}\n"
        f"- chat IDs: {config.telegram_chat_ids}\n"
        f"- access to messages: {bot.can_read_all_group_messages}"
        "</pre>"
    )
    if not bot.can_read_all_group_messages:
        text += f"\n\n{PRIVACY_MESSAGE}"

    # AI information
    text += (
        "\n\n<pre>"
        "AI information:\n"
        f"- model: {config.openai_model}\n"
        f"- history depth: {config.max_history_depth}\n"
        f"- imagine: {config.imagine}\n"
        f"- shortcuts: {list(config.shortcuts.keys())}"
        "</pre>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def imagine_handle(update: Update, context: CallbackContext):
    """Generates an image according to the description."""
    if not config.imagine:
        await update.message.reply_text(
            "The `imagine` command is disabled. You can enable it in the `config.yml` file.",
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
    message = f"⚠️ {context.error}"
    await context.bot.send_message(update.effective_chat.id, message)


async def _reply_to(message: Message, context: CallbackContext, question: str):
    """Replies to a specific question."""
    logger.debug(f"question: {question}")
    await message.chat.send_action(action="typing")

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
        f"question from user={message.from_user.username}, "
        f"n_chars={len(question)}, len_history={len(history)}, took={elapsed}ms"
    )
    return answer


def _generate_help_message() -> str:
    """Generates a help message, including a list of allowed commands."""
    commands = "\n".join(f"/{cmd} - {descr}" for cmd, descr in BOT_COMMANDS)
    return HELP_MESSAGE.format(commands=commands)


if __name__ == "__main__":
    main()
