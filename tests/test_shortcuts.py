import unittest

from bot.config import config
from bot import shortcuts


class ExtractTest(unittest.TestCase):
    def test_extract(self):
        name, question = shortcuts.extract("!translate Ciao")
        self.assertEqual(name, "translate")
        self.assertEqual(question, "Ciao")

    def test_failed(self):
        config.shortcuts["translate"] = "Translate into English."
        with self.assertRaises(ValueError):
            shortcuts.extract("Ciao")


class ApplyTest(unittest.TestCase):
    def test_apply(self):
        config.shortcuts["translate"] = "Translate into English."
        question = shortcuts.apply("translate", "Ciao")
        self.assertEqual(question, "Translate into English.\n\nCiao")

    def test_unknown_shortcut(self):
        with self.assertRaises(ValueError):
            shortcuts.apply("sing", "Ciao")
