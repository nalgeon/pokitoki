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
        logger.info(
            f"Message handler called: "
            f"from={update.effective_user.username}, "
            f"text={bool(message.text)}, "
            f"voice={bool(message.voice)}"
        )

        # the bot is meant to answer questions in private chats,
        # but it can also answer a specific question in a group when mentioned
        if message.chat.type == Chat.PRIVATE:
            question = await questions.extract_private(message, context)
        else:
            question, message = await questions.extract_group(message, context)

        logger.info(f"Extracted question: {question}")

        if not question:
            # this is not a question to the bot, so ignore it
            logger.info("No question extracted, ignoring message")
            return

        await self.reply_func(
            update=update, message=message, context=context, question=question
        )
