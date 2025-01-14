"""Bot message filters."""

import logging
from typing import Union
from dataclasses import dataclass
from telegram.ext import filters
from bot.config import config

logger = logging.getLogger(__name__)


@dataclass
class Filters:
    """Filters for the incoming Telegram messages."""

    users: Union[filters.MessageFilter, filters.User]
    admins: filters.User
    chats: Union[filters.MessageFilter, filters.Chat]

    users_or_chats: filters.BaseFilter
    admins_private: filters.BaseFilter
    text_filter: filters.BaseFilter

    def __init__(self) -> None:
        """Defines users and chats that are allowed to use the bot."""
        if config.telegram.usernames:
            self.users = filters.User(username=config.telegram.usernames)
            self.chats = filters.Chat(chat_id=config.telegram.chat_ids)
        else:
            self.users = filters.ALL
            self.chats = filters.ALL

        if config.telegram.admins:
            self.admins = filters.User(username=config.telegram.admins)
        else:
            self.admins = filters.User(username=[])

        self.users_or_chats = self.users | self.chats
        self.admins_private = self.admins & filters.ChatType.PRIVATE
        self.text_filter = filters.TEXT

        logger.info(
            f"Filters initialized: text={self.text_filter}, users_or_chats={self.users_or_chats}"
        )

    def reload(self) -> None:
        """Reloads users and chats from config."""
        if self.users == filters.ALL and config.telegram.usernames:
            # cannot update the filter from ALL to specific usernames without a restart
            raise Exception("Restart the bot for changes to take effect")
        self.users.usernames = config.telegram.usernames
        self.chats.chat_ids = config.telegram.chat_ids
        self.admins.usernames = config.telegram.admins

    def is_known_user(self, username: str) -> bool:
        """Checks if the username is included in the `users` filter."""
        if self.users == filters.ALL:
            return False
        return username in self.users.usernames
