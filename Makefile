.PHONY: start stop test lint
.SILENT: start stop test lint

start:
	CONFIG=config.$(name).yml nohup uv run python -m bot.bot > $(name).log 2>&1 & echo $$! > $(name).pid
	echo "Started $(name) bot"

stop:
	kill $(shell cat $(name).pid)
	rm -f $(name).pid
	echo "Stopped $(name) bot"

test:
	uv run python -m unittest discover

lint:
	uv run ruff check .
	uv run ruff format --check .
