"""Text message handler."""

import logging
import time

from telegram import Chat, Message, Update
from telegram.ext import CallbackContext

from bot import askers
from bot import questions
from bot.fetcher import Fetcher
from bot.models import UserData

logger = logging.getLogger(__name__)


class MessageCommand:
    """Answers a question from the user."""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

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

        await self.reply_to(message, context, question=question)

    async def reply_to(self, message: Message, context: CallbackContext, question: str) -> None:
        """Replies to a specific question."""
        await message.chat.send_action(action="typing", message_thread_id=message.message_thread_id)

        try:
            asker = askers.create(question)
            if message.chat.type == Chat.PRIVATE and message.forward_date:
                # this is a forwarded message, don't answer yet
                answer = "This is a forwarded message. What should I do with it?"
            else:
                answer = await self._ask_question(message, context, question, asker)

            user = UserData(context.user_data)
            user.messages.add(question, answer)
            logger.debug(user.messages)
            await asker.reply(message, context, answer)

        except Exception as exc:
            class_name = f"{exc.__class__.__module__}.{exc.__class__.__qualname__}"
            error_text = f"Failed to answer. Reason: {class_name}: {exc}"
            logger.error(error_text)
            await message.reply_text(error_text)

    async def _ask_question(
        self, message: Message, context: CallbackContext, question: str, asker: askers.Asker
    ) -> str:
        """Answers a question using the OpenAI model."""
        logger.info(
            f"-> question id={message.id}, user={message.from_user.username}, n_chars={len(question)}"
        )

        question, is_follow_up = questions.prepare(question)
        question = await self.fetcher.substitute_urls(question)
        logger.debug(f"Prepared question: {question}")

        user = UserData(context.user_data)
        if is_follow_up:
            # this is a follow-up question,
            # so the bot should retain the previous history
            history = user.messages.as_list()
        else:
            # user is asking a question 'from scratch',
            # so the bot should forget the previous history
            user.messages.clear()
            history = []

        start = time.perf_counter_ns()
        answer = await asker.ask(question, history)
        elapsed = int((time.perf_counter_ns() - start) / 1e6)

        logger.info(
            f"<- answer id={message.id}, user={message.from_user.username}, "
            f"n_chars={len(question)}, len_history={len(history)}, took={elapsed}ms"
        )
        return answer
