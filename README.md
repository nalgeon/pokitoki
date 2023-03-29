# ChatGPT Telegram Bot

This is a Telegram chat bot built using the ChatGPT (GPT-3.5 or GPT-4) language model from OpenAI.

Notable features:

-   Both one-on-one and group chats.
-   Direct questions or mentions.
-   Ask again by retrying or editing the last message.
-   Follow-up questions.
-   Custom commands.

## Personal chats

The bot acts as your personal assistant:

<img src="docs/chat-1.png" alt="Sample chat" width="400">

To allow other users to use the bot, list them in the `telegram_usernames` config property.

The bot has a terrible memory, so don't expect it to remember any chat context by default. You can, however, reply with a follow-up question. Alternatively, use a plus sign to follow up:

<table>
    <tr>
        <td>
            <img src="docs/chat-2.png" alt="Follow-up by reply" width="400">
        </td>
        <td>
            <img src="docs/chat-3.png" alt="Follow-up by plus sign" width="400">
        </td>
    </tr>
</table>

Available commands:

-   `/retry` - retry answering the last question
-   `/help` - show help

To rephrase or add to the last question, simply edit it. The bot will then answer the updated question.

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

To make the bot reply to group members, list the group id in the `telegram_chat_ids` config property. Otherwise, the bot will ignore questions from group members unless they are listed in the `telegram_usernames` config property.

If you don't know the group id, run the `/version` bot command in a group to find it:

```
Chat information:
- id: -1001405001234
- title: My Favorite Group
- type: supergroup

Bot information:
- id: 5930739038
- name: @pokitokibot
- version: 70
- usernames: 6 users
- chat IDs: []
- access to messages: True

AI information:
- model: gpt-3.5-turbo
- history depth: 3
- commands: ['bugfix', 'proofread', 'summarize', 'translate']
```

## Custom commands (🚧 experimental)

Use short commands to save time and ask the bot to do something specific with your questions. For example, ask it to proofread your writing with a `!proofread` command:

> !proofread I can has write java programz

Answer:

> I can write Java programs.
>
> Explanation:
>
> -   "can has" is not proper English, so it has been changed to "can write".
> -   "programz" is not the correct spelling of "programs", so it has been corrected.
> -   The capitalization of "Java" has been corrected to follow proper naming conventions for programming languages.
> -   The period has been added at the end to form a complete sentence.

There are several built-in commands:

-   `bugfix` fixes your code.
-   `proofread` fixes your writing.
-   `translate` translates your text into English.
-   `summarize` gives a two paragraph summary of a text.

You can add your own commands. See `config.example.yml` for details.

## Setup

1. Get your [OpenAI API](https://openai.com/api/) key

2. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)

3. Copy `config.example.yml` to `config.yml` and specify your tokens there.

4. Start the bot:

```bash
docker compose up --build
```

## Credits

Based on the [chatgpt_telegram_bot](https://github.com/karfly/chatgpt_telegram_bot).
