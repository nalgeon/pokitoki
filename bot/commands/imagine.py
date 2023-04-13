"""/imagine command."""

from typing import Awaitable
from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from bot.config import config


class ImagineCommand:
    """Generates an image according to the description."""

    def __init__(self, reply_func: Awaitable) -> None:
        self.reply_func = reply_func

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        message = update.message or update.edited_message

        if config.imagine.enabled == "none":
            await message.reply_text(
                "The `imagine` command is disabled.", parse_mode=ParseMode.MARKDOWN
            )
            return

        if (
            config.imagine.enabled == "users_only"
            and update.effective_user.username not in config.telegram.usernames
        ):
            await message.reply_text(
                "The `imagine` command is disabled for group users.", parse_mode=ParseMode.MARKDOWN
            )
            return

        if not context.args:
            await message.reply_text(
                "Please describe an image. "
                "For example:\n<code>/imagine a lazy cat on a sunny day</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        await self.reply_func(update.message, context, question=message.text)
