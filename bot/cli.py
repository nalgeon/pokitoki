"""
Command-line interface to the AI model.

Usage example:
$ python -m bot.cli "What is your name?"
"""

import asyncio
import os
import sys
import textwrap

from bot.ai import chat
from bot.config import config
from bot.fetcher import Fetcher


async def main(question):
    print(f"> {question}")
    if not chat.can_fetch():
        fetcher = Fetcher()
        question = await fetcher.substitute_urls(question)
        await fetcher.close()
    model = os.getenv("AI_MODEL") or config.ai.model
    answer = await chat.ask(model, prompt=config.ai.prompt, question=question, history=[])
    lines = textwrap.wrap(answer, width=60)
    for line in lines:
        print(line)


if __name__ == "__main__":
    if len(sys.argv) == 0:
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
