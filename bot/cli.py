"""
Command-line interface to the OpenAI API.

Usage example:
$ python -m bot.cli "What is your name?"
"""

import asyncio
import os
import sys
import textwrap

from bot.config import config
from bot.fetcher import Fetcher
import bot.ai.chatgpt
import bot.ai.custom
import bot.ai.davinci


async def main(question):
    print(f"> {question}")
    fetcher = Fetcher()
    question = await fetcher.substitute_urls(question)
    ai = init_model()
    answer = await ai.ask(question, history=[])
    await fetcher.close()
    lines = textwrap.wrap(answer, width=60)
    for line in lines:
        print(line)


def init_model():
    name = os.getenv("OPENAI_MODEL") or config.openai.model
    if name.startswith("gpt"):
        return bot.ai.chatgpt.Model(name)
    if name == "davinci":
        return bot.ai.davinci.Model()
    return bot.ai.custom.Model(name)


if __name__ == "__main__":
    if len(sys.argv) == 0:
        exit(1)
    asyncio.run(main(sys.argv[1]))
