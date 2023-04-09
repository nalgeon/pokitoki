"""DALL-E model from OpenAI."""

import openai
from bot.config import config

openai.api_key = config.openai.api_key


class Model:
    """OpenAI DALL-E wrapper."""

    async def imagine(self, prompt: str, size: str) -> str:
        """Generates an image of the specified size according to the description."""
        resp = await openai.Image.acreate(prompt=prompt, size=size, n=1)
        if len(resp.data) == 0:
            raise ValueError("received an empty answer")
        return resp.data[0].url
