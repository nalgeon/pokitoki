# Pokitoki

Pokitoki is a Telegram AI assistant bot that talks to any OpenAI-compatible chat completions API (OpenAI, OpenRouter, Nebius, Gemini) over raw `httpx`, without the `openai` SDK. Python 3.13, python-telegram-bot 22.x. User-facing features are documented in README.md.

## Commands

Dependencies are managed with uv (`pyproject.toml` + `uv.lock`); `uv sync` creates `.venv/`.

```sh
uv run python -m unittest discover                           # all tests (also: make test)
uv run python -m unittest tests.test_askers                  # one module
uv run python -m unittest tests.test_askers.TextAskerTest.test_ask   # one test
uv run ruff check . && uv run ruff format --check .          # lint (also: make lint)
uv run python -m bot.bot                                     # run the bot (needs config.yml)
uv run python -m bot.cli "question"                          # one-off question to the AI from the CLI
make start name=foo / make stop name=foo                     # run with config.foo.yml in background
docker compose up --build --detach                           # production deploy
```

Lint and format with Ruff (default rules, line length 100, configured in `pyproject.toml`). CI (`.github/workflows/build.yml`) runs the linter, copies `config.example.yml` to `config.yml` and runs the unittest suite.

## Architecture

**Config is a module-level singleton loaded at import time.** `bot/config.py` reads `$CONFIG` (default `config.yml`) when it is imported, and the same goes for any module that imports `bot.config`. So **tests and every `bot.*` import need a `config.yml` in the working directory** (copy `config.example.yml`). On load, `SchemaMigrator` upgrades old configs and rewrites the file. If you change the config shape, bump `Config.schema_version` and add a `_migrate_vN` step. `ConfigEditor` backs the `/config` command, which edits values by dotted path (`ai.model`) at runtime and saves them back to disk. Properties are grouped as `readonly`, `immediate` or `delayed` (applied after a restart). `Config.version` is the bot version, which gets bumped in standalone `build: version N` commits.

**Request flow:**

1. `bot/bot.py` registers handlers. Access control uses `bot/filters.py` (`Filters`, built from `telegram.usernames`, `chat_ids` and `admins`; `Filters.reload()` is called after `/config` changes).
2. Every command is a callable class in `bot/commands/`, exported under a short alias in `commands/__init__.py`. Commands that produce an AI answer (`Message`, `Retry`, `Imagine`) take the `reply_to` function from `bot.py` as a dependency.
3. `bot/questions.py` turns a Telegram message into a question string. The rules differ for private chats and groups (in groups: mention, reply to the bot, topic replies). Text documents are inlined as fenced code. A leading `+` marks a follow-up, `!name` applies a shortcut (`bot/shortcuts.py`), and a leading `/cmd` is stripped.
4. `reply_to` (wrapped by `with_message_limit`) builds the history. In private chats it uses the per-user deque, which is cleared unless the message is a follow-up. In groups it only uses the replied-to bot message. URLs are inlined with `bot/fetcher.py` (quoted URLs are skipped).
5. `bot/askers.py`: `askers.create()` returns a `TextAsker` or an `ImagineAsker`. The `Asker` does `ask()` (AI call) and then `reply()`, which renders Markdown as Telegram HTML via `bot/markdown.py`. If the answer exceeds Telegram's length limit, it is sent as an `.md` attachment instead.

**AI layer (`bot/ai/chat.py`).** It POSTs to `{ai.url}/chat/completions` with just the model and messages (no sampling params like `temperature` or `max_tokens`, since many modern models reject them). The `MODELS` dict holds context window sizes of current OpenAI and Gemini models that support Chat Completions. Unknown models fall back to `ai.window`. Adding a new model means adding an entry there. History is trimmed by `shorten()` using a rough token estimate of words × 1.2, leaving `N_OUTPUT` tokens of the window for the answer.

**State.** Per-chat and per-user data persist through `PicklePersistence` (`persistence_path`, default `./data/persistence.pkl`). `bot/models.py` wraps the raw `context.chat_data` and `context.user_data` dicts:

- `ChatData`: per-chat `prompt` and `model` overrides.
- `UserData`: message history and an `ExpiringCounter` for rate limiting.

**Tests** use `unittest.IsolatedAsyncioTestCase` with hand-written fakes in `tests/mocks.py` (`FakeBot`, `FakeApplication`, `FakeGPT`, `FakeDalle`). `mock_text_asker()` monkeypatches `TextAsker.__init__` to inject a fake model. Tests also change the global `config` directly (e.g. `config.telegram.usernames = [...]`).

## Conventions

Commit messages are prefixed with the area: `ai: ...`, `commands: ...`, `config: ...`, `markdown: ...`, `docker: ...`, `build: ...`, `doc: ...`.

Never add `Co-Authored-By` or any other attribution lines to commit messages.
