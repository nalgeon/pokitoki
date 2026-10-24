"""Google Gemini API."""

import logging

from bot.ai import api
from bot.config import config

logger = logging.getLogger(__name__)

ROLES = {"user": "user", "assistant": "model"}


async def complete(model: str, messages: list[dict]) -> str:
    """Sends the messages to the model and returns the answer text."""
    body = {
        "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
        "contents": [
            {"role": ROLES[m["role"]], "parts": [{"text": m["content"]}]}
            for m in api.ensure_user_first(messages[1:])
        ],
    }
    tools = []
    if "web_search" in config.ai.tools:
        tools.append({"google_search": {}})
    if "web_fetch" in config.ai.tools:
        tools.append({"url_context": {}})
    if tools:
        body["tools"] = tools

    logger.debug("> request: model=%s, messages=%s", model, messages)
    resp = await api.post(
        f"{config.ai.base_url}/models/{model}:generateContent",
        headers={"x-goog-api-key": config.ai.api_key},
        body=body,
    )
    logger.debug("< response: usage=%s", resp.get("usageMetadata"))

    candidates = resp.get("candidates") or []
    if not candidates:
        reason = (resp.get("promptFeedback") or {}).get("blockReason")
        raise RuntimeError(f"received an empty answer: block_reason={reason}")

    # Skip thought summaries, keep the text.
    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    answer = "".join(p["text"] for p in parts if "text" in p and not p.get("thought"))
    if not answer.strip():
        raise RuntimeError(
            f"received an empty answer: finish_reason={candidate.get('finishReason')}"
        )
    return answer.strip()
