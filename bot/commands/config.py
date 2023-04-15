"""/config command."""

from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from bot.config import config, ConfigEditor
from bot.filters import Filters

HELP_MESSAGE = """Syntax:
<code>/config property [value]</code>

E.g. to view the property value:
<code>/config openai.prompt</code>

E.g. to change the property value:
<code>/config openai.prompt You are an AI assistant</code>"""

editor = ConfigEditor(config)


class ConfigCommand:
    """Displays or changes config properties."""

    def __init__(self, filters: Filters) -> None:
        self.filters = filters

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        message = update.message or update.edited_message

        parts = message.text.split()
        if len(parts) == 1:
            # /config without arguments
            await message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)
            return

        property = parts[1]
        value = editor.get_value(property)
        value = value if value is not None else "(empty)"

        if len(parts) == 2:
            # view config property (`/config {property}`)
            await message.reply_text(f"`{value}`", parse_mode=ParseMode.MARKDOWN)
            return

        # change config property (`/config {property} {new_value}`)
        new_value = " ".join(parts[2:])
        has_changed, is_immediate, new_val = editor.set_value(property, new_value)

        if not has_changed:
            text = f"✗ The `{property}` property already equals to `{new_value}`"
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return

        editor.save()
        if self._should_reload_filters(property):
            self.filters.reload()

        text = f"✓ Changed the `{property}` property: `{value}` → `{new_val}`"
        if not is_immediate:
            text += "\n❗️Restart the bot for changes to take effect."
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    def _should_reload_filters(self, property: str) -> bool:
        return property in (
            "telegram.usernames",
            "telegram.chat_ids",
            "telegram.admins",
        )
