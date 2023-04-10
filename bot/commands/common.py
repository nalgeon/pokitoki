"""Common bot commands data."""

from bot.config import config

HELP_MESSAGE = """Send me a question, and I will do my best to answer it. Please be specific, as I'm not very clever.

I don't remember chat context by default. To ask follow-up questions, reply to my messages or start your questions with a '+' sign.

Built-in commands:
{commands}{admin_commands}

AI shortcuts:
{shortcuts}

[More features →](https://github.com/nalgeon/pokitoki#readme)
"""

PRIVACY_MESSAGE = (
    "⚠️ The bot does not have access to group messages, "
    "so it cannot reply in groups. Use @botfather "
    "to give the bot access (Bot Settings > Group Privacy > Turn off)"
)

BOT_COMMANDS = [
    ("retry", "retry the last question"),
    ("imagine", "generate described image"),
    ("version", "show debug information"),
    ("help", "show help"),
]

ADMIN_COMMANDS = {
    "config": "view or edit the config",
}


def generate_help_message(username: str) -> str:
    """Generates a help message, including a list of allowed commands."""

    # user commands
    commands = "\n".join(f"/{cmd} - {descr}" for cmd, descr in BOT_COMMANDS)

    # admin commands
    admin_commands = ""
    if username in config.telegram.admins:
        admin_commands += "\n\nAdmin-only commads:\n"
        admin_commands += f'/config - {ADMIN_COMMANDS["config"]}\n'
    admin_commands = admin_commands.rstrip()

    # shortcuts
    if config.shortcuts:
        shortcuts = "\n".join(f"`!{shortcut}`" for shortcut in config.shortcuts)
    else:
        shortcuts = "none"

    return HELP_MESSAGE.format(
        commands=commands, admin_commands=admin_commands, shortcuts=shortcuts
    )
