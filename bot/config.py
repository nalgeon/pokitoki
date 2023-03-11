"""Bot configuration parameters."""

import yaml

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

# Telegram Bot API token.
telegram_token = config["telegram_token"]

# OpenAI API key.
openai_api_key = config["openai_api_key"]

# The list of Telegram usernames allowed to chat with the bot.
telegram_usernames = config["telegram_usernames"]

# Where to store the chat context file.
persistence_path = config["persistence_path"]
