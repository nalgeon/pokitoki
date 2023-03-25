"""
Command-line interface to the OpenAI API.

Usage example:
$ python -m bot.cli "What is your name?"
"""

import asyncio
import os
import sys
import textwrap

import bot.ai.chatgpt
import bot.ai.custom
import bot.ai.davinci

MODEL = os.getenv("OPENAI_MODEL")


async def main(question):
    print(f"> {question}")
    ai = init_model(MODEL)
    answer = await ai.ask(question, history=[])
    lines = textwrap.wrap(answer, width=60)
    for line in lines:
        print(line)


def init_model(name):
    if not name or name == "chatgpt":
        return bot.ai.chatgpt.Model()
    if name == "davinci":
        return bot.ai.davinci.Model()
    return bot.ai.custom.Model(name)


if __name__ == "__main__":
    if len(sys.argv) == 0:
        exit(1)
    asyncio.run(main(sys.argv[1]))
