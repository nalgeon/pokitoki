import logging
import traceback
import html
import json
import time

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

import chatgpt
import config


# setup
logger = logging.getLogger(__name__)

HELP_MESSAGE = """Hi! I'm a poor man's ChatGPT re-created with GPT-3 DaVinci OpenAI model.

Send me a question, and I will do my best to answer it. Please be specific, as I'm not very clever.

I also have a terrible memory, so don't expect me to remember any chat context.

Supported commands:

/retry – Regenerate last bot answer
/help – Show help
"""


async def start_handle(update: Update, context: CallbackContext):
    init_user(update, context)
    context.user_data["last_interation_timestamp"] = time.time()

    reply_text = "Hi! I'm <b>ChatGPT</b> bot implemented with GPT-3.5 OpenAI API 🤖\n\n"
    reply_text += HELP_MESSAGE

    reply_text += "\nAnd now... ask me anything!"

    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def help_handle(update: Update, context: CallbackContext):
    init_user(update, context)
    context.user_data["last_interation_timestamp"] = time.time()
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    context.user_data["last_interation_timestamp"] = time.time()

    if not context.user_data["last_message"]:
        await update.message.reply_text("No message to retry 🤷‍♂️")
        return

    last_message = context.user_data["last_message"]
    await message_handle(update, context, message=last_message)


async def message_handle(update: Update, context: CallbackContext, message=None):
    init_user(update, context)

    context.user_data["last_interation_timestamp"] = time.time()

    # send typing action
    await update.message.chat.send_action(action="typing")

    try:
        message = message or update.message.text
        context.user_data["last_message"] = message
        answer = chatgpt.ChatGPT().send_message(message)
    except Exception as e:
        error_text = f"Something went wrong during completion. Reason: {e}"
        logger.error(error_text)
        await update.message.reply_text(error_text)
        return

    await update.message.reply_text(answer, parse_mode=ParseMode.HTML)


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


def run_bot() -> None:
    persistence = PicklePersistence(filepath=config.persistence_path)

    application = ApplicationBuilder().token(config.telegram_token).persistence(persistence).build()

    # add handlers
    if len(config.allowed_telegram_usernames) == 0:
        user_filter = filters.ALL
    else:
        user_filter = filters.User(username=config.allowed_telegram_usernames)

    application.add_handler(CommandHandler("start", start_handle, filters=user_filter))
    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle)
    )
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))

    application.add_error_handler(error_handler)

    # start the bot
    print("✓ Bot started")
    application.run_polling()


def init_user(update: Update, context: CallbackContext):
    if "last_message" not in context.user_data:
        context.user_data["last_message"] = ""
    if "last_interation_timestamp" not in context.user_data:
        context.user_data["last_interation_timestamp"] = time.time()


if __name__ == "__main__":
    run_bot()
