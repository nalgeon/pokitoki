"""OpenAI-compatible image generation model."""

import httpx
from bot.config import config

client = httpx.AsyncClient(timeout=60.0)


class Model:
    """AI API wrapper."""

    async def imagine(self, prompt: str, size: str) -> str:
        """Generates an image of the specified size according to the description."""
        response = await client.post(
            f"{config.openai.url}/images/generations",
            headers={"Authorization": f"Bearer {config.openai.api_key}"},
            json={
                "model": config.openai.image_model,
                "prompt": prompt,
                "size": size,
                "n": 1,
            },
        )
        resp = response.json()
        if "data" not in resp:
            raise Exception(resp)
        if len(resp["data"]) == 0:
            raise Exception("received an empty answer")
        return resp["data"][0]["url"]
