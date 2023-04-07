.PHONY: start stop test
.SILENT: start stop test

start:
	CONFIG=config.$(name).yml nohup env/bin/python -m bot.bot > $(name).log 2>&1 & echo $$! > $(name).pid
	echo "Started $(name) bot"

stop:
	kill $(shell cat $(name).pid)
	rm -f $(name).pid
	echo "Stopped $(name) bot"

test:
	env/bin/python -m unittest discover
