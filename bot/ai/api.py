"""HTTP client and helpers shared by the AI providers."""

import httpx

# Server-side tools (web search and fetch) and reasoning can take a while.
client = httpx.AsyncClient(timeout=300.0)


async def post(url: str, headers: dict, body: dict) -> dict:
    """Sends a JSON request and returns the JSON response, raising on errors."""
    response = await client.post(url, headers=headers, json=body)
    try:
        data = response.json()
    except ValueError:
        response.raise_for_status()
        raise
    if response.is_error:
        raise RuntimeError(f"{response.status_code} {_error_message(data)}")
    return data


def _error_message(data) -> str:
    """Extracts the error message from a provider's error response."""
    # OpenAI, Claude and Gemini all use {"error": {"message": ...}}.
    error = data.get("error", data) if isinstance(data, dict) else data
    if isinstance(error, dict):
        return error.get("message") or str(error)
    return str(error)


def ensure_user_first(messages: list[dict]) -> list[dict]:
    """
    Makes sure the conversation starts with a user message.
    It may start with an assistant message after the history is trimmed,
    or when replying to a bot message in a group chat.
    """
    if messages and messages[0]["role"] == "assistant":
        return [{"role": "user", "content": "(continuing the conversation)"}, *messages]
    return messages
