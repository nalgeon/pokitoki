import unittest
from unittest import mock

from bot import db
from bot.config import Config, ConfigEditor, SchemaMigrator


class ConfigTest(unittest.TestCase):
    def test_init(self):
        src = {
            "telegram": {"token": "tg-1234", "usernames": ["nalgeon"]},
            "ai": {"api_key": "oa-1234", "model": "gpt-4"},
            "conversation": {"depth": 5},
        }
        config = Config("config.test.yml", src)

        self.assertEqual(config.telegram.token, "tg-1234")
        self.assertEqual(config.telegram.usernames, ["nalgeon"])
        self.assertEqual(config.telegram.admins, [])
        self.assertEqual(config.telegram.chat_ids, [])

        self.assertEqual(config.ai.api_key, "oa-1234")
        self.assertEqual(config.ai.model, "gpt-4")
        self.assertEqual(config.ai.window, 128000)
        self.assertTrue(config.ai.prompt, "You are an AI assistant.")

        self.assertEqual(config.conversation.depth, 5)
        self.assertEqual(config.db_path, "./data/pokitoki.db")
        self.assertEqual(config.shortcuts, {})

    def test_defaults(self):
        src = {
            "telegram": {"token": "tg-1234"},
            "ai": {"api_key": "oa-1234"},
            "conversation": {},
        }
        config = Config("config.test.yml", src)
        self.assertEqual(config.ai.url, "https://api.openai.com/v1")
        self.assertEqual(config.ai.model, "gpt-6-luna")

    def test_as_dict(self):
        src = {
            "telegram": {"token": "tg-1234", "usernames": ["nalgeon"]},
            "ai": {"api_key": "oa-1234", "model": "gpt-4"},
            "conversation": {"depth": 5},
        }
        config = Config("config.test.yml", src)
        data = config.as_dict()
        self.assertEqual(data["telegram"]["token"], src["telegram"]["token"])
        self.assertEqual(data["telegram"]["usernames"], src["telegram"]["usernames"])
        self.assertEqual(data["telegram"]["admins"], [])
        self.assertEqual(data["telegram"]["chat_ids"], [])
        self.assertEqual(data["ai"]["api_key"], src["ai"]["api_key"])
        self.assertEqual(data["ai"]["model"], src["ai"]["model"])
        self.assertEqual(data["conversation"]["depth"], src["conversation"]["depth"])


class GetValueTest(unittest.TestCase):
    def setUp(self) -> None:
        src = {
            "telegram": {"token": "tg-1234", "usernames": ["nalgeon"]},
            "ai": {"api_key": "oa-1234", "model": "gpt-4"},
            "conversation": {"depth": 5},
            "shortcuts": {"translate": "Translate into English"},
        }
        self.editor = ConfigEditor(Config("config.test.yml", src))

    def test_object(self):
        value = self.editor.get_value("telegram")
        self.assertEqual(
            value, {"token": "tg-1234", "usernames": ["nalgeon"], "admins": [], "chat_ids": []}
        )

    def test_object_attr(self):
        value = self.editor.get_value("telegram.token")
        self.assertEqual(value, "tg-1234")

    def test_list(self):
        value = self.editor.get_value("telegram.usernames")
        self.assertEqual(value, ["nalgeon"])

    def test_dict(self):
        value = self.editor.get_value("shortcuts")
        self.assertEqual(value, {"translate": "Translate into English"})

    def test_dict_value(self):
        value = self.editor.get_value("shortcuts.translate")
        self.assertEqual(value, "Translate into English")

    def test_str(self):
        value = self.editor.get_value("db_path")
        self.assertEqual(value, "./data/pokitoki.db")

    def test_int(self):
        value = self.editor.get_value("conversation.depth")
        self.assertEqual(value, 5)

    def test_not_allowed(self):
        with self.assertRaises(ValueError):
            self.editor.get_value("__class__")

    def test_does_not_exist(self):
        with self.assertRaises(ValueError):
            self.editor.get_value("quack")

    def test_object_attr_not_exist(self):
        with self.assertRaises(ValueError):
            self.editor.get_value("telegram.godmode")

    def test_dict_value_does_not_exist(self):
        value = self.editor.get_value("shortcuts.bugfix")
        self.assertIsNone(value)


class SetValueTest(unittest.TestCase):
    def setUp(self) -> None:
        src = {
            "telegram": {
                "token": "tg-1234",
                "usernames": ["alice", "bob"],
                "admins": ["botfather"],
            },
            "ai": {"api_key": "oa-1234", "model": "gpt-4"},
            "conversation": {"depth": 5},
            "shortcuts": {"translate": "Translate into English"},
        }
        self.editor = ConfigEditor(Config("config.test.yml", src))
        self.editor.save = lambda: None

    def test_object(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("telegram", '{"token": "tg-1234", "usernames": ["alice"]}')

    def test_object_attr(self):
        self.editor.set_value("telegram.token", "tg-5678")
        value = self.editor.get_value("telegram.token")
        self.assertEqual(value, "tg-5678")

    def test_list(self):
        self.editor.set_value("telegram.usernames", '["cindy", "dave"]')
        value = self.editor.get_value("telegram.usernames")
        self.assertEqual(value, ["cindy", "dave"])

    def test_list_add(self):
        self.editor.set_value("telegram.usernames", "+cindy")
        value = self.editor.get_value("telegram.usernames")
        self.assertEqual(value, ["alice", "bob", "cindy"])

    def test_list_remove(self):
        self.editor.set_value("telegram.usernames", "-bob")
        value = self.editor.get_value("telegram.usernames")
        self.assertEqual(value, ["alice"])

    def test_dict(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("shortcuts.bugfix", '{"bugfix": "Fix bugs in the code"}')

    def test_dict_value(self):
        self.editor.set_value("shortcuts.translate", "Translate into Spanish")
        value = self.editor.get_value("shortcuts.translate")
        self.assertEqual(value, "Translate into Spanish")

    def test_int(self):
        self.editor.set_value("conversation.depth", "7")
        value = self.editor.get_value("conversation.depth")
        self.assertEqual(value, 7)

    def test_invalid_type_1(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("conversation.depth", "five")

    def test_invalid_type_2(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("telegram.usernames", "alice")

    def test_invalid_type_3(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("conversation", "no")

    def test_not_allowed(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("__class__", "{}")

    def test_readonly(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("version", "10")

    def test_does_not_exist(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("quack", "yes")

    def test_object_attr_not_exist(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("telegram.godmode", "on")

    def test_dict_value_does_not_exist(self):
        self.editor.set_value("shortcuts.bugfix", "Fix bugs in the code")
        value = self.editor.get_value("shortcuts.bugfix")
        self.assertEqual(value, "Fix bugs in the code")

    def test_invalid_value(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("ai.model", '"gpt-5')

    def test_has_changed(self):
        has_changed, _, new_val = self.editor.set_value("ai.model", "gpt-5")
        self.assertTrue(has_changed)
        self.assertEqual(new_val, "gpt-5")

    def test_has_not_changed(self):
        has_changed, _, new_val = self.editor.set_value("ai.model", "gpt-4")
        self.assertFalse(has_changed)
        self.assertEqual(new_val, "gpt-4")

    def test_is_immediate_1(self):
        _, is_immediate, _ = self.editor.set_value("ai.model", "gpt-5")
        self.assertTrue(is_immediate)

    def test_is_immediate_2(self):
        _, is_immediate, _ = self.editor.set_value("telegram.usernames", '["cindy", "dave"]')
        self.assertTrue(is_immediate)

    def test_is_delayed(self):
        _, is_immediate, _ = self.editor.set_value("telegram.token", "tg-5678")
        self.assertFalse(is_immediate)


class MigrateTest(unittest.TestCase):
    def setUp(self) -> None:
        # don't touch the real files
        patcher = mock.patch.object(db, "import_pickle")
        self.import_pickle = patcher.start()
        self.addCleanup(patcher.stop)

    def test_migrate_v1(self):
        old = {
            "telegram_token": "tg-1234",
            "telegram_usernames": ["alice"],
            "telegram_chat_ids": [-100500],
            "openai_api_key": "oa-1234",
            "openai_model": "gpt-3.5-turbo",
            "persistence_path": "./data/persistence.pkl",
        }
        migrated, has_changed = SchemaMigrator.migrate(old)
        self.assertTrue(has_changed)
        self.assertEqual(
            migrated,
            {
                "schema_version": 7,
                "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
                "ai": {"api_key": "oa-1234", "model": "gpt-3.5-turbo"},
                "conversation": {"depth": 3},
                "db_path": "./data/pokitoki.db",
                "shortcuts": None,
            },
        )

    def test_migrate_v2(self):
        old = {
            "schema_version": 2,
            "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
            "openai": {"api_key": "oa-1234", "model": "gpt-3.5-turbo"},
            "max_history_depth": 5,
            "imagine": False,
            "persistence_path": "./data/persistence.pkl",
            "shortcuts": {"bugfix": "Fix bugs"},
        }
        migrated, has_changed = SchemaMigrator.migrate(old)
        self.assertTrue(has_changed)
        self.assertEqual(
            migrated,
            {
                "schema_version": 7,
                "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
                "ai": {"api_key": "oa-1234", "model": "gpt-3.5-turbo"},
                "conversation": {"depth": 5},
                "db_path": "./data/pokitoki.db",
                "shortcuts": {"bugfix": "Fix bugs"},
            },
        )

    def test_migrate_v3(self):
        old = {
            "schema_version": 3,
            "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
            "openai": {"api_key": "oa-1234", "model": "gpt-3.5-turbo"},
            "conversation": {"depth": 5},
            "imagine": True,
            "persistence_path": "./data/persistence.pkl",
            "shortcuts": {"bugfix": "Fix bugs"},
        }
        migrated, has_changed = SchemaMigrator.migrate(old)
        self.assertTrue(has_changed)
        self.assertEqual(
            migrated,
            {
                "schema_version": 7,
                "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
                "ai": {"api_key": "oa-1234", "model": "gpt-3.5-turbo"},
                "conversation": {"depth": 5},
                "db_path": "./data/pokitoki.db",
                "shortcuts": {"bugfix": "Fix bugs"},
            },
        )

    def test_migrate_v4(self):
        old = {
            "schema_version": 4,
            "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
            "openai": {
                "api_key": "oa-1234",
                "model": "gpt-3.5-turbo",
                "params": {"temperature": 0.7, "max_tokens": 4096},
            },
            "conversation": {"depth": 5},
            "imagine": {"enabled": "users_only"},
            "persistence_path": "./data/persistence.pkl",
            "shortcuts": {"bugfix": "Fix bugs"},
        }
        migrated, has_changed = SchemaMigrator.migrate(old)
        self.assertTrue(has_changed)
        self.assertEqual(
            migrated,
            {
                "schema_version": 7,
                "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
                "ai": {"api_key": "oa-1234", "model": "gpt-3.5-turbo"},
                "conversation": {"depth": 5},
                "db_path": "./data/pokitoki.db",
                "shortcuts": {"bugfix": "Fix bugs"},
            },
        )

    def test_migrate_v5(self):
        old = {
            "schema_version": 5,
            "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
            "ai": {"api_key": "oa-1234", "model": "gpt-5", "image_model": "dall-e-3"},
            "conversation": {"depth": 5},
            "imagine": {"enabled": "users_only"},
            "persistence_path": "./data/persistence.pkl",
            "shortcuts": {"bugfix": "Fix bugs"},
        }
        migrated, has_changed = SchemaMigrator.migrate(old)
        self.assertTrue(has_changed)
        self.assertEqual(
            migrated,
            {
                "schema_version": 7,
                "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
                "ai": {"api_key": "oa-1234", "model": "gpt-5"},
                "conversation": {"depth": 5},
                "db_path": "./data/pokitoki.db",
                "shortcuts": {"bugfix": "Fix bugs"},
            },
        )

    def test_migrate_v6(self):
        old = {
            "schema_version": 6,
            "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
            "ai": {"api_key": "oa-1234", "model": "gpt-5"},
            "conversation": {"depth": 5},
            "persistence_path": "/var/bot/state.pkl",
            "shortcuts": {"bugfix": "Fix bugs"},
        }
        migrated, has_changed = SchemaMigrator.migrate(old)
        self.assertTrue(has_changed)
        self.assertEqual(
            migrated,
            {
                "schema_version": 7,
                "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
                "ai": {"api_key": "oa-1234", "model": "gpt-5"},
                "conversation": {"depth": 5},
                "db_path": "/var/bot/pokitoki.db",
                "shortcuts": {"bugfix": "Fix bugs"},
            },
        )
        self.import_pickle.assert_called_once_with("/var/bot/state.pkl", "/var/bot/pokitoki.db")

    def test_not_changed(self):
        old = {
            "schema_version": 7,
            "telegram": {"token": "tg-1234", "usernames": ["alice"], "chat_ids": [-100500]},
            "ai": {"api_key": "oa-1234", "model": "gpt-3.5-turbo"},
            "conversation": {"depth": 5},
            "db_path": "./data/pokitoki.db",
            "shortcuts": {"bugfix": "Fix bugs"},
        }
        migrated, has_changed = SchemaMigrator.migrate(old)
        self.assertFalse(has_changed)
        self.import_pickle.assert_not_called()
        self.assertEqual(migrated, old)
