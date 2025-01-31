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
import bot.ai.chat


async def main(question):
    print(f"> {question}")
    fetcher = Fetcher()
    question = await fetcher.substitute_urls(question)
    ai = init_model()
    answer = await ai.ask(prompt=config.openai.prompt, question=question, history=[])
    await fetcher.close()
    lines = textwrap.wrap(answer, width=60)
    for line in lines:
        print(line)


def init_model():
    name = os.getenv("OPENAI_MODEL") or config.openai.model
    return bot.ai.chat.Model(name)


if __name__ == "__main__":
    if len(sys.argv) == 0:
        exit(1)
    asyncio.run(main(sys.argv[1]))
