"""
Asker is an abstraction that sends questions to the AI
and responds to the user with answers provided by the AI.
"""

import io
import re
import textwrap

from telegram import Message
from telegram.constants import MessageLimit, ParseMode
from telegram.ext import CallbackContext

from bot import ai
from bot import config
from bot import markdown


class Asker:
    """Asks AI questions and responds with answers."""

    async def ask(self, question: str, history: list[tuple[str, str]]) -> str:
        """Asks AI a question."""
        pass

    async def reply(self, message: Message, context: CallbackContext, answer: str) -> None:
        """Replies with an answer from AI."""
        pass


class TextAsker(Asker):
    """Works with chat completion AI."""

    model = ai.chatgpt.Model(config.openai_model)

    async def ask(self, question: str, history: list[tuple[str, str]]) -> str:
        """Asks AI a question."""
        return await self.model.ask(question, history)

    async def reply(self, message: Message, context: CallbackContext, answer: str) -> None:
        """Replies with an answer from AI."""
        if len(answer) <= MessageLimit.MAX_TEXT_LENGTH:
            answer = markdown.to_html(answer)
            await message.reply_text(answer, parse_mode=ParseMode.HTML)
            return

        doc = io.StringIO(answer)
        caption = (
            textwrap.shorten(answer, width=40, placeholder="...") + " (see attachment for the rest)"
        )
        await context.bot.send_document(
            chat_id=message.chat_id,
            caption=caption,
            filename=f"{message.id}.md",
            document=doc,
        )


class ImagineAsker(Asker):
    """Works with image generation AI."""

    model = ai.dalle.Model()
    size_re = re.compile(r"(256|512|1024)x\1")
    default_size = "512x512"

    def __init__(self) -> None:
        self.caption = ""

    async def ask(self, question: str, history: list[tuple[str, str]]) -> str:
        """Asks AI a question."""
        size = self._extract_size(question)
        self.caption = self._extract_caption(question)
        return await self.model.imagine(prompt=self.caption, size=size)

    async def reply(self, message: Message, context: CallbackContext, answer: str) -> None:
        """Replies with an answer from AI."""
        await message.reply_photo(answer, caption=self.caption)

    def _extract_size(self, question: str) -> str:
        size_match = self.size_re.search(question)
        size = size_match.group(0) if size_match else self.default_size
        return size

    def _extract_caption(self, question: str) -> str:
        caption = self.size_re.sub("", question).strip()
        return caption


def create(question: str) -> Asker:
    """Creates a new asker based on the question asked."""
    if question.startswith("/imagine"):
        return ImagineAsker()
    return TextAsker()
