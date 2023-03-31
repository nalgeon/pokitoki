"""ChatGPT (GPT-3.5+) language model from OpenAI."""

import re
import textwrap
import openai
from bot.models import UserMessage
from bot import config

openai.api_key = config.openai_api_key

BASE_PROMPT = "Your primary goal is to answer my questions. This may involve writing code or providing helpful information. Be detailed and thorough in your responses."

# OpenAI counts length in tokens, not charactes,
# so these are approximate numbers (1 token = 4 chars).
# We also leave some characters reserved for the output.
CHARS_PER_TOKEN = 4
MAX_LENGTHS = {
    # max 4096 tokens total, max 3072 for the input
    "gpt-3.5-turbo": int(3 * 1024 * CHARS_PER_TOKEN),
    # max 8192 tokens total, max 7168 for the input
    "gpt-4": int(7 * 1024 * CHARS_PER_TOKEN),
}

# What sampling temperature to use, between 0 and 2.
# Higher values like 0.8 will make the output more random,
# while lower values like 0.2 will make it more focused and deterministic.
SAMPLING_TEMPERATURE = 0.7

# The maximum number of tokens to generate
MAX_OUTPUT_TOKENS = 1000

PRE_RE = re.compile(r"&lt;(/?pre)")


class Model:
    """OpenAI API wrapper."""

    def __init__(self, name: str):
        """Creates a wrapper for a given OpenAI large language model."""
        self.name = name
        self.maxlen = MAX_LENGTHS[name]

    async def ask(self, question: str, history: list[UserMessage]):
        """Asks the language model a question and returns an answer."""
        messages = self._generate_messages(question, history)
        messages = shorten(messages, length=self.maxlen)
        resp = await openai.ChatCompletion.acreate(
            model=self.name,
            messages=messages,
            temperature=SAMPLING_TEMPERATURE,
            max_tokens=MAX_OUTPUT_TOKENS,
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


def shorten(messages: list[dict], length: int) -> list[dict]:
    """
    Truncates messages so that the total number or characters
    does not exceed the specified length.
    """
    total_len = sum(len(m["content"]) for m in messages)
    if total_len <= length:
        return messages

    # exclude older messages to fit into the desired length
    # can't exclude the prompt though
    prompt_msg, messages = messages[0], messages[1:]
    while len(messages) > 1 and total_len > length:
        first, messages = messages[0], messages[1:]
        total_len -= len(first["content"])
    messages = [prompt_msg] + messages
    if total_len <= length:
        return messages

    # there is only one message left, and it's still longer than allowed
    # so we have to shorten it
    prompt_len = len(prompt_msg["content"])
    messages[1]["content"] = textwrap.shorten(
        messages[1]["content"], length - prompt_len, placeholder="..."
    )
    return messages
