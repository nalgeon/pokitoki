"""Claude API (Messages API)."""

import logging

from bot.ai import api
from bot.config import config

logger = logging.getLogger(__name__)

# Maximum number of output tokens (required by the API), including thinking.
MAX_TOKENS = 16000

# Maximum number of tool uses per answer, to keep costs in check.
MAX_TOOL_USES = 5

# How many times to resume a turn paused by the server-side tool loop.
MAX_CONTINUATIONS = 3


async def complete(model: str, messages: list[dict]) -> str:
    """Sends the messages to the model and returns the answer text."""
    body = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": messages[0]["content"],
        "messages": api.ensure_user_first(messages[1:]),
    }
    tools = _tools(model)
    if tools:
        body["tools"] = tools

    logger.debug("> request: model=%s, messages=%s", model, messages)
    texts = []
    for _ in range(MAX_CONTINUATIONS + 1):
        resp = await api.post(
            f"{config.ai.base_url}/messages",
            headers={"x-api-key": config.ai.api_key, "anthropic-version": "2023-06-01"},
            body=body,
        )
        logger.debug("< response: stop_reason=%s, usage=%s", resp["stop_reason"], resp["usage"])
        # Skip thinking and tool blocks, keep the text.
        # Text with citations is split into several blocks, so join them as is.
        texts.extend(block["text"] for block in resp["content"] if block["type"] == "text")
        if resp["stop_reason"] != "pause_turn":
            break
        # The server paused a long tool loop, send the content back to resume it.
        body["messages"] = [*body["messages"], {"role": "assistant", "content": resp["content"]}]

    answer = "".join(texts).strip()
    if not answer:
        raise RuntimeError(f"received an empty answer: stop_reason={resp['stop_reason']}")
    return answer


def _tools(model: str) -> list[dict]:
    """Returns the server-side tools enabled in the config."""
    # Haiku models only support the basic tool versions,
    # the others support the newer ones with dynamic filtering.
    basic = "haiku" in model
    tools = []
    if "web_search" in config.ai.tools:
        version = "20250305" if basic else "20260209"
        tools.append(
            {"type": f"web_search_{version}", "name": "web_search", "max_uses": MAX_TOOL_USES}
        )
    if "web_fetch" in config.ai.tools:
        version = "20250910" if basic else "20260209"
        tools.append(
            {"type": f"web_fetch_{version}", "name": "web_fetch", "max_uses": MAX_TOOL_USES}
        )
    return tools
