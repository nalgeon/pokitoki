"""OpenAI-compatible language model."""

import logging

import httpx

from bot.config import config

client = httpx.AsyncClient(timeout=60.0)
logger = logging.getLogger(__name__)

# Number of tokens reserved for the answer when trimming the history.
N_OUTPUT = 4096

# Known models and their context windows
MODELS = {
    # Gemini
    "gemini-4-argon": 1_048_576,
    "gemini-3.8-flash": 1_048_576,
    "gemini-3.6-flash": 1_048_576,
    "gemini-3.5-flash-lite": 1_048_576,
    "gemini-3.1-pro-preview": 1_048_576,
    "gemini-3.1-flash-lite": 1_048_576,
    "gemini-3-flash-preview": 1_048_576,
    # OpenAI
    "gpt-6.1-sol": 1_050_000,
    "gpt-6-sol": 1_050_000,
    "gpt-6-astra": 1_050_000,
    "gpt-6-luna": 1_050_000,
    "gpt-5.6-sol": 1_050_000,
    "gpt-5.6-terra": 1_050_000,
    "gpt-5.6-luna": 1_050_000,
    "gpt-5.5": 1_050_000,
    "gpt-5.4": 1_050_000,
    "gpt-5.4-mini": 400_000,
    "gpt-5.2": 400_000,
}


class Model:
    """AI API wrapper."""

    def __init__(self, name: str) -> None:
        """Creates a wrapper for a given OpenAI large language model."""
        self.name = name

    async def ask(self, prompt: str, question: str, history: list[tuple[str, str]]) -> str:
        """Asks the language model a question and returns an answer."""
        model = self.name
        n_input = _calc_n_input(model, n_output=N_OUTPUT)
        messages = self._generate_messages(prompt, question, history)
        messages = shorten(messages, length=n_input)

        logger.debug("> chat request: model=%s, messages=%s", model, messages)
        response = await client.post(
            f"{config.ai.url}/chat/completions",
            headers={"Authorization": f"Bearer {config.ai.api_key}"},
            json={"model": model, "messages": messages},
        )
        resp = response.json()
        if "usage" not in resp:
            raise RuntimeError(resp)
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
        prompt: str,
        question: str,
        history: list[tuple[str, str]],
    ) -> list[dict]:
        """Builds message history to provide context for the language model."""
        messages = [{"role": "system", "content": prompt or config.ai.prompt}]
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
    n_total = MODELS.get(name) or config.ai.window
    logger.debug("model=%s, n_total=%s, n_output=%s", name, n_total, n_output)
    return n_total - n_output
