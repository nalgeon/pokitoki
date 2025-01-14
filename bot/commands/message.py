"""Text message handler."""

import logging
from typing import Awaitable

from telegram import Chat, Update
from telegram.ext import CallbackContext

from bot import questions
from bot.file_processor import FileProcessor
from bot.config import config
from bot.models import UserData

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
            f"voice={bool(message.voice)}, "
            f"document={message.document.file_name if message.document else None}, "
            f"photo={bool(message.photo)}, "
            f"caption={bool(message.caption)}"
        )

        # Сначала обрабатываем файлы, если они есть
        file_content = None
        if (message.document or message.photo) and config.files.enabled:
            file_processor = FileProcessor()
            file_content = await file_processor.process_files(
                documents=[message.document] if message.document else [],
                photos=message.photo if message.photo else [],
            )

        # Извлекаем текст сообщения
        if message.chat.type == Chat.PRIVATE:
            question = await questions.extract_private(message, context)
        else:
            question, message = await questions.extract_group(message, context)

        # Если есть файл, но нет текста
        if file_content and not question:
            user = UserData(context.user_data)
            # Сохраняем содержимое файла в контексте пользователя
            user.data["last_file_content"] = file_content
            # Запрашиваем что делать с файлом
            await message.reply_text("This is a file. What should I do with it?")
            return

        # Если есть вопрос к предыдущему файлу
        if question and not file_content:
            user = UserData(context.user_data)
            file_content = user.data.pop("last_file_content", None)
            if file_content:
                question = f"{question}\n\n{file_content}"

        # Если нет ни файла, ни текста - игнорируем
        if not file_content and not question:
            logger.info("No content extracted, ignoring message")
            return

        # Добавляем содержимое файла к вопросу, если оно есть
        if file_content:
            question = f"{question}\n\n{file_content}" if question else file_content

        logger.info(f"Extracted question: {question}")

        await self.reply_func(
            update=update, message=message, context=context, question=question
        )
