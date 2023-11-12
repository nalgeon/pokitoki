"""/prompt command."""

from telegram import Chat, Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from bot.config import config
from bot.models import ChatData

HELP_MESSAGE = """Syntax:
<code>/prompt [custom prompt]</code>

For example:
<code>/prompt You are an evil genius. Reply with an evil laugh.</code>

To use the default prompt:
<code>/prompt reset</code>"""

RESET = "reset"


class PromptCommand:
    """Sets a custom chat prompt."""

    async def __call__(self, update: Update, context: CallbackContext) -> None:
        message = update.message or update.edited_message

        if (
            message.chat.type != Chat.PRIVATE
            and update.effective_user.username not in config.telegram.admins
        ):
            # Only admins are allowed to change the prompt in group chats.
            return

        chat = ChatData(context.chat_data)
        _, _, prompt = message.text.partition(" ")
        if not prompt:
            # /prompt without arguments
            if chat.prompt:
                # custom prompt is already set, show it
                await message.reply_text(
                    f"Using custom prompt:\n<code>{chat.prompt}</code>",
                    parse_mode=ParseMode.HTML,
                )
                return
            else:
                # custom prompt is not set, show help message
                await message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)
                return

        if prompt == RESET:
            # /prompt with "reset" argument
            chat.prompt = ""
            await message.reply_text(
                f"✓ Using default prompt:\n<code>{config.openai.prompt}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        # /prompt with a custom prompt
        chat.prompt = prompt
        await message.reply_text(
            f"✓ Set custom prompt:\n<code>{prompt}</code>",
            parse_mode=ParseMode.HTML,
        )
