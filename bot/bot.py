import datetime as dt
import logging
import traceback
import html
import json
import sys

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)
from telegram.constants import ParseMode

from bot.davinci import DaVinci
from bot import config

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

HELP_MESSAGE = """Send me a question, and I will do my best to answer it. Please be specific, as I'm not very clever.

I also have a terrible memory, so don't expect me to remember any chat context.

Supported commands:

/retry – retry answering the last question
/help – show help
"""

model = DaVinci()


def main() -> None:
    persistence = PicklePersistence(filepath=config.persistence_path)
    application = ApplicationBuilder().token(config.telegram_token).persistence(persistence).build()

    if len(config.telegram_usernames) == 0:
        user_filter = filters.ALL
    else:
        user_filter = filters.User(username=config.telegram_usernames)

    application.add_handler(CommandHandler("start", start_handle, filters=user_filter))
    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle)
    )
    application.add_error_handler(error_handler)

    logging.info(f"allowed users: {user_filter}")
    application.run_polling()


async def start_handle(update: Update, context: CallbackContext):
    reply_text = "Hi! I'm a poor man's ChatGPT rebuilt with the GPT-3 DaVinci OpenAI model.\n\n"
    reply_text += HELP_MESSAGE
    reply_text += "\nAnd now... ask me anything!"
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def help_handle(update: Update, context: CallbackContext):
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    if not context.user_data.get("last_question"):
        await update.message.reply_text("No message to retry 🤷‍♂️")
        return
    last_question = context.user_data["last_question"]
    await message_handle(update, context, question=last_question)


async def message_handle(update: Update, context: CallbackContext, question=None):
    message = update.message or update.edited_message
    await message.chat.send_action(action="typing")

    try:
        username = message.from_user.username
        question = question or message.text
        question, history = _prepare_question(question, context)
        start = dt.datetime.now()
        answer = model.ask(question, history)
        elapsed = int((dt.datetime.now() - start).total_seconds() * 1000)
        logger.info(
            f"question from user={username}, n_chars={len(question)}, len_history={len(history)}, took={elapsed}ms"
        )
        context.user_data["last_question"] = question
        context.user_data["last_answer"] = answer
    except Exception as e:
        error_text = f"Failed to answer. Reason: {e}"
        logger.error(error_text)
        await message.reply_text(error_text)
        return

    await message.reply_text(answer, parse_mode=ParseMode.HTML)


async def error_handler(update: Update, context: CallbackContext) -> None:
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
    history = []
    if question[0] == "+" and "last_answer" in context.user_data:
        question = question[1:].strip()
        history = [(context.user_data["last_question"], context.user_data["last_answer"])]
    return question, history


if __name__ == "__main__":
    main()
