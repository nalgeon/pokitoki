"""OpenAI-compatible language model."""

import logging
import httpx
from bot.config import config

client = httpx.AsyncClient(timeout=60.0)
logger = logging.getLogger(__name__)

# Known models and their context windows
MODELS = {
    # Gemini
    "gemini-2.5-pro": 1_048_576,
    "gemini-2.5-flash": 1_048_576,
    "gemini-2.5-flash-lite": 1_048_576,
    "gemini-2.0-flash": 1_048_576,
    "gemini-1.5-flash": 1_048_576,
    "gemini-1.5-flash-8b": 1_048_576,
    "gemini-1.5-pro": 2_097_152,
    # OpenAI
    "o1": 200000,
    "o1-mini": 128000,
    "o1-pro": 200000,
    "o3": 200000,
    "o3-mini": 200000,
    "o4": 200000,
    "o4-mini": 200000,
    "gpt-5.1": 128000,
    "gpt-5": 128000,
    "gpt-5-mini": 128000,
    "gpt-5-nano": 128000,
    "gpt-4.1": 1_047_576,
    "gpt-4.1-mini": 1_047_576,
    "gpt-4.1-nano": 1_047_576,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4-turbo-preview": 128000,
    "gpt-4-vision-preview": 128000,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-3.5-turbo": 16385,
}

# Prompt role name overrides.
ROLE_OVERRIDES = {
    "o1": "user",
    "o1-mini": "user",
    "o1-pro": "user",
    "o3": "user",
    "o3-mini": "user",
    "o4": "user",
    "o4-mini": "user",
}

# Model parameter overrides.
PARAM_OVERRIDES = {
    "gpt-5.1": lambda params: {},
    "gpt-5": lambda params: {},
    "gpt-5-mini": lambda params: {},
    "gpt-5-nano": lambda params: {},
    "o1": lambda params: {},
    "o1-mini": lambda params: {},
    "o1-pro": lambda params: {},
    "o3": lambda params: {},
    "o3-mini": lambda params: {},
    "o4": lambda params: {},
    "o4-mini": lambda params: {},
}


class Model:
    """AI API wrapper."""

    def __init__(self, name: str) -> None:
        """Creates a wrapper for a given OpenAI large language model."""
        self.name = name

    async def ask(self, prompt: str, question: str, history: list[tuple[str, str]]) -> str:
        """Asks the language model a question and returns an answer."""
        model = self.name
        prompt_role = ROLE_OVERRIDES.get(model) or "system"
        params_func = PARAM_OVERRIDES.get(model) or (lambda params: params)

        n_input = _calc_n_input(model, n_output=config.openai.params["max_tokens"])
        messages = self._generate_messages(prompt_role, prompt, question, history)
        messages = shorten(messages, length=n_input)

        params = params_func(config.openai.params)
        logger.debug(
            "> chat request: model=%s, params=%s, messages=%s",
            model,
            params,
            messages,
        )
        response = await client.post(
            f"{config.openai.url}/chat/completions",
            headers={"Authorization": f"Bearer {config.openai.api_key}"},
            json={
                "model": model,
                "messages": messages,
                **params,
            },
        )
        resp = response.json()
        if "usage" not in resp:
            raise Exception(resp)
        logger.debug(
            "< chat response: prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
            resp["usage"]["prompt_tokens"],
            resp["usage"]["completion_tokens"],
            resp["usage"]["total_tokens"],
        )
        answer = self._prepare_answer(resp)
        return answer

    def _generate_messages(
        self,
        prompt_role: str,
        prompt: str,
        question: str,
        history: list[tuple[str, str]],
    ) -> list[dict]:
        """Builds message history to provide context for the language model."""
        messages = [{"role": prompt_role, "content": prompt or config.openai.prompt}]
        for prev_question, prev_answer in history:
            messages.append({"role": "user", "content": prev_question})
            messages.append({"role": "assistant", "content": prev_answer})
        messages.append({"role": "user", "content": question})
        return messages

    def _prepare_answer(self, resp) -> str:
        """Post-processes an answer from the language model."""
        if len(resp["choices"]) == 0:
            raise ValueError("received an empty answer")

        answer = resp["choices"][0]["message"]["content"]
        answer = answer.strip()
        return answer


def shorten(messages: list[dict], length: int) -> list[dict]:
    """
    Truncates messages so that the total number or tokens
    does not exceed the specified length.
    """
    lengths = [_calc_tokens(m["content"]) for m in messages]
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
    tokens = messages[1]["content"].split()[:maxlen]
    messages[1]["content"] = " ".join(tokens)
    return messages


def _calc_tokens(s: str) -> int:
    """Calculates the number of tokens in a string."""
    return int(len(s.split()) * 1.2)


def _calc_n_input(name: str, n_output: int) -> int:
    """
    Calculates the maximum number of input tokens
    according to the model and the maximum number of output tokens.
    """
    # OpenAI counts length in tokens, not charactes.
    # We need to leave some tokens reserved for the output.
    n_total = MODELS.get(name) or config.openai.window
    logger.debug("model=%s, n_total=%s, n_output=%s", name, n_total, n_output)
    return n_total - n_output
