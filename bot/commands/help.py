"""/help command."""

from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from bot.config import config
from . import constants


class HelpCommand:
    """Answers the `help` command."""

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        text = generate_message(update.effective_user.username)
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )


def generate_message(username: str) -> str:
    """Generates a help message, including a list of allowed commands."""

    # user commands
    commands = "\n".join(f"/{cmd} - {descr}" for cmd, descr in constants.BOT_COMMANDS)

    # admin commands
    admin_commands = ""
    if username in config.telegram.admins:
        admin_commands += "\n\nAdmin-only commads:\n"
        admin_commands += f'/config - {constants.ADMIN_COMMANDS["config"]}\n'
    admin_commands = admin_commands.rstrip()

    # shortcuts
    if config.shortcuts:
        shortcuts = "\n".join(f"`!{shortcut}`" for shortcut in config.shortcuts)
    else:
        shortcuts = "none"

    return constants.HELP_MESSAGE.format(
        commands=commands, admin_commands=admin_commands, shortcuts=shortcuts
    )
