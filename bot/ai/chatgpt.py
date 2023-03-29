"""ChatGPT (GPT-3.5+) language model from OpenAI."""

import re
import openai
from bot.models import UserMessage
from bot import config

openai.api_key = config.openai_api_key

BASE_PROMPT = "Your primary goal is to answer my questions. This may involve writing code or providing helpful information. Be detailed and thorough in your responses."

PRE_RE = re.compile(r"&lt;(/?pre)")


class Model:
    """OpenAI API wrapper."""

    def __init__(self, name: str):
        """Creates a wrapper for a given OpenAI large language model."""
        self.name = name

    async def ask(self, question: str, history: list[UserMessage]):
        """Asks the language model a question and returns an answer."""
        messages = self._generate_messages(question, history)
        resp = await openai.ChatCompletion.acreate(
            model=self.name,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        answer = self._prepare_answer(resp)
        return answer

    def _generate_messages(self, question: str, history: list[UserMessage]) -> list[dict]:
        """Builds message history to provide context for the language model."""
        messages = [{"role": "system", "content": BASE_PROMPT}]
        for message in history:
            messages.append({"role": "user", "content": message.question})
            messages.append({"role": "assistant", "content": message.answer})
        messages.append({"role": "user", "content": question})
        return messages

    def _prepare_answer(self, resp):
        """Post-processes an answer from the language model."""
        if len(resp.choices) == 0:
            raise ValueError("received an empty answer")

        answer = resp.choices[0].message.content
        answer = answer.strip()
        answer = answer.replace("<", "&lt;")
        answer = PRE_RE.sub(r"<\1", answer)
        return answer
