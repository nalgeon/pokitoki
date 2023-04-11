"""/retry command."""

from typing import Awaitable
from telegram import Update
from telegram.ext import CallbackContext
from bot.models import UserData


class RetryCommand:
    """Retries asking the last question (if any)."""

    def __init__(self, reply_func: Awaitable) -> None:
        self.reply_func = reply_func

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        user = UserData(context.user_data)
        last_message = user.messages.pop()
        if not last_message:
            await update.message.reply_text("No message to retry 🤷‍♂️")
            return
        await self.reply_func(update.message, context, question=last_message.question)
