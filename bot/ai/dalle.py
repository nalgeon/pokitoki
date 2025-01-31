"""DALL-E model from OpenAI."""

import httpx
from bot.config import config

client = httpx.AsyncClient(timeout=60.0)


class Model:
    """OpenAI DALL-E wrapper."""

    async def imagine(self, prompt: str, size: str) -> str:
        """Generates an image of the specified size according to the description."""
        response = await client.post(
            f"{config.openai.url}/images/generations",
            headers={"Authorization": f"Bearer {config.openai.api_key}"},
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "size": size,
                "n": 1,
            },
        )
        resp = response.json()
        if len(resp["data"]) == 0:
            raise ValueError("received an empty answer")
        return resp["data"][0]["url"]
