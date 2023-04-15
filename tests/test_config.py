import unittest
from bot.config import Config, ConfigEditor


class ConfigTest(unittest.TestCase):
    def test_init(self):
        src = {
            "telegram": {"token": "tg-1234", "usernames": ["nalgeon"]},
            "openai": {"api_key": "oa-1234", "model": "gpt-4"},
            "conversation": {"depth": 5},
            "imagine": {"enabled": "none"},
        }
        config = Config("config.test.yml", src)

        self.assertEqual(config.telegram.token, "tg-1234")
        self.assertEqual(config.telegram.usernames, ["nalgeon"])
        self.assertEqual(config.telegram.admins, [])
        self.assertEqual(config.telegram.chat_ids, [])

        self.assertEqual(config.openai.api_key, "oa-1234")
        self.assertEqual(config.openai.model, "gpt-4")
        self.assertTrue(config.openai.prompt.startswith("Your primary goal"))
        self.assertEqual(config.openai.params["temperature"], 0.7)
        self.assertEqual(config.openai.params["presence_penalty"], 0)
        self.assertEqual(config.openai.params["frequency_penalty"], 0)
        self.assertEqual(config.openai.params["max_tokens"], 1000)

        self.assertEqual(config.conversation.depth, 5)
        self.assertEqual(config.imagine.enabled, "none")
        self.assertEqual(config.persistence_path, "./data/persistence.pkl")
        self.assertEqual(config.shortcuts, {})

    def test_as_dict(self):
        src = {
            "telegram": {"token": "tg-1234", "usernames": ["nalgeon"]},
            "openai": {"api_key": "oa-1234", "model": "gpt-4"},
            "conversation": {"depth": 5},
            "imagine": {"enabled": "none"},
        }
        config = Config("config.test.yml", src)
        data = config.as_dict()
        self.assertEqual(data["telegram"]["token"], src["telegram"]["token"])
        self.assertEqual(data["telegram"]["usernames"], src["telegram"]["usernames"])
        self.assertEqual(data["telegram"]["admins"], [])
        self.assertEqual(data["telegram"]["chat_ids"], [])
        self.assertEqual(data["openai"]["api_key"], src["openai"]["api_key"])
        self.assertEqual(data["openai"]["model"], src["openai"]["model"])
        self.assertEqual(data["conversation"]["depth"], src["conversation"]["depth"])
        self.assertEqual(data["imagine"]["enabled"], src["imagine"]["enabled"])


class GetValueTest(unittest.TestCase):
    def setUp(self) -> None:
        src = {
            "telegram": {"token": "tg-1234", "usernames": ["nalgeon"]},
            "openai": {"api_key": "oa-1234", "model": "gpt-4"},
            "conversation": {"depth": 5},
            "imagine": {"enabled": "none"},
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
        value = self.editor.get_value("persistence_path")
        self.assertEqual(value, "./data/persistence.pkl")

    def test_int(self):
        value = self.editor.get_value("conversation.depth")
        self.assertEqual(value, 5)

    def test_float(self):
        value = self.editor.get_value("openai.params.temperature")
        self.assertEqual(value, 0.7)

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
                "usernames": ["nalgeon"],
                "admins": ["botfather"],
            },
            "openai": {"api_key": "oa-1234", "model": "gpt-4"},
            "conversation": {"depth": 5},
            "imagine": {"enabled": "none"},
            "shortcuts": {"translate": "Translate into English"},
        }
        self.editor = ConfigEditor(Config("config.test.yml", src))

    def test_object(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("telegram", '{"token": "tg-1234", "usernames": ["nalgeon"]}')

    def test_object_attr(self):
        self.editor.set_value("telegram.token", "tg-5678")
        value = self.editor.get_value("telegram.token")
        self.assertEqual(value, "tg-5678")

    def test_list(self):
        self.editor.set_value("telegram.usernames", '["alice", "bob"]')
        value = self.editor.get_value("telegram.usernames")
        self.assertEqual(value, ["alice", "bob"])

    def test_dict(self):
        with self.assertRaises(ValueError):
            self.editor.set_value("shortcuts.bugfix", '{"bugfix": "Fix bugs in the code"}')

    def test_dict_value(self):
        self.editor.set_value("shortcuts.translate", "Translate into Spanish")
        value = self.editor.get_value("shortcuts.translate")
        self.assertEqual(value, "Translate into Spanish")

    def test_int(self):
        self.editor.set_value("openai.params.max_tokens", "500")
        value = self.editor.get_value("openai.params.max_tokens")
        self.assertEqual(value, 500)

    def test_float(self):
        self.editor.set_value("openai.params.temperature", "0.5")
        value = self.editor.get_value("openai.params.temperature")
        self.assertEqual(value, 0.5)

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
            self.editor.set_value("imagine.enabled", '"users_only')

    def test_has_changed(self):
        has_changed, _ = self.editor.set_value("imagine.enabled", "users_only")
        self.assertTrue(has_changed)

    def test_has_not_changed(self):
        has_changed, _ = self.editor.set_value("imagine.enabled", "none")
        self.assertFalse(has_changed)

    def test_is_immediate_1(self):
        _, is_immediate = self.editor.set_value("imagine.enabled", "users_only")
        self.assertTrue(is_immediate)

    def test_is_immediate_2(self):
        _, is_immediate = self.editor.set_value("telegram.usernames", '["alice", "bob"]')
        self.assertTrue(is_immediate)

    def test_is_delayed_1(self):
        _, is_immediate = self.editor.set_value("conversation.depth", "10")
        self.assertFalse(is_immediate)

    def test_is_delayed_2(self):
        _, is_immediate = self.editor.set_value("telegram.token", "tg-5678")
        self.assertFalse(is_immediate)
