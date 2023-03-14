"""Bot configuration parameters."""

import yaml

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

# Telegram Bot API token.
telegram_token = config["telegram_token"]

# OpenAI API key.
openai_api_key = config["openai_api_key"]

# The list of Telegram usernames allowed to chat with the bot.
# If empty, the bot will be available to anyone.
telegram_usernames = set(config["telegram_usernames"])

# The list of Telegram group ids, whose members are allowed to chat with the bot.
# If empty, the bot will only be available to `telegram_usernames`.
telegram_chat_ids = config.get("telegram_chat_ids", [])

# Where to store the chat context file.
persistence_path = config["persistence_path"]
