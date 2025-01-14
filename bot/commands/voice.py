"""Voice message handler."""

import logging
from typing import Awaitable

from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


class VoiceMessage:
    """Processes voice messages."""

    def __init__(self, reply_func: Awaitable) -> None:
        self.reply_func = reply_func

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        message = update.message or update.edited_message
        logger.info(f"Voice message received: from={update.effective_user.username}")

        await self.reply_func(
            update=update, message=message, context=context, question=""
        )
