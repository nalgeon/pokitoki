"""DALL-E model from OpenAI."""

from openai import AsyncOpenAI
from bot.config import config

openai = AsyncOpenAI(api_key=config.openai.api_key)


class Model:
    """OpenAI DALL-E wrapper."""

    async def imagine(self, prompt: str, size: str) -> str:
        """Generates an image of the specified size according to the description."""
        resp = await openai.images.generate(model="dall-e-3", prompt=prompt, size=size, n=1)
        if len(resp.data) == 0:
            raise ValueError("received an empty answer")
        return resp.data[0].url
