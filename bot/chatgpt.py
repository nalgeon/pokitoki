"""ChatGPT (GPT-3.5) language model from OpenAI."""

import openai
from bot.models import UserMessage
from bot import config

openai.api_key = config.openai_api_key

BASE_PROMPT = "Your primary goal is to answer my questions. This may involve writing code or providing helpful information. Be detailed and thorough in your responses."


class ChatGPT:
    """OpenAI API wrapper."""

    async def ask(self, question: str, history: list[UserMessage]):
        """Asks the language model a question and returns an answer."""
        try:
            messages = self._generate_messages(question, history)
            resp = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            answer = self._prepare_answer(resp)
            return answer

        except openai.error.InvalidRequestError as exc:
            raise ValueError("too many tokens to make completion") from exc

    def _generate_messages(self, question: str, history: list[UserMessage]) -> list[dict]:
        """Builds message history to provide context for the language model."""
        messages = [{"role": "system", "content": BASE_PROMPT}]
        for message in history:
            messages.append({"role": "user", "content": message.question})
            messages.append({"role": "assistant", "content": message.answer})
        messages.append({"role": "user", "content": question})
        return messages

    def _prepare_answer(self, resp):
        """
        Post-processes an answer from the language model.
        """
        if len(resp.choices) == 0:
            raise ValueError("received an empty answer")

        answer = resp.choices[0].message.content
        return answer
