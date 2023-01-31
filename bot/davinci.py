import openai
from bot import config

openai.api_key = config.openai_api_key

BASE_PROMPT = "Your primary goal is to answer my questions. This may involve writing code or providing helpful information. Be detailed and thorough in your responses. Write code inside <pre>, </pre> tags."


class DaVinci:
    def ask(self, question):
        try:
            prompt = self._generate_prompt(question)
            resp = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                temperature=0.7,
                max_tokens=1000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )

            if len(resp.choices) == 0:
                raise ValueError("received an empty answer")
            answer = resp.choices[0].text
            answer = answer.strip()
            answer = answer.replace(" < ", " &lt; ")
            return answer

        except openai.error.InvalidRequestError as exc:
            raise ValueError("too many tokens to make completion") from exc

        except Exception as exc:
            raise ValueError("failed to answer") from exc

    def _generate_prompt(self, question):
        prompt = BASE_PROMPT
        prompt += "\n\n"
        prompt += f"Question: {question}\n"
        prompt += "Answer: "
        return prompt
