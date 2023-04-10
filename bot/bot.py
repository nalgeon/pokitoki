"""Telegram chat bot built using the language model from OpenAI."""

import logging
import sys

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
)
from bot import commands
from bot.config import config
from bot.fetcher import Fetcher
from bot.filters import Filters


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("bot.ai.chatgpt").setLevel(logging.INFO)
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

    # the message command is reused by others
    message_cmd = commands.Message(fetcher)

    # command handlers
    application.add_handler(CommandHandler("start", commands.Start()))
    application.add_handler(CommandHandler("help", commands.Help(), filters=filters.users))
    application.add_handler(CommandHandler("version", commands.Version(), filters=filters.users))
    application.add_handler(
        CommandHandler("retry", commands.Retry(message_cmd), filters=filters.users_or_chats)
    )
    application.add_handler(
        CommandHandler("imagine", commands.Imagine(message_cmd), filters=filters.users_or_chats)
    )
    application.add_handler(
        CommandHandler("config", commands.Config(filters), filters=filters.admins_private)
    )

    # non-command handler: the default action is to reply to a message
    application.add_handler(MessageHandler(filters.messages, message_cmd))

    # generic error handler
    application.add_error_handler(commands.Error())


async def post_init(application: Application) -> None:
    """Defines bot settings."""
    bot = application.bot
    logging.info(f"config: file={config.filename}, version={config.version}")
    logging.info(f"allowed users: {config.telegram.usernames}")
    logging.info(f"allowed chats: {config.telegram.chat_ids}")
    logging.info(f"admins: {config.telegram.admins}")
    logging.info(f"model name: {config.openai.model}")
    logging.info(f"bot: username={bot.username}, id={bot.id}")
    await bot.set_my_commands(commands.BOT_COMMANDS)


async def post_shutdown(application: Application) -> None:
    """Frees acquired resources."""
    await fetcher.close()


if __name__ == "__main__":
    main()
