"""Telegram chat bot built using the language model from OpenAI."""

import logging
import sys
import textwrap
import time

from telegram import Chat, Message, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
)
from bot import askers
from bot import commands
from bot import questions
from bot import models
from bot.config import config
from bot.fetcher import Fetcher
from bot.filters import Filters
from bot.models import ChatData, UserData


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("bot").setLevel(logging.INFO)
logging.getLogger("bot.ai.chat").setLevel(logging.INFO)
logging.getLogger("bot.commands").setLevel(logging.INFO)
logging.getLogger("bot.questions").setLevel(logging.INFO)
logging.getLogger("__main__").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# retrieves remote content
fetcher = Fetcher()

# telegram message filters
filters = Filters()


def main():
    persistence = PicklePersistence(filepath=config.persistence_path)
    application = (
        ApplicationBuilder()
        .token(config.telegram.token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .persistence(persistence)
        .concurrent_updates(True)
        .get_updates_http_version("1.1")
        .http_version("1.1")
        .build()
    )
    add_handlers(application)
    application.run_polling()


def add_handlers(application: Application):
    """Adds command handlers."""

    # info commands
    application.add_handler(CommandHandler("start", commands.Start()))
    application.add_handler(CommandHandler("help", commands.Help(), filters=filters.users))
    application.add_handler(CommandHandler("version", commands.Version(), filters=filters.users))

    # admin commands
    application.add_handler(
        CommandHandler("config", commands.Config(filters), filters=filters.admins_private)
    )

    # message-related commands
    application.add_handler(
        CommandHandler("imagine", commands.Imagine(reply_to), filters=filters.users_or_chats)
    )
    application.add_handler(CommandHandler("model", commands.Model(), filters=filters.users))
    application.add_handler(CommandHandler("prompt", commands.Prompt(), filters=filters.users))
    application.add_handler(
        CommandHandler("retry", commands.Retry(reply_to), filters=filters.users_or_chats)
    )

    # non-command handler: the default action is to reply to a message
    application.add_handler(MessageHandler(filters.messages, commands.Message(reply_to)))

    # generic error handler
    application.add_error_handler(commands.Error())


async def post_init(application: Application) -> None:
    """Defines bot settings."""
    bot = application.bot
    logging.info(f"config: file={config.filename}, version={config.version}")
    logging.info(f"allowed users: {config.telegram.usernames}")
    logging.info(f"allowed chats: {config.telegram.chat_ids}")
    logging.info(f"admins: {config.telegram.admins}")
    logging.info(f"api url: {config.openai.url}")
    logging.info(f"model name: {config.openai.model}")
    logging.info(f"bot: username={bot.username}, id={bot.id}")
    await bot.set_my_commands(commands.BOT_COMMANDS)


async def post_shutdown(application: Application) -> None:
    """Frees acquired resources."""
    await fetcher.close()


def with_message_limit(func):
    """Refuses to reply if the user has exceeded the message limit."""

    async def wrapper(
        update: Update, message: Message, context: CallbackContext, question: str
    ) -> None:
        username = update.effective_user.username
        user = UserData(context.user_data)

        # check if the message counter exceeds the message limit
        if (
            not filters.is_known_user(username)
            and user.message_counter.value >= config.conversation.message_limit.count > 0
            and not user.message_counter.is_expired()
        ):
            # this is a group user and they have exceeded the message limit
            wait_for = models.format_timedelta(user.message_counter.expires_after())
            await message.reply_text(f"Please wait {wait_for} before asking a new question.")
            return

        # this is a known user or they have not exceeded the message limit,
        # so proceed to the actual message handler
        await func(update=update, message=message, context=context, question=question)

        # increment the message counter
        message_count = user.message_counter.increment()
        logger.debug(f"user={username}, n_messages={message_count}")

    return wrapper


@with_message_limit
async def reply_to(
    update: Update, message: Message, context: CallbackContext, question: str
) -> None:
    """Replies to a specific question."""
    await message.chat.send_action(action="typing", message_thread_id=message.message_thread_id)

    try:
        chat = ChatData(context.chat_data)
        model = chat.model or config.openai.model
        asker = askers.create(model=model, question=question)
        if message.chat.type == Chat.PRIVATE and message.forward_date:
            # this is a forwarded message, don't answer yet
            answer = "This is a forwarded message. What should I do with it?"
        else:
            answer = await _ask_question(message, context, question, asker)

        user = UserData(context.user_data)
        user.messages.add(question, answer)
        logger.debug(user.messages)
        await asker.reply(message, context, answer)

    except Exception as exc:
        class_name = f"{exc.__class__.__module__}.{exc.__class__.__qualname__}"
        error_text = f"{class_name}: {exc}"
        logger.error("Failed to answer: %s", error_text)
        text = textwrap.shorten(f"⚠️ {error_text}", width=255, placeholder="...")
        await message.reply_text(text)


async def _ask_question(
    message: Message, context: CallbackContext, question: str, asker: askers.Asker
) -> str:
    """Answers a question using the OpenAI model."""
    user_id = message.from_user.username or message.from_user.id
    logger.info(f"-> question id={message.id}, user={user_id}, n_chars={len(question)}")

    question, is_follow_up = questions.prepare(question)
    question = await fetcher.substitute_urls(question)
    logger.debug(f"Prepared question: {question}")

    user = UserData(context.user_data)
    if message.chat.type == Chat.PRIVATE:
        # in private chats the bot remembers previous messages
        if is_follow_up:
            # this is a follow-up question,
            # so the bot should retain the previous history
            history = user.messages.as_list()
        else:
            # user is asking a question 'from scratch',
            # so the bot should forget the previous history
            user.messages.clear()
            history = []
    else:
        # in group chats the bot only answers direct questions
        # or follow-up questions to the bot messages
        prev_message = questions.extract_prev(message, context)
        history = [("", prev_message)] if prev_message else []

    chat = ChatData(context.chat_data)
    start = time.perf_counter_ns()
    answer = await asker.ask(prompt=chat.prompt, question=question, history=history)
    elapsed = int((time.perf_counter_ns() - start) / 1e6)

    logger.info(
        f"<- answer id={message.id}, user={user_id}, "
        f"n_chars={len(answer)}, len_history={len(history)}, took={elapsed}ms"
    )
    return answer


if __name__ == "__main__":
    main()
