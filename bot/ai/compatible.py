"""Any OpenAI-compatible Chat Completions API."""

import logging
import re

from bot.ai import api
from bot.config import config

logger = logging.getLogger(__name__)

# Some reasoning models put their thinking into the answer.
THINK_RE = re.compile(r"^\s*<think>.*?</think>", re.DOTALL)


async def complete(model: str, messages: list[dict]) -> str:
    """Sends the messages to the model and returns the answer text."""
    logger.debug("> request: model=%s, messages=%s", model, messages)
    resp = await api.post(
        f"{config.ai.base_url}/chat/completions",
        headers={"Authorization": f"Bearer {config.ai.api_key}"},
        body={"model": model, "messages": messages},
    )
    # Some providers report errors with a successful status code.
    if "choices" not in resp:
        raise RuntimeError(resp.get("error") or resp)
    logger.debug("< response: usage=%s", resp.get("usage"))

    if not resp["choices"]:
        raise RuntimeError("received an empty answer")
    answer = resp["choices"][0]["message"]["content"] or ""
    return THINK_RE.sub("", answer).strip()
