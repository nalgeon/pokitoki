import datetime as dt
import config
import openai

openai.api_key = config.openai_api_key


CHAT_MODES = {
    "assistant": {
        "name": "👩🏼‍🎓 Assistant",
        "welcome_message": "👩🏼‍🎓 How can I help you?",
        "prompt_start": "Your primary goal is to answer my questions. This may involve writing code or providing helpful information. Be detailed and thorough in your responses. Write code inside <pre>, </pre> tags.",
    },
}


class ChatGPT:
    def __init__(self):
        pass

    def send_message(self, message, chat_mode="assistant"):
        if chat_mode not in CHAT_MODES.keys():
            raise ValueError(f"Chat mode {chat_mode} is not supported")

        answer = None
        while answer is None:
            prompt = self._generate_prompt(message, chat_mode)
            try:
                start = dt.datetime.now()
                r = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=1000,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                )
                elapsed = dt.datetime.now() - start
                print(f"getting an answer took {elapsed}")
                answer = r.choices[0].text
                answer = answer.strip()

            except openai.error.InvalidRequestError as e:  # too many tokens
                raise ValueError("too many tokens to make completion") from e

        return answer

    def _generate_prompt(self, message, chat_mode):
        prompt = CHAT_MODES[chat_mode]["prompt_start"]
        prompt += "\n\n"
        prompt += f"Question: {message}\n"
        prompt += "Answer: "
        return prompt
