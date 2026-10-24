"""/retry command."""

from collections.abc import Awaitable

from telegram import Update
from telegram.ext import CallbackContext

from bot.models import UserData


class RetryCommand:
    """Retries asking the last question (if any)."""

    def __init__(self, reply_func: Awaitable) -> None:
        self.reply_func = reply_func

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        user = UserData(update.effective_user.id)
        last_message = user.messages.last
        if not last_message or not last_message.question:
            await update.message.reply_text("No message to retry 🤷‍♂️")
            return
        user.messages.pop()
        await self.reply_func(
            update=update, message=update.message, context=context, question=last_message.question
        )
