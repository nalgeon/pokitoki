"""/help command."""

from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from . import common


class HelpCommand:
    """Answers the `help` command."""

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        text = common.generate_help_message(update.effective_user.username)
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
