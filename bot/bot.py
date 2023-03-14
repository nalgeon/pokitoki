"""Telegram chat bot built using the language model from OpenAI."""

import datetime as dt
import logging
import sys

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

from bot.chatgpt import ChatGPT
from bot.models import UserData
from bot import config

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("__main__").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

HELP_MESSAGE = """Send me a question, and I will do my best to answer it. Please be specific, as I'm not very clever.

I have a terrible memory, so don't expect me to remember any chat context (unless you put a '+' sign in front of the question).

Supported commands:

/retry – retry answering the last question
/help – show help
/version – show debug information
"""

PRIVACY_MESSAGE = (
    "⚠️ The bot does not have access to group messages, "
    "so it cannot reply in groups. Use @botfather "
    "to give the bot access (Bot Settings > Group Privacy > Turn off)"
)

BOT_COMMANDS = [
    ("retry", "retry answering the last question"),
    ("help", "show help"),
    ("version", "show debug information"),
]

# We are using the latest and greatest OpenAI model.
# There is also a previous generation (GPT-3)
# available via davinci.DaVinci class, but who needs it?
model = ChatGPT()


def main():
    # chat context persistence
    persistence = PicklePersistence(filepath=config.persistence_path)
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .post_init(post_init)
        .persistence(persistence)
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
    application.run_polling()


async def post_init(application: Application) -> None:
    """Defines bot settings."""
    await application.bot.set_my_commands(BOT_COMMANDS)


async def start_handle(update: Update, context: CallbackContext):
    """Answers the `start` command."""
    if update.effective_user.username not in config.telegram_usernames:
        text = (
            "Sorry, I don't know you. To setup your own bot, "
            "visit https://github.com/nalgeon/pokitoki"
        )
        await update.message.reply_text(text)
        return

    text = "Hi! I'm a humble ChatGPT Telegram Bot.\n\n"
    text += HELP_MESSAGE
    text += "\nLet's go!"
    if not context.bot.can_read_all_group_messages:
        text += f"\n\n{PRIVACY_MESSAGE}"
    await update.message.reply_text(text)


async def help_handle(update: Update, context: CallbackContext):
    """Answers the `help` command."""
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def version_handle(update: Update, context: CallbackContext):
    """Answers the `version` command."""
    chat = update.message.chat
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
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    """Retries asking the last question (if any)."""
    user = UserData(context.user_data)
    if not user.last_message:
        await update.message.reply_text("No message to retry 🤷‍♂️")
        return
    await _reply_to(update.message, context, question=user.last_message.question)


async def message_handle(update: Update, context: CallbackContext):
    """Answers a question from the user."""
    message = update.message or update.edited_message
    logger.debug(update)

    # the bot is meant to answer questions in private chats,
    # but it can also answer a specific question in a group when mentioned
    if message.chat.type != Chat.PRIVATE:
        if not message.text.startswith(context.bot.name):
            # ignore a message in a group unless it is mentioning the bot
            return
        question = message.text.removeprefix(context.bot.name).strip()
        if message.reply_to_message:
            # the real question is in the original message
            question = f"{question}: {message.reply_to_message.text}"
            message = message.reply_to_message
    else:
        # allow any messages in a private chat
        question = message.text

    logger.debug(f"question: {question}")
    await _reply_to(message, context, question=question)


async def error_handler(update: Update, context: CallbackContext) -> None:
    """If the bot failed to answer, prints the error and the stack trace (if any)."""
    logger.error("Exception while handling an update %s:", update, exc_info=context.error)
    message = f"⚠️ {context.error}"
    await context.bot.send_message(update.effective_chat.id, message)


async def _reply_to(message: Message, context: CallbackContext, question: str):
    """Replies to a specific question."""
    await message.chat.send_action(action="typing")

    try:
        username = message.from_user.username
        question = question or message.text
        question, history = _prepare_question(question, context)
        start = dt.datetime.now()
        answer = await model.ask(question, history)
        elapsed = int((dt.datetime.now() - start).total_seconds() * 1000)
        logger.info(
            f"question from user={username}, n_chars={len(question)}, len_history={len(history)}, took={elapsed}ms"
        )
        user = UserData(context.user_data)
        user.add_message(question, answer)
    except Exception as exc:
        error_text = f"Failed to answer. Reason: {exc}"
        logger.error(error_text)
        await message.reply_text(error_text)
        return

    await message.reply_text(answer, parse_mode=ParseMode.HTML)


def _prepare_question(question: str, context: CallbackContext) -> tuple[str, list]:
    """Returns the question along with the previous messages (for follow-up questions)."""
    user = UserData(context.user_data)
    history = []
    if question[0] == "+":
        question = question[1:].strip()
        history = list(user.messages)
    else:
        # user is asking a question 'from scratch',
        # so the bot should forget the previous history
        user.clear_messages()
    return question, history


if __name__ == "__main__":
    main()
