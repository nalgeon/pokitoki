"""/model command."""

from telegram import Chat, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from bot.config import config
from bot.models import ChatData

HELP_MESSAGE = """Syntax:
<code>/model [AI model name]</code>

For example:
<code>/model gpt-6-astra</code>

To use the default model:
<code>/model reset</code>"""

RESET = "reset"


class ModelCommand:
    """Sets an AI model."""

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        message = update.message or update.edited_message

        if (
            message.chat.type != Chat.PRIVATE
            and update.effective_user.username not in config.telegram.admins
        ):
            # Only admins are allowed to change the model in group chats.
            return

        chat = ChatData(message.chat_id)
        _, _, model = message.text.partition(" ")
        if not model:
            # /model without arguments
            if chat.model:
                # the model is already set, show it
                await message.reply_text(
                    f"Using model:\n<code>{chat.model}</code>",
                    parse_mode=ParseMode.HTML,
                )
                return
            else:
                # the model is not set, show help message
                await message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)
                return

        if model == RESET:
            # /model with "reset" argument
            chat.model = ""
            await message.reply_text(
                f"✓ Using default model:\n<code>{config.ai.model}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        # /model with a name
        chat.model = model
        await message.reply_text(
            f"✓ Set model:\n<code>{model}</code>",
            parse_mode=ParseMode.HTML,
        )
