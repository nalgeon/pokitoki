### v130 - 2023-04-10

-   Allow changing `telegram.usernames` and `telegram.chat_ids` on the fly.
-   Allow `/config` only for admins in private chats.

### v129 - 2023-04-10

-   On-the-fly [configuration](https://github.com/nalgeon/pokitoki#configuration) ([#4](https://github.com/nalgeon/pokitoki/issues/4)).

### v125 - 2023-04-09

-   OpenAI `prompt` and `params` config properties.
-   Allow `/imagine` and `/reply` commands in groups.
-   Concurrent updates from Telegram.

### v116 - 2023-04-08

-   Relaxed image size parsing ([#13](https://github.com/nalgeon/pokitoki/issues/13)).
-   Allow shortcuts without prompt.
-   Show shortcuts in help.
-   Changed config file access mode from read-only to read-write.
-   Nested config properties.

### v104 - 2023-04-06

-   Count question length in tokens instead of characters ([#12](https://github.com/nalgeon/pokitoki/issues/12)).
-   Truncate questions that exceed the maximum number of tokens allowed by ChatGPT.

### v99 - 2023-04-06

-   [Image generation](https://github.com/nalgeon/pokitoki#image-generation) via DALL-E ([#13](https://github.com/nalgeon/pokitoki/issues/13)).

### v93 - 2023-04-04

-   Switched back to HTML parse mode instead of Markdown, but with code formatting.

### v86 - 2023-04-02

-   Switched to Markdown parse mode instead of HTML.

### v83 - 2023-04-01

-   Access [external links](https://github.com/nalgeon/pokitoki#external-links).

### v76 - 2023-03-31

-   Send large answers as [documents](https://github.com/nalgeon/pokitoki#reply-with-attachment).

### v70 - 2023-03-30

-   Custom [AI shortcuts](https://github.com/nalgeon/pokitoki#shortcuts).

### v68 - 2023-03-29

-   GPT-4 support and `openai_model` config property.
-   Support for fine-tuned models (CLI only).
-   Switched from HTTP/2 to HTTP/1.1 to mitigate LocalProtocolError.

### v61 - 2023-03-18

-   Handle [forwarded messages](https://github.com/nalgeon/pokitoki#forwarding) in private chats.
-   `max_history_depth` config property.

### v56 - 2023-03-16

-   Follow-up by reply.

### v46 - 2023-03-15

-   The [version](https://github.com/nalgeon/pokitoki#bot-information) command.

### c29d380 - 2023-03-13

-   Answer in [groups](https://github.com/nalgeon/pokitoki#groups).

### f2c5962 - 2023-03-11

-   Switched from GPT-3 to GPT-3.5.
-   Remember up to 3 previous questions.
-   Async calls to OpenAI.

### 704ad28 - 2023-02-01

Initial release:

-   Uses the GPT-3 (davinci) model, as GPT-3.5 is currently unavailable.
-   Basic chat functionality with limited context (last question only).
