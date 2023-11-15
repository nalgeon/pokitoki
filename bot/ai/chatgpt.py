"""ChatGPT (GPT-3.5+) language model from OpenAI."""

import logging
from typing import Optional
from openai import AsyncAzureOpenAI, AsyncOpenAI
import tiktoken
from bot.config import config

if config.openai.azure:
    openai = AsyncAzureOpenAI(
        api_key=config.openai.api_key,
        api_version=config.openai.azure["version"],
        azure_endpoint=config.openai.azure["endpoint"],
        azure_deployment=config.openai.azure["deployment"],
    )
else:
    openai = AsyncOpenAI(api_key=config.openai.api_key)

encoding = tiktoken.get_encoding("cl100k_base")
logger = logging.getLogger(__name__)

# Supported models and their context windows
MODELS = {
    "gpt-4-1106-preview": 128000,
    "gpt-4-vision-preview": 128000,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-3.5-turbo-1106": 16385,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-16k": 16385,
}


class Model:
    """OpenAI API wrapper."""

    def __init__(self, name: Optional[str] = None) -> None:
        """Creates a wrapper for a given OpenAI large language model."""
        self.name = name

    async def ask(self, prompt: str, question: str, history: list[tuple[str, str]]) -> str:
        """Asks the language model a question and returns an answer."""
        # maximum number of input tokens
        model = self.name or config.openai.model
        n_input = _calc_n_input(model, n_output=config.openai.params["max_tokens"])
        messages = self._generate_messages(prompt, question, history)
        messages = shorten(messages, length=n_input)
        params = config.openai.params
        logger.debug(
            f"> chat request: model=%s, params=%s, messages=%s",
            model,
            params,
            messages,
        )
        resp = await openai.chat.completions.create(
            model=model,
            messages=messages,
            **params,
        )
        logger.debug(
            "< chat response: prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
            resp.usage.prompt_tokens,
            resp.usage.completion_tokens,
            resp.usage.total_tokens,
        )
        answer = self._prepare_answer(resp)
        return answer

    def _generate_messages(
        self, prompt: str, question: str, history: list[tuple[str, str]]
    ) -> list[dict]:
        """Builds message history to provide context for the language model."""
        messages = [{"role": "system", "content": prompt or config.openai.prompt}]
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


def _calc_n_input(name: str, n_output: int) -> int:
    """
    Calculates the maximum number of input tokens
    according to the model and the maximum number of output tokens.
    """
    # OpenAI counts length in tokens, not charactes.
    # We need to leave some tokens reserved for the output.
    n_total = MODELS.get(name, 4096)  # max 4096 tokens total by default
    return n_total - n_output
