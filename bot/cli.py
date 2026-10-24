"""
Command-line interface to the OpenAI API.

Usage example:
$ python -m bot.cli "What is your name?"
"""

import asyncio
import os
import sys
import textwrap

import bot.ai.chat
from bot.config import config
from bot.fetcher import Fetcher


async def main(question):
    print(f"> {question}")
    fetcher = Fetcher()
    question = await fetcher.substitute_urls(question)
    ai = init_model()
    answer = await ai.ask(prompt=config.ai.prompt, question=question, history=[])
    await fetcher.close()
    lines = textwrap.wrap(answer, width=60)
    for line in lines:
        print(line)


def init_model():
    name = os.getenv("AI_MODEL") or config.ai.model
    return bot.ai.chat.Model(name)


if __name__ == "__main__":
    if len(sys.argv) == 0:
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
