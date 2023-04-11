"""Text message handler."""

import logging
from typing import Awaitable
from telegram import Chat, Update
from telegram.ext import CallbackContext
from bot import questions

logger = logging.getLogger(__name__)


class MessageCommand:
    """Answers a question from the user."""

    def __init__(self, reply_func: Awaitable) -> None:
        self.reply_func = reply_func

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        message = update.message or update.edited_message
        logger.debug(update)

        # the bot is meant to answer questions in private chats,
        # but it can also answer a specific question in a group when mentioned
        if message.chat.type == Chat.PRIVATE:
            question = questions.extract_private(message, context)
        else:
            question, message = questions.extract_group(message, context)

        if not question:
            # this is not a question to the bot, so ignore it
            return

        await self.reply_func(message, context, question=question)
