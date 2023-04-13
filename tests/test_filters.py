import unittest

from telegram.ext import filters as tg_filters
from bot.config import config
from bot.filters import Filters


class FiltersTest(unittest.TestCase):
    def test_init(self):
        config.telegram.usernames = ["alice", "bob"]
        config.telegram.chat_ids = [-100, -200]
        config.telegram.admins = ["admin"]
        filters = Filters()
        self.assertEqual(filters.users.usernames, set(["alice", "bob"]))
        self.assertEqual(filters.chats.chat_ids, set([-100, -200]))
        self.assertEqual(filters.admins.usernames, set(["admin"]))

    def test_reload(self):
        config.telegram.usernames = ["alice", "bob"]
        config.telegram.chat_ids = [-100, -200]
        config.telegram.admins = ["admin"]
        filters = Filters()

        config.telegram.usernames = ["alice", "bob", "cindy"]
        config.telegram.chat_ids = [-300]
        config.telegram.admins = ["zappa", "xanos"]
        filters.reload()
        self.assertEqual(filters.users.usernames, set(["alice", "bob", "cindy"]))
        self.assertEqual(filters.chats.chat_ids, set([-300]))
        self.assertEqual(filters.admins.usernames, set(["zappa", "xanos"]))

    def test_is_known_user(self):
        config.telegram.usernames = ["alice", "bob"]
        filters = Filters()
        self.assertTrue(filters.is_known_user("alice"))
        self.assertFalse(filters.is_known_user("cindy"))


class EmptyTest(unittest.TestCase):
    def test_init(self):
        config.telegram.usernames = []
        config.telegram.chat_ids = [-100, -200]
        config.telegram.admins = ["admin"]
        filters = Filters()
        self.assertEqual(filters.users, tg_filters.ALL)
        self.assertEqual(filters.chats, tg_filters.ALL)
        self.assertEqual(filters.admins.usernames, set(["admin"]))

    def test_reload(self):
        config.telegram.usernames = []
        filters = Filters()
        config.telegram.usernames = ["alice", "bob"]
        with self.assertRaises(Exception):
            filters.reload()

    def test_is_known_user(self):
        config.telegram.usernames = []
        filters = Filters()
        self.assertFalse(filters.is_known_user("alice"))
        self.assertFalse(filters.is_known_user("cindy"))
