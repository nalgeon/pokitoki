"""Telegram chat bot built using the language model from OpenAI."""

import datetime as dt
import logging
import traceback
import html
import json
import sys

from telegram import Update
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

logger = logging.getLogger(__name__)

HELP_MESSAGE = """Send me a question, and I will do my best to answer it. Please be specific, as I'm not very clever.

I also have a terrible memory, so don't expect me to remember any chat context (unless you put a '+' sign in front of the question).

Supported commands:

/retry – retry answering the last question
/help – show help
"""

BOT_COMMANDS = [
    ("start", "what is this bot about?"),
    ("retry", "retry answering the last question"),
    ("help", "show help"),
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
    else:
        user_filter = filters.User(username=config.telegram_usernames)

    # available commands: start, help, retry and message (default)
    application.add_handler(CommandHandler("start", start_handle, filters=user_filter))
    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle)
    )
    application.add_error_handler(error_handler)

    # start the bot
    bot_id, _, _ = config.telegram_token.partition(":")
    logging.info(f"bot id: {bot_id}")
    logging.info(f"allowed users: {user_filter}")
    application.run_polling()


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)


async def start_handle(update: Update, context: CallbackContext):
    """Answers the `start` command."""
    reply_text = "Hi! I'm a humble ChatGPT Telegram Bot.\n\n"
    reply_text += HELP_MESSAGE
    reply_text += "\nAnd now... ask me anything!"
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def help_handle(update: Update, context: CallbackContext):
    """Answers the `help` command."""
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    """Retries asking the last question (if any)."""
    user = UserData(context.user_data)
    if not user.last_message:
        await update.message.reply_text("No message to retry 🤷‍♂️")
        return
    await message_handle(update, context, question=user.last_message.question)


async def message_handle(update: Update, context: CallbackContext, question=None):
    """Answers a question from the user."""
    message = update.message or update.edited_message
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


async def error_handler(update: Update, context: CallbackContext) -> None:
    """If the bot failed to answer, prints the error and the stack trace (if any)."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # collect error message
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)[:2000]
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    await context.bot.send_message(update.effective_chat.id, message, parse_mode=ParseMode.HTML)


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
