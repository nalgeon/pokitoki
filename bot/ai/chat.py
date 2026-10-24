"""Language model chat, backed by one of the supported AI providers."""

import logging

from bot.ai import claude, compatible, gemini, openai
from bot.config import config

logger = logging.getLogger(__name__)

PROVIDERS = {
    "openai": openai,
    "claude": claude,
    "gemini": gemini,
    "compatible": compatible,
}

# Number of tokens reserved for the answer when trimming the history.
N_OUTPUT = 4096

# Known models and their context windows
MODELS = {
    # Claude
    "claude-fable-5-1": 1_000_000,
    "claude-fable-5": 1_000_000,
    "claude-opus-5-5": 1_000_000,
    "claude-opus-5": 1_000_000,
    "claude-opus-4-8": 1_000_000,
    "claude-opus-4-7": 1_000_000,
    "claude-opus-4-6": 1_000_000,
    "claude-sonnet-5-5": 1_000_000,
    "claude-sonnet-5": 1_000_000,
    "claude-sonnet-4-6": 1_000_000,
    "claude-haiku-5-5": 1_000_000,
    "claude-haiku-4-5": 200_000,
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


async def ask(model: str, prompt: str, question: str, history: list[tuple[str, str]]) -> str:
    """Asks the language model a question and returns an answer."""
    provider = PROVIDERS.get(config.ai.provider)
    if not provider:
        raise ValueError(f"Unknown AI provider: {config.ai.provider}")
    n_input = _calc_n_input(model, n_output=N_OUTPUT)
    messages = _generate_messages(prompt, question, history)
    messages = shorten(messages, length=n_input)
    return await provider.complete(model, messages)


def can_fetch() -> bool:
    """Returns True if the model fetches URLs from the question by itself."""
    return config.ai.provider in ("claude", "gemini") and "web_fetch" in config.ai.tools


def _generate_messages(prompt: str, question: str, history: list[tuple[str, str]]) -> list[dict]:
    """Builds message history to provide context for the language model."""
    messages = [{"role": "system", "content": prompt or config.ai.prompt}]
    for prev_question, prev_answer in history:
        # in group chats, the history only contains the previous answer
        if prev_question:
            messages.append({"role": "user", "content": prev_question})
        messages.append({"role": "assistant", "content": prev_answer})
    messages.append({"role": "user", "content": question})
    return messages


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
    # Models count length in tokens, not charactes.
    # We need to leave some tokens reserved for the output.
    n_total = MODELS.get(name) or config.ai.window
    logger.debug("model=%s, n_total=%s, n_output=%s", name, n_total, n_output)
    return n_total - n_output
