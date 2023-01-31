# DaVinci (GPT-3) Telegram Bot

This is a poor man's ChatGPT re-created with GPT-3 DaVinci OpenAI model.

## Bot commands

-   `/retry` – Regenerate last bot answer
-   `/help` – Show help

## Setup

1. Get your [OpenAI API](https://openai.com/api/) key

2. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)

3. Edit `config.example.yml` to add your tokens and raname it to `config.yml`:

```bash
mv config.example.yml config.yml
```

4. Run:

```bash
docker compose up --build
```
