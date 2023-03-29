"""Working with questions in chat messages."""

import datetime as dt
import logging
from telegram import Message
from telegram.ext import (
    CallbackContext,
)

from bot import commands
from bot import config
from bot.ai.chatgpt import Model
from bot.models import UserData

logger = logging.getLogger(__name__)

# We are using the latest and greatest OpenAI model.
# There is also a previous generation (GPT-3)
# available via davinci.Model class, but who needs it?
model = Model(config.openai_model)


def extract_private(message: Message, context: CallbackContext) -> str:
    """Extracts a question from a message in a private chat."""
    # allow any messages in a private chat
    question = message.text
    if message.reply_to_message:
        # it's a follow-up question
        question = f"+ {question}"
    return question


def extract_group(message: Message, context: CallbackContext) -> tuple[str, Message]:
    """Extracts a question from a message in a group chat."""
    if (
        message.reply_to_message
        and message.reply_to_message.from_user.username == context.bot.username
    ):
        # treat a reply to the bot as a follow-up question
        question = f"+ {message.text}"
        return question, message

    elif not message.text.startswith(context.bot.name):
        # the message is not a reply to the bot,
        # so ignore it unless it's mentioning the bot
        return "", message

    # the message is mentioning the bot,
    # so remove the mention to get the question
    question = message.text.removeprefix(context.bot.name).strip()

    if message.reply_to_message:
        # the real question is in the original message
        question = (
            f"{question}: {message.reply_to_message.text}"
            if question
            else message.reply_to_message.text
        )
        return question, message.reply_to_message

    return question, message


def prepare(question: str, context: CallbackContext) -> tuple[str, list]:
    """Returns the question along with the previous messages (for follow-up questions)."""
    user = UserData(context.user_data)
    history = []
    if question[0] == "+":
        # this is a follow-up question,
        # so the bot should retain the previous history
        question = question.strip("+ ")
        history = user.messages.as_list()

    elif question[0] == "!":
        # this is a command, so the bot should
        # process the question before asking it
        command, question = commands.extract(question)
        question = commands.apply(command, question)
        # questions with commands clear the previous history
        user.messages.clear()

    else:
        # user is asking a question 'from scratch',
        # so the bot should forget the previous history
        user.messages.clear()
    return question, history


async def ask(message: Message, context: CallbackContext, question: str) -> str:
    """Answers a question using the OpenAI model."""
    question = question or message.text
    prep_question, history = prepare(question, context)
    logger.debug(f"Prepared question: {prep_question}")
    start = dt.datetime.now()
    answer = await model.ask(prep_question, history)
    elapsed = int((dt.datetime.now() - start).total_seconds() * 1000)
    logger.info(
        f"question from user={message.from_user.username}, "
        f"n_chars={len(prep_question)}, len_history={len(history)}, took={elapsed}ms"
    )
    return answer
