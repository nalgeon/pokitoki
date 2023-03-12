# ChatGPT Telegram Bot

This is a Telegram chat bot built using the ChatGPT (aka GPT-3.5) language model from OpenAI.

## Private chats

You can use the bot as a personal assistant:

<img src="docs/chat-1.png" alt="Sample chat" width="400">

You can also allow other users to use the bot; list them in the `telegram_usernames` config property.

The bot has a terrible memory, so don't expect it to remember any chat context by default. But you can ask follow-up questions using a plus sign:

<table>
    <tr>
        <td>
            <img src="docs/chat-2.png" alt="Question" width="400">
        </td>
        <td>
            <img src="docs/chat-3.png" alt="Follow-up question" width="400">
        </td>
    </tr>
</table>

Available commands:

-   `/retry` - retry answering the last question
-   `/help` - show help

## Groups

To get an answer from the bot in a group, mention it in a reply to a question, or ask a question directly:

<table>
    <tr>
        <td>
            <img src="docs/chat-4.png" alt="Reply with mention" width="400">
        </td>
        <td>
            <img src="docs/chat-5.png" alt="Direct question" width="400">
        </td>
    </tr>
</table>

The bot will ignore questions from group members unless they are listed in the `telegram_usernames` config property.

## Setup

1. Get your [OpenAI API](https://openai.com/api/) key

2. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)

3. Copy `config.example.yml` to `config.yml` and specify your tokens there.

4. Start the bot:

```bash
docker compose up --build
```

## Credits

Based on the [chatgpt_telegram_bot](https://github.com/karfly/chatgpt_telegram_bot). I removed all the bells and whistles, refactored the code and added comments.
