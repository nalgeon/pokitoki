# DaVinci (GPT-3) Telegram Bot

This is a poor man's ChatGPT rebuilt with the GPT-3 DaVinci OpenAI model. It has a terrible memory, so don't expect it to remember any chat context.

Based on the [chatgpt_telegram_bot](https://github.com/karfly/chatgpt_telegram_bot).

Available commands:

-   `/retry` - retry answering the last question
-   `/help` - show help

## Setup

1. Get your [OpenAI API](https://openai.com/api/) key

2. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)

3. Copy `config.example.yml` to `config.yml` and specify your tokens there.

4. Start the bot:

```bash
docker compose up --build
```
