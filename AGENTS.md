# Pokitoki

Pokitoki is a text-only Telegram AI assistant bot that talks to the OpenAI Responses, Claude Messages, Gemini and any OpenAI-compatible Chat Completions APIs over raw `httpx`, without the vendor SDKs. Python 3.13, python-telegram-bot 22.x. User-facing features are documented in README.md.

## Commands

Dependencies are managed with uv (`pyproject.toml` + `uv.lock`); `uv sync` creates `.venv/`.

```sh
uv run python -m unittest discover                           # all tests (also: make test)
uv run python -m unittest tests.test_ai                      # one module
uv run python -m unittest tests.test_ai.ShortenTest.test_do_not_shorten   # one test
uv run ruff check . && uv run ruff format --check .          # lint (also: make lint)
uv run python -m bot.bot                                     # run the bot (needs config.yml)
uv run python -m bot.cli "question"                          # one-off question to the AI from the CLI
make start name=foo / make stop name=foo                     # run with config.foo.yml in background
docker compose up --build --detach                           # production deploy
```

Lint and format with Ruff (default rules, line length 100, configured in `pyproject.toml`). CI (`.github/workflows/build.yml`) runs the linter, copies `config.example.yml` to `config.yml` and runs the unittest suite.

## Architecture

**Config is a module-level singleton loaded at import time.** `bot/config.py` reads `$CONFIG` (default `config.yml`) when it is imported, and the same goes for any module that imports `bot.config`. So **tests and every `bot.*` import need a `config.yml` in the working directory** (copy `config.example.yml`). On load, `SchemaMigrator` upgrades old configs and rewrites the file. If you change the config shape, bump `Config.schema_version` and add a `_migrate_vN` step. `ConfigEditor` backs the `/config` command, which edits values by dotted path (`ai.model`) at runtime and saves them back to disk. Properties are grouped as `readonly`, `immediate` or `delayed` (applied after a restart). `Config.version` is the bot version in calendar format (`yyyy.mm.dd`, or `yyyy.mm.dd.n` for a repeated release on the same day). It gets bumped in standalone `build: version yyyy.mm.dd` commits.

**Request flow:**

1. `bot/bot.py` registers handlers. Access control uses `bot/filters.py` (`Filters`, built from `telegram.usernames`, `chat_ids` and `admins`; `Filters.reload()` is called after `/config` changes).
2. Every command is a callable class in `bot/commands/`, exported under a short alias in `commands/__init__.py`. Commands that produce an AI answer (`Message`, `Retry`) take the `reply_to` function from `bot.py` as a dependency.
3. `bot/questions.py` turns a Telegram message into a question string. The rules differ for private chats and groups (in groups: mention, reply to the bot, topic replies). Text documents are inlined as fenced code. A leading `+` marks a follow-up, `!name` applies a shortcut (`bot/shortcuts.py`), and a leading `/cmd` is stripped.
4. `reply_to` (wrapped by `with_message_limit`) builds the history. In private chats it uses the per-user deque, which is cleared unless the message is a follow-up. In groups it only uses the replied-to bot message. Unless the model fetches URLs by itself (`ai.chat.can_fetch()`), URLs are inlined with `bot/fetcher.py` (quoted URLs are skipped).
5. `_ask_question` calls `ai.chat.ask()` with the chat's model (or `ai.model`), then `_send_answer` renders the Markdown answer as Telegram HTML via `bot/markdown.py` (parsed with `markdown-it-py`; formatting Telegram lacks, like headings, lists and tables, becomes plain text). If Telegram rejects the HTML, the answer is resent as plain text. If the answer exceeds Telegram's length limit, it is sent as a `.txt` attachment instead.

**AI layer (`bot/ai/`).** `chat.ask()` builds provider-neutral messages (system prompt first, then user/assistant pairs), trims them and passes them to the adapter selected by `ai.provider`. Each adapter has `complete(model, messages) -> str` and POSTs to `ai.base_url` (`ai.url` or the provider's default) via `api.post()`, which raises on HTTP errors:

- `openai.py`: Responses API (`/responses`, `store: false`). `web_search` tool only, no fetch tool.
- `claude.py`: Claude Messages API (`/messages`). Server-side `web_search`/`web_fetch` tools (basic versions for Haiku models), resumes `pause_turn` responses.
- `gemini.py`: `models/{model}:generateContent`. `google_search` and `url_context` tools.
- `compatible.py`: Chat Completions (`/chat/completions`), no tools, strips a leading `<think>` block.

`ai.tools` (`web_search`, `web_fetch`) enables the hosted tools. Adapters return only the answer text: thinking, tool calls and citations are dropped. Requests send no sampling params like `temperature`, since many modern models reject them. Claude and Gemini need the first message to be from the user, so `api.ensure_user_first()` adds a placeholder when the history starts with an answer. The `MODELS` dict in `chat.py` holds context window sizes of current OpenAI, Claude and Gemini models. Unknown models fall back to `ai.window`. Adding a new model means adding an entry there. History is trimmed by `shorten()` using a rough token estimate of words × 1.2, leaving `N_OUTPUT` tokens of the window for the answer. Tests fake the HTTP layer by replacing `api.client` with an `httpx.MockTransport` client.

**State.** Per-chat and per-user data live in SQLite (`db_path`, default `./data/pokitoki.db`), not in PTB persistence (`context.chat_data`/`user_data` are unused). `bot/db.py` holds a module-level connection (`db.init(path)` is called in `main()`; autocommit, WAL) and the schema. The models in `bot/models.py` read and write the tables directly on every access, so editing the database by hand takes effect immediately:

- `ChatData(chat_id)`: per-chat `prompt` and `model` overrides (`chats` table, empty = NULL).
- `UserData(user_id)`: message history (`messages` table, trimmed to `conversation.depth` rows per user) and an `ExpiringCounter` for rate limiting (`users` table).

The schema 8 config migration (`_migrate_v7`) sets `ai.provider` to `openai` for api.openai.com URLs and to `compatible` otherwise. The schema 7 config migration (`_migrate_v6`) imports chat overrides from the old PicklePersistence file (`persistence_path`) into a database with the same name (`state.pkl` → `state.db`) via `db.import_pickle()`, so bots with different pickle files in one directory don't share a database. Since config migrations run at import time, tests that migrate configs must stub `db.import_pickle`.

**Tests** use `unittest.IsolatedAsyncioTestCase` with hand-written fakes in `tests/mocks.py` (`FakeBot`, `FakeApplication` (which also resets `db` to a fresh in-memory database), `FakeGPT`). `mock_chat()` replaces `chat.ask` with a fake model. Tests also change the global `config` directly (e.g. `config.telegram.usernames = [...]`).

## Conventions

Commit messages are prefixed with the area: `ai: ...`, `commands: ...`, `config: ...`, `markdown: ...`, `docker: ...`, `build: ...`, `doc: ...`.

Never add `Co-Authored-By` or any other attribution lines to commit messages.
