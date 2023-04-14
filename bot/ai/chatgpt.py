"""ChatGPT (GPT-3.5+) language model from OpenAI."""

import logging
import openai
import tiktoken
from bot.config import config

logger = logging.getLogger(__name__)

openai.api_key = config.openai.api_key
encoding = tiktoken.get_encoding("cl100k_base")

# OpenAI counts length in tokens, not charactes.
# We also leave some tokens reserved for the output.
MAX_LENGTHS = {
    # max 4096 tokens total, max 3072 for the input
    "gpt-3.5-turbo": int(3 * 1024),
    # max 8192 tokens total, max 7168 for the input
    "gpt-4": int(7 * 1024),
}


class Model:
    """OpenAI API wrapper."""

    def __init__(self, name: str) -> None:
        """Creates a wrapper for a given OpenAI large language model."""
        self.name = name
        self.maxlen = MAX_LENGTHS[name]

    async def ask(self, question: str, history: list[tuple[str, str]]) -> str:
        """Asks the language model a question and returns an answer."""
        messages = self._generate_messages(question, history)
        messages = shorten(messages, length=self.maxlen)
        params = self._prepare_params()
        resp = await openai.ChatCompletion.acreate(
            model=self.name,
            messages=messages,
            **params,
        )
        logger.debug(
            "prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
            resp.usage.prompt_tokens,
            resp.usage.completion_tokens,
            resp.usage.total_tokens,
        )
        answer = self._prepare_answer(resp)
        return answer

    def _prepare_params(self) -> dict:
        params = config.openai.params.copy()
        if config.openai.azure:
            params["api_type"] = "azure"
            params["api_base"] = config.openai.azure["endpoint"]
            params["api_version"] = config.openai.azure["version"]
            params["deployment_id"] = config.openai.azure["deployment"]
        return params

    def _generate_messages(self, question: str, history: list[tuple[str, str]]) -> list[dict]:
        """Builds message history to provide context for the language model."""
        messages = [{"role": "system", "content": config.openai.prompt}]
        for prev_question, prev_answer in history:
            messages.append({"role": "user", "content": prev_question})
            messages.append({"role": "assistant", "content": prev_answer})
        messages.append({"role": "user", "content": question})
        return messages

    def _prepare_answer(self, resp) -> str:
        """Post-processes an answer from the language model."""
        if len(resp.choices) == 0:
            raise ValueError("received an empty answer")

        answer = resp.choices[0].message.content
        answer = answer.strip()
        return answer


def shorten(messages: list[dict], length: int) -> list[dict]:
    """
    Truncates messages so that the total number or tokens
    does not exceed the specified length.
    """
    lengths = [len(encoding.encode(m["content"])) for m in messages]
    total_len = sum(lengths)
    if total_len <= length:
        return messages

    # exclude older messages to fit into the desired length
    # can't exclude the prompt though
    prompt_msg, messages = messages[0], messages[1:]
    prompt_len, lengths = lengths[0], lengths[1:]
    while len(messages) > 1 and total_len > length:
        messages = messages[1:]
        first_len, lengths = lengths[0], lengths[1:]
        total_len -= first_len
    messages = [prompt_msg] + messages
    if total_len <= length:
        return messages

    # there is only one message left, and it's still longer than allowed
    # so we have to shorten it
    maxlen = length - prompt_len
    tokens = encoding.encode(messages[1]["content"])
    tokens = tokens[:maxlen]
    messages[1]["content"] = encoding.decode(tokens)
    return messages
