"""/imagine command."""

from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from bot.config import config
from .message import MessageCommand


class ImagineCommand:
    """Generates an image according to the description."""

    def __init__(self, message_cmd: MessageCommand) -> None:
        self.message_cmd = message_cmd

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        message = update.message or update.edited_message

        if not config.imagine:
            await message.reply_text(
                "The `imagine` command is disabled. "
                f"You can enable it in the `{config.filename}` file.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        if not context.args:
            await message.reply_text(
                "Please describe an image. "
                "For example:\n<code>/imagine a lazy cat on a sunny day</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        await self.message_cmd.reply_to(update.message, context, question=message.text)
