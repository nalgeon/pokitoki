# Humble AI Telegram Bot

This is a Telegram chat bot (AI assistant) that uses large language models from [OpenAI](https://platform.openai.com/), [Claude](https://platform.claude.com/), [Gemini](https://ai.google.dev/gemini-api/docs) or any OpenAI-compatible provider (like [OpenRouter](https://openrouter.ai/docs/) or [Nebius](https://docs.nebius.com/)).

Notable features:

- Both one-on-one and group chats.
- Direct questions, mentions, follow-ups.
- Web search and access to external links (articles, code, data).
- Shortcuts (custom AI commands).
- Custom per-chat prompts and models.
- On-the-fly configuration.

Read on for a detailed feature description or jump to [setup](#setup).

## Personal chats

The bot acts as your personal assistant:

> 🧑 Explain Apache Kafka to a three year old
>
> 🤖 Apache Kafka is like a big mailbox that helps different toys (computers) send messages to each other. When one toy has something to say, it puts a message in the mailbox, and other toys can take that message out and read it. This way, they can talk and share things quickly!

To allow other users to use the bot, list them in the `telegram.usernames` config property.

The bot remembers the conversation while you keep talking. If you ask a question within 5 minutes after the bot's answer, it continues the conversation:

> 🧑 Yesterday, all my troubles seemed so far away
>
> 🤖 It sounds like you're quoting "Yesterday" by The Beatles. It's a classic song about longing and nostalgia.
>
> 🧑 who wrote it?
>
> 🤖 "Yesterday" was written by Paul McCartney of The Beatles.

After a longer pause, the bot starts a new conversation. To start over sooner, use the `/new` command (`/new question` starts over and asks the question right away). To pick up a conversation after a pause, start the question with a plus sign (`+ who wrote it?`) or reply to the bot's message (`Ctrl/Cmd + ↑`). After a pause, a reply continues from the message you replied to.

Change the pause length with the `conversation.timeout` config property (in minutes). Set it to `0` to start a new conversation with every question, unless it starts with a plus or is a reply.

Available commands:

- `/new` - start a new conversation
- `/retry` - retry answering the last question
- `/help` - show help
- `/version` - show bot info

To rephrase or add to the last question, simply edit it. The bot will then answer the updated question.

## Groups

To get an answer from the bot in a group, mention it in a reply to a question:

> 🧑 I forgot who played Ramsy in the Game of Thrones 😕<br>
> 🧑 ↳ @pokitokibot help
>
> 🤖 Ramsay Bolton in Game of Thrones was played by Iwan Rheon.

Or ask a question directly:

> 🧑 @pokitokibot Who played Ramsy in the Game of Thrones?
>
> 🤖 Iwan Rheon played Ramsay Bolton in Game of Thrones.

To make the bot reply to group members, list the group id in the `telegram.chat_ids` config property. Otherwise, the bot will ignore questions from group members unless they are listed in the `telegram.usernames` config property.

If you don't know the group id, run the `/version` bot command in a group to find it:

```
Chat information:
- id: -1001405001234
- title: My Favorite Group
- type: supergroup
...
```

## Web search and external links

With the `openai`, `claude` and `gemini` providers, the model can search the web by itself, using the provider's server-side tools (`ai.tools`). With `claude` and `gemini`, it also opens links from your questions. Providers may charge extra for tool use.

> 🧑 Name 1 major feature of the Go 1.23 release https://tip.golang.org/doc/go1.23 Be brief!
>
> 🤖 A major feature of Go 1.23 is the inclusion of the "range-over-func" experiment as a standard language feature, allowing the "range" clause in "for-range" loops to accept iterator functions.

When the model can't open links by itself (the `openai` and `compatible` providers, or when the `web_fetch` tool is disabled), the bot fetches the remote content and feeds it to the model. In this case, only text content is supported (articles, code, data), not PDFs, images or audio.

If you _don't want_ the bot to fetch the URL in this case, quote it:

> 🧑 Exact contents of "https://antonz.org/robots.txt"
>
> 🤖 I can't access external websites directly. You can check the contents of a robots.txt file by visiting the URL in your browser.

## Shortcuts

Use short commands to save time and ask the bot to do something specific with your questions. For example, ask it to proofread your writing with a `!proofread` command:

> 🧑 !proofread I can has write java programz
>
> 🤖 Revised text: "I can write Java programs."
>
> Changes made:
>
> 1. Removed "has" for grammatical correctness; "can" does not require "has."
> 2. Corrected "java" to "Java" for proper capitalization as it is a proper noun.
> 3. Changed "programz" to "programs" for correct spelling and clarity.

There are several built-in shortcuts:

- `bugfix` fixes your code.
- `proofread` fixes your writing.
- `translate` translates your text into English.
- `summarize` gives a two paragraph summary of a text.

You can add your own shortcuts. See `config.example.yml` for details.

## Per-chat settings

You can customize some settings on a per-chat basis. For example, to have one prompt for your private chat with a bot and another prompt for a group chat that you manage.

### Prompt

Set a custom prompt for the current chat with the `/prompt` command:

> 🧑 /prompt You are an evil genius. Reply with an evil laugh.

To return to the default prompt, use `/prompt reset`.

The `/prompt` command in group chats is only available to admins - users listed in the `telegram.admins` property.

### Model

Set a custom AI model for the current chat with the `/model` command:

> 🧑 /model o3-mini

To return to the default model, use `/model reset`.

The `/model` command in group chats is only available to admins - users listed in the `telegram.admins` property.

## Other useful features

The convenience of working with a bot is made up of small details. Here are some situations where it can save you time and effort.

### Forwarding

Say you received a message from a colleague or read a post on a channel and want to ask a question. Simply forward the message to the bot and answer the clarifying question it asks.

### Ask with file

To ask a question about a document, send it as a file and write the question in the caption. The bot will read the file contents and answer. Currently only supports text content (plain text, code, data), not PDFs, images or audio. Sending multiple files is also not supported.

### Reply with attachment

Sometimes the AI's reply exceeds the maximum message length set by Telegram. In this case, the bot will not fail or spam you with messages. Instead, it will send the answer as an attached text file.

### Edited question

To rephrase or add to the last question, edit it (`↑` shortcut). The bot will notice this and respond to the clarified question.

## Bot information

Use the `/version` command to print detailed information about the current chat, bot, and AI model:

```
Chat information:
- id: -1001405001234
- title: My Favorite Group
- type: supergroup

Bot information:
- id: 5930739038
- name: @pokitokibot
- version: 2026.10.24
- usernames: 6 users
- admins: 1 users
- chat IDs: []
- access to messages: True

AI information:
- provider: openai (api.openai.com)
- model: gpt-6-luna
- history depth: 5
- conversation timeout: 5 min
- shortcuts: proofread, summarize
```

## Configuration

Use the `/config` command to change almost any setting on the fly, without restarting the bot.

- Add or remove users and chats allowed to interact with the bot (`telegram.usernames` and `telegram.chat_ids`).
- Adjust the AI provider (`ai.provider` and `ai.url`), API key (`ai.api_key`), model (`ai.model`), prompt (`ai.prompt`) and tools (`ai.tools`).
- Add or change AI shortcuts (`shortcuts`).
- Change any other config property.

To view a specific config property, put its name after `/config`:

```
/config telegram.usernames
/config ai.prompt
```

To change a specific config property, put its name and value after `/config`:

```
/config telegram.usernames ["alice", "bob", "cindy"]
/config ai.provider claude
/config ai.model claude-opus-5-5
/config ai.prompt "You are an evil AI bot"
```

When working with list properties like `telegram.usernames`, you can add or remove individual items instead of redefining the whole list:

```
/config telegram.usernames +cindy
/config telegram.usernames -bob
```

The `/config` command is only available to admins - users listed in the `telegram.admins` property.

## Message limits

Heated discussions with the bot in large groups can lead to high usage of the AI API. To avoid spending your entire budget, set message limits for groups with the `conversation.message_limit` config property.

You can limit the number of messages from a user over a period of time. For example:

- 10 messages per user per hour:

```yaml
message_limit:
    count: 10
    period: hour
```

- 1 message per user per minute:

```yaml
message_limit:
    count: 1
    period: minute
```

- 30 messages per user per day:

```yaml
message_limit:
    count: 30
    period: day
```

## Setup

1. Get your AI API key (from [OpenAI](https://platform.openai.com/), [Claude](https://platform.claude.com/), [Gemini](https://aistudio.google.com/) or other provider)

2. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)

3. Clone the repo to the server:

```bash
git clone https://github.com/nalgeon/pokitoki.git
```

4. Copy `config.example.yml` to `config.yml` and specify your tokens there. Add yourself to the `telegram.usernames` property, otherwise the bot will be available to everyone.

5. Start the bot:

```bash
docker compose up --build --detach
```

To stop the bot:

```bash
docker compose stop
```

To update the bot to a new version:

```bash
docker compose down
git pull
docker compose up --build --detach
```

## Development setup

Install [uv](https://docs.astral.sh/uv/) and prepare the environment:

```
uv sync
```

Prepare the config and data directory:

```
cp config.example.yml config.yml
mkdir ./data
```

Set tokens and other settings in `config.yml`.

Run tests:

```
make test
```

Run linter:

```
make lint
```

Start the bot:

```
uv run python -m bot.bot
```

## Contributing

This project only accepts bug fixes.

Use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting (`uv run ruff check --fix . && uv run ruff format .`). Be sure to add or update tests as appropriate.

## Changelog

For feature history, see [releases](https://github.com/nalgeon/pokitoki/releases).

## Credits

Originally based on [chatgpt_telegram_bot](https://github.com/karfly/chatgpt_telegram_bot), although the projects have diverged quite a bit.
