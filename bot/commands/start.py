"""/start command."""

from telegram import LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from bot.config import config

from . import constants, help


class StartCommand:
    """Answers the `start` command."""

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        if update.effective_user.username not in config.telegram.usernames:
            text = (
                "Sorry, I don't know you. To setup your own bot, "
                "visit https://github.com/nalgeon/pokitoki"
            )
            await update.message.reply_text(text)
            return

        text = "Hi! I'm a humble AI-driven chat bot.\n\n"
        text += help.generate_message(update.effective_user.username)
        if not context.bot.can_read_all_group_messages:
            text += f"\n\n{constants.PRIVACY_MESSAGE}"
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
