import yaml

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

telegram_token = config["telegram_token"]
openai_api_key = config["openai_api_key"]
telegram_usernames = config["telegram_usernames"]
persistence_path = config["persistence_path"]
