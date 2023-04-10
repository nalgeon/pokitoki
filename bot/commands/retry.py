"""/retry command."""

from telegram import Update
from telegram.ext import CallbackContext
from bot.models import UserData
from .message import MessageCommand


class RetryCommand:
    """Retries asking the last question (if any)."""

    def __init__(self, message_cmd: MessageCommand) -> None:
        self.message_cmd = message_cmd

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        user = UserData(context.user_data)
        last_message = user.messages.pop()
        if not last_message:
            await update.message.reply_text("No message to retry 🤷‍♂️")
            return
        await self.message_cmd.reply_to(update.message, context, question=last_message.question)
