"""Extracts questions from chat messages."""

import logging
from typing import Optional

from telegram import Message, MessageEntity
from telegram.ext import CallbackContext

from bot import shortcuts

logger = logging.getLogger(__name__)


async def extract_private(message: Message, context: CallbackContext) -> Optional[str]:
    """Extracts a question from a private message."""
    # allow any messages in a private chat
    question = await _extract_text(message, context)
    if message.reply_to_message:
        # it's a follow-up question
        question = f"+ {question}"
    return question


async def extract_group(
    message: Message, context: CallbackContext
) -> tuple[str, Message]:
    """Extracts a question from a message in a group chat."""
    text = await _extract_text(message, context)

    # Проверяем, является ли сообщение ответом боту
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user.username == context.bot.username
    )

    # Проверяем упоминание бота
    entities = message.entities or message.caption_entities
    mention = (
        entities[0] if entities and entities[0].type == MessageEntity.MENTION else None
    )

    # Если это не ответ боту и нет упоминания - игнорируем
    if not is_reply_to_bot and not mention:
        return "", message

    # Если это ответ боту
    if is_reply_to_bot:
        question = f"+ {text}" if text else ""
        return question, message

    # Если есть упоминание, проверяем что оно относится к боту
    mention_text = text[mention.offset : mention.offset + mention.length]
    if mention_text.lower() != context.bot.name.lower():
        return "", message

    # Убираем упоминание из текста
    question = text[: mention.offset] + text[mention.offset + mention.length :]
    question = question.strip()

    # Если это ответ на сообщение (но не на создание топика)
    if message.reply_to_message and not message.reply_to_message.forum_topic_created:
        reply_text = await _extract_text(message.reply_to_message, context)
        question = f"{question}: {reply_text}" if question else reply_text
        return question, message.reply_to_message

    return question, message


def extract_prev(message: Message, context: CallbackContext) -> str:
    """Extracts the previous message by the bot, if any."""
    if (
        message.reply_to_message
        and message.reply_to_message.from_user.username == context.bot.username
    ):
        # treat a reply to the bot as a follow-up question
        return message.reply_to_message.text

    # otherwise, ignore previous messages
    return ""


def prepare(question: str) -> tuple[str, bool]:
    """
    Returns the question without the special commands
    and indicates whether it is a follow-up.
    """

    if question[0] == "+":
        question = question.strip("+ ")
        is_follow_up = True
    else:
        is_follow_up = False

    if question[0] == "!":
        # this is a shortcut, so the bot should
        # process the question before asking it
        shortcut, question = shortcuts.extract(question)
        question = shortcuts.apply(shortcut, question)

    elif question[0] == "/":
        # this is a command, so the bot should
        # strip it from the question before asking
        _, _, question = question.partition(" ")
        question = question.strip()

    return question, is_follow_up


async def _extract_text(message: Message, context: CallbackContext) -> str:
    """Extracts text from a text message or a document message."""
    if message.text:
        return message.text
    if message.caption:
        return message.caption
    return ""
