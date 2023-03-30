"""Bot configuration parameters."""

import yaml

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

# Bot version.
version = 76

# Telegram Bot API token.
telegram_token = config["telegram_token"]

# The list of Telegram usernames allowed to chat with the bot.
# If empty, the bot will be available to anyone.
telegram_usernames = set(config["telegram_usernames"])

# The list of Telegram group ids, whose members are allowed to chat with the bot.
# If empty, the bot will only be available to `telegram_usernames`.
telegram_chat_ids = config.get("telegram_chat_ids", [])

# OpenAI API key.
openai_api_key = config["openai_api_key"]

# OpenAI model name. One of the following:
# gpt-3.5-turbo, gpt-4
openai_model = config.get("openai_model", "gpt-3.5-turbo")

# The maximum number of previous messages
# the bot will remember when talking to a user.
max_history_depth = config.get("max_history_depth", 3)

# Where to store the chat context file.
persistence_path = config["persistence_path"]

# Shortcuts
shortcuts = config.get("shortcuts", {})
