"""Bot command constants."""

HELP_MESSAGE = """Send me a question, and I will do my best to answer it.

{memory}

Built-in commands:
{commands}{admin_commands}

AI shortcuts:
{shortcuts}

[More features →](https://github.com/nalgeon/pokitoki#readme)
"""

MEMORY_MESSAGE = (
    "I remember the conversation while you keep talking: "
    "questions sent within {timeout} minutes after my answer continue it. "
    "To start over, use /new. "
    "To continue later, reply to my message or start your question with a '+' sign."
)

NO_MEMORY_MESSAGE = (
    "I don't remember chat context by default. "
    "To ask follow-up questions, reply to my messages or start your questions with a '+' sign."
)

PRIVACY_MESSAGE = (
    "⚠️ The bot does not have access to group messages, "
    "so it cannot reply in groups. Use @botfather "
    "to give the bot access (Bot Settings > Group Privacy > Turn off)"
)

BOT_COMMANDS = [
    ("new", "start a new conversation"),
    ("retry", "retry the last question"),
    ("version", "show debug information"),
    ("help", "show help"),
]

ADMIN_COMMANDS = {
    "config": "view or edit the config",
}
