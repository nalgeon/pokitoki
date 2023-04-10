"""Generic error handler."""

import logging
from telegram import Chat, Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


class ErrorCommand:
    """If the bot failed to answer, prints the error and the stack trace (if any)."""

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        if not update:
            # telegram.error.NetworkError or a similar error, there is no chat to respond to.
            # Not sure if we should completely silence such errors.
            logger.warning("General exception: %s:", context.error)
            return

        class_name = f"{context.error.__class__.__module__}.{context.error.__class__.__qualname__}"
        error_text = f"{class_name}: {context.error}"
        logger.warning("Exception while handling an update %s: %s", update, error_text)
        text = f"⚠️ {context.error}"

        message = update.message
        reply_to_message_id = message.id if message and message.chat.type != Chat.PRIVATE else None
        await context.bot.send_message(
            update.effective_chat.id, text, reply_to_message_id=reply_to_message_id
        )
