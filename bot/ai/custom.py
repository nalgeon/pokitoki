"""Fine-tuned language model from OpenAI."""

import re
import openai
from bot.config import config

openai.api_key = config.openai.api_key

DEFAULT_STOP = "###"
PRE_RE = re.compile(r"&lt;(/?pre)")


class Model:
    """
    Fine-tuned OpenAI model.
    Read more about fine-tuning at https://platform.openai.com/docs/guides/fine-tuning/
    """

    def __init__(self, name, stop=DEFAULT_STOP):
        """
        Creates a wrapper for a fine-tuned OpenAI model
        with a given name and stop sequence.
        """
        self.name = name
        self.stop = stop

    async def ask(self, question, history=None) -> str:
        """Asks the language model a question and returns an answer."""
        try:
            history = history or []
            prompt = self._generate_prompt(question, history)
            resp = await openai.Completion.acreate(
                model=self.name,
                prompt=prompt,
                temperature=0.7,
                max_tokens=1000,
                stop=[self.stop],
            )
            answer = self._prepare_answer(resp)
            return answer

        except openai.error.InvalidRequestError as exc:
            raise ValueError("too many tokens to make completion") from exc

    def _generate_prompt(self, question, history):
        """Builds a prompt to provide context for the language model."""
        prompt = ""
        for q, a in history:
            prompt += f"Q: {q} -> {a}{self.stop}"
        prompt += f"Q: {question} ->"
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
