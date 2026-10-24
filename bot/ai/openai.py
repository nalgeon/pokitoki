"""OpenAI Responses API."""

import logging

from bot.ai import api
from bot.config import config

logger = logging.getLogger(__name__)


async def complete(model: str, messages: list[dict]) -> str:
    """Sends the messages to the model and returns the answer text."""
    body = {
        "model": model,
        "instructions": messages[0]["content"],
        "input": messages[1:],
        "store": False,
    }
    # There is no separate fetch tool: web search opens pages as needed.
    if "web_search" in config.ai.tools:
        body["tools"] = [{"type": "web_search"}]

    logger.debug("> request: model=%s, messages=%s", model, messages)
    resp = await api.post(
        f"{config.ai.base_url}/responses",
        headers={"Authorization": f"Bearer {config.ai.api_key}"},
        body=body,
    )
    logger.debug("< response: status=%s, usage=%s", resp.get("status"), resp.get("usage"))

    # Skip reasoning and tool call items, keep the text of the messages.
    answer = "".join(
        part["text"]
        for item in resp.get("output") or []
        if item["type"] == "message"
        for part in item["content"]
        if part["type"] == "output_text"
    )
    if not answer:
        details = resp.get("error") or resp.get("incomplete_details") or resp.get("status")
        raise RuntimeError(f"received an empty answer: {details}")
    return answer.strip()
