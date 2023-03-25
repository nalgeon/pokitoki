"""
Command-line interface to the OpenAI API.

Usage example:
$ python -m bot.cli "What is your name?"
"""

import asyncio
import sys
import textwrap

from bot.davinci import ChatGPT

ai = ChatGPT()


async def main(question):
    print(f"> {question}")
    answer = await ai.ask(question, history=[])
    lines = textwrap.wrap(answer, width=60)
    for line in lines:
        print(line)


if __name__ == "__main__":
    if len(sys.argv) == 0:
        exit(1)
    asyncio.run(main(sys.argv[1]))
