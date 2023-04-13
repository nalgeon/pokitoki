"""/version command."""

from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from bot.config import config
from . import constants


class VersionCommand:
    """Answers the `version` command."""

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        chat = update.message.chat
        # chat information
        text = (
            "<pre>"
            "Chat information:\n"
            f"- id: {chat.id}\n"
            f"- title: {chat.title}\n"
            f"- type: {chat.type}"
            "</pre>"
        )
        bot = await context.bot.get_me()
        usernames = (
            "all" if not config.telegram.usernames else f"{len(config.telegram.usernames)} users"
        )
        admins = "none" if not config.telegram.admins else f"{len(config.telegram.admins)} users"

        # bot information
        text += (
            "\n\n<pre>"
            "Bot information:\n"
            f"- id: {bot.id}\n"
            f"- name: {bot.name}\n"
            f"- version: {config.version}\n"
            f"- usernames: {usernames}\n"
            f"- admins: {admins}\n"
            f"- chat IDs: {config.telegram.chat_ids}\n"
            f"- access to messages: {bot.can_read_all_group_messages}"
            "</pre>"
        )
        if not bot.can_read_all_group_messages:
            text += f"\n\n{constants.PRIVACY_MESSAGE}"

        # AI information
        text += (
            "\n\n<pre>"
            "AI information:\n"
            f"- model: {config.openai.model}\n"
            f"- history depth: {config.conversation.depth}\n"
            f"- imagine: {config.imagine.enabled}\n"
            f"- shortcuts: {', '.join(config.shortcuts.keys())}"
            "</pre>"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
