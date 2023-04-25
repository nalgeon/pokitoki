"""Extracts questions from chat messages."""

from telegram import Message, MessageEntity
from telegram.ext import CallbackContext
from bot import shortcuts


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

    mention = (
        message.entities[0]
        if message.entities and message.entities[0].type == MessageEntity.MENTION
        else None
    )
    if not mention:
        # the message is not a reply to the bot,
        # so ignore it unless it's mentioning the bot
        return "", message

    mention_text = message.text[mention.offset : mention.offset + mention.length]
    if mention_text.lower() != context.bot.name.lower():
        # the message mentions someone else
        return "", message

    # the message is mentioning the bot,
    # so remove the mention to get the question
    question = message.text[: mention.offset] + message.text[mention.offset + mention.length :]
    question = question.strip()

    # messages in topics are technically replies to the 'topic created' message
    # so we should ignore such replies
    if message.reply_to_message and not message.reply_to_message.forum_topic_created:
        # the real question is in the original message
        question = (
            f"{question}: {message.reply_to_message.text}"
            if question
            else message.reply_to_message.text
        )
        return question, message.reply_to_message

    return question, message


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
