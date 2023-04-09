"""DaVinci (GPT-3) language model from OpenAI."""

import re
import openai
from bot.config import config

openai.api_key = config.openai.api_key

BASE_PROMPT = "Your primary goal is to answer my questions. This may involve writing code or providing helpful information. Be detailed and thorough in your responses. Write code inside <pre>, </pre> tags."

PRE_RE = re.compile(r"&lt;(/?pre)")


class Model:
    """OpenAI API wrapper."""

    async def ask(self, question, history=None):
        """Asks the language model a question and returns an answer."""
        history = history or []
        prompt = self._generate_prompt(question, history)
        resp = await openai.Completion.acreate(
            model="text-davinci-003",
            prompt=prompt,
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        answer = self._prepare_answer(resp)
        return answer

    def _generate_prompt(self, question, history):
        """Builds a prompt to provide context for the language model."""
        prompt = BASE_PROMPT
        for q, a in history:
            prompt += "\n"
            prompt += f"Question: {q}\n"
            prompt += f"Answer: {a}\n"
        prompt += "\n"
        prompt += f"Question: {question}\n"
        prompt += "Answer: "
        return prompt

    def _prepare_answer(self, resp):
        """
        Post-processes an answer from the language model,
        fixing possible HTML formatting issues.
        """
        if len(resp.choices) == 0:
            raise ValueError("received an empty answer")

        answer = resp.choices[0].text
        answer = answer.strip()
        answer = answer.replace("<", "&lt;")
        answer = PRE_RE.sub(r"<\1", answer)
        return answer
