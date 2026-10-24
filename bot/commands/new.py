"""/new command."""

from collections.abc import Awaitable

from telegram import Update
from telegram.ext import CallbackContext

from bot.models import UserData


class NewCommand:
    """Starts a new conversation, optionally with a question."""

    def __init__(self, reply_func: Awaitable) -> None:
        self.reply_func = reply_func

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        user = UserData(update.effective_user.id)
        user.messages.clear()
        if not context.args:
            await update.message.reply_text("Started a new conversation.")
            return
        await self.reply_func(
            update=update, message=update.message, context=context, question=update.message.text
        )
