import json
import unittest

import httpx

from bot.ai import api, chat
from bot.config import config
from bot.models import UserMessage


class GenerateMessagesTest(unittest.TestCase):
    def test_generate_messages(self):
        history = [UserMessage("Hello", "Hi"), UserMessage("Is it cold today?", "Yep!")]
        messages = chat._generate_messages(prompt="", question="What's your name?", history=history)
        self.assertEqual(len(messages), 6)

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], config.ai.prompt)

        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Hello")

        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[2]["content"], "Hi")

        self.assertEqual(messages[3]["role"], "user")
        self.assertEqual(messages[3]["content"], "Is it cold today?")

        self.assertEqual(messages[4]["role"], "assistant")
        self.assertEqual(messages[4]["content"], "Yep!")

        self.assertEqual(messages[5]["role"], "user")
        self.assertEqual(messages[5]["content"], "What's your name?")

    def test_group_history(self):
        # in group chats, the history only has the previous answer
        history = [("", "It's cold.")]
        messages = chat._generate_messages(prompt="Be brief", question="Why?", history=history)
        self.assertEqual(
            messages,
            [
                {"role": "system", "content": "Be brief"},
                {"role": "assistant", "content": "It's cold."},
                {"role": "user", "content": "Why?"},
            ],
        )


class ShortenTest(unittest.TestCase):
    def test_do_not_shorten(self):
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "Hello"},
        ]
        shortened = chat.shorten(messages, length=11)
        self.assertEqual(shortened, messages)

    def test_remove_messages_1(self):
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "What is your name?"},
            {"role": "assistant", "content": "My name is Alice."},
            {"role": "user", "content": "Is it cold today?"},
        ]
        shortened = chat.shorten(messages, length=11)
        self.assertEqual(
            shortened,
            [
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "user", "content": "Is it cold today?"},
            ],
        )

    def test_remove_messages_2(self):
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "What is your name?"},
            {"role": "assistant", "content": "My name is Alice."},
            {"role": "user", "content": "Is it cold today?"},
        ]
        shortened = chat.shorten(messages, length=15)
        self.assertEqual(
            shortened,
            [
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "assistant", "content": "My name is Alice."},
                {"role": "user", "content": "Is it cold today?"},
            ],
        )

    def test_shorten_question(self):
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "Is it cold today? I think it's rather cold"},
        ]
        shortened = chat.shorten(messages, length=10)
        self.assertEqual(
            shortened,
            [
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "user", "content": "Is it cold today?"},
            ],
        )


class ProviderTest(unittest.IsolatedAsyncioTestCase):
    """Base class for provider tests with fake HTTP responses."""

    provider = ""

    def setUp(self) -> None:
        self.requests = []
        self.responses = []
        self.client = api.client
        api.client = httpx.AsyncClient(transport=httpx.MockTransport(self.handle))
        self.config = (config.ai.provider, config.ai.url, config.ai.tools)
        config.ai.provider = self.provider
        config.ai.url = ""
        config.ai.tools = ["web_search", "web_fetch"]

    def tearDown(self) -> None:
        api.client = self.client
        config.ai.provider, config.ai.url, config.ai.tools = self.config

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self.responses.pop(0)
        return httpx.Response(status, json=body)

    def body(self, idx: int = 0) -> dict:
        return json.loads(self.requests[idx].content)

    async def ask(self, model: str = "model") -> str:
        history = [("Hello", "Hi")]
        return await chat.ask(model, prompt="Be brief", question="What's up?", history=history)


class OpenAITest(ProviderTest):
    provider = "openai"

    async def test_ask(self):
        output = [
            {"type": "reasoning", "id": "rs_1", "summary": []},
            {"type": "web_search_call", "id": "ws_1", "status": "completed"},
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": "Not much. ", "annotations": []},
                    {"type": "output_text", "text": "You?", "annotations": []},
                ],
            },
        ]
        self.responses.append((200, {"status": "completed", "output": output, "usage": {}}))
        answer = await self.ask()
        self.assertEqual(answer, "Not much. You?")

        request = self.requests[0]
        self.assertEqual(str(request.url), "https://api.openai.com/v1/responses")
        self.assertEqual(request.headers["authorization"], f"Bearer {config.ai.api_key}")
        self.assertEqual(
            self.body(),
            {
                "model": "model",
                "instructions": "Be brief",
                "input": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                    {"role": "user", "content": "What's up?"},
                ],
                "store": False,
                "tools": [{"type": "web_search"}],
            },
        )

    async def test_no_tools(self):
        config.ai.tools = []
        output = [{"type": "message", "content": [{"type": "output_text", "text": "Hi"}]}]
        self.responses.append((200, {"status": "completed", "output": output}))
        await self.ask()
        self.assertNotIn("tools", self.body())

    async def test_incomplete(self):
        resp = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
        self.responses.append((200, {**resp, "output": []}))
        with self.assertRaisesRegex(RuntimeError, "max_output_tokens"):
            await self.ask()

    async def test_error(self):
        self.responses.append((400, {"error": {"message": "Invalid model"}}))
        with self.assertRaisesRegex(RuntimeError, "400 Invalid model"):
            await self.ask()


class ClaudeTest(ProviderTest):
    provider = "claude"

    async def test_ask(self):
        content = [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "server_tool_use", "id": "srvtoolu_1", "name": "web_search", "input": {}},
            {"type": "web_search_tool_result", "tool_use_id": "srvtoolu_1", "content": []},
            {"type": "text", "text": "Not much"},
            {"type": "text", "text": " (it's quiet).", "citations": [{"type": "x"}]},
        ]
        self.responses.append((200, {"content": content, "stop_reason": "end_turn", "usage": {}}))
        answer = await self.ask("claude-opus-5-5")
        self.assertEqual(answer, "Not much (it's quiet).")

        request = self.requests[0]
        self.assertEqual(str(request.url), "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.headers["x-api-key"], config.ai.api_key)
        self.assertEqual(request.headers["anthropic-version"], "2023-06-01")
        body = self.body()
        self.assertEqual(body["model"], "claude-opus-5-5")
        self.assertEqual(body["system"], "Be brief")
        self.assertEqual(
            body["messages"],
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "What's up?"},
            ],
        )
        self.assertEqual(
            [t["type"] for t in body["tools"]], ["web_search_20260209", "web_fetch_20260209"]
        )

    async def test_haiku_tools(self):
        content = [{"type": "text", "text": "Hi"}]
        self.responses.append((200, {"content": content, "stop_reason": "end_turn", "usage": {}}))
        await self.ask("claude-haiku-4-5")
        types = [t["type"] for t in self.body()["tools"]]
        self.assertEqual(types, ["web_search_20250305", "web_fetch_20250910"])

    async def test_pause_turn(self):
        paused = [
            {"type": "text", "text": "Let me check. "},
            {"type": "server_tool_use", "id": "srvtoolu_1", "name": "web_fetch", "input": {}},
        ]
        self.responses.append((200, {"content": paused, "stop_reason": "pause_turn", "usage": {}}))
        content = [{"type": "text", "text": "Done."}]
        self.responses.append((200, {"content": content, "stop_reason": "end_turn", "usage": {}}))
        answer = await self.ask()
        self.assertEqual(answer, "Let me check. Done.")
        messages = self.body(1)["messages"]
        self.assertEqual(messages[-1], {"role": "assistant", "content": paused})
        self.assertEqual(len(messages), 4)

    async def test_user_first(self):
        content = [{"type": "text", "text": "Because."}]
        self.responses.append((200, {"content": content, "stop_reason": "end_turn", "usage": {}}))
        await chat.ask("model", prompt="", question="Why?", history=[("", "It's cold.")])
        messages = self.body()["messages"]
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1], {"role": "assistant", "content": "It's cold."})

    async def test_refusal(self):
        self.responses.append((200, {"content": [], "stop_reason": "refusal", "usage": {}}))
        with self.assertRaisesRegex(RuntimeError, "refusal"):
            await self.ask()

    async def test_error(self):
        error = {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}
        self.responses.append((529, error))
        with self.assertRaisesRegex(RuntimeError, "529 Overloaded"):
            await self.ask()


class GeminiTest(ProviderTest):
    provider = "gemini"

    async def test_ask(self):
        parts = [
            {"text": "Thinking about it...", "thought": True},
            {"text": "Not much."},
        ]
        resp = {"candidates": [{"content": {"role": "model", "parts": parts}}]}
        self.responses.append((200, resp))
        answer = await self.ask("gemini-4-argon")
        self.assertEqual(answer, "Not much.")

        request = self.requests[0]
        self.assertEqual(
            str(request.url),
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-4-argon:generateContent",
        )
        self.assertEqual(request.headers["x-goog-api-key"], config.ai.api_key)
        self.assertEqual(
            self.body(),
            {
                "systemInstruction": {"parts": [{"text": "Be brief"}]},
                "contents": [
                    {"role": "user", "parts": [{"text": "Hello"}]},
                    {"role": "model", "parts": [{"text": "Hi"}]},
                    {"role": "user", "parts": [{"text": "What's up?"}]},
                ],
                "tools": [{"google_search": {}}, {"url_context": {}}],
            },
        )

    async def test_blocked(self):
        self.responses.append((200, {"promptFeedback": {"blockReason": "SAFETY"}}))
        with self.assertRaisesRegex(RuntimeError, "SAFETY"):
            await self.ask()


class CompatibleTest(ProviderTest):
    provider = "compatible"

    def setUp(self) -> None:
        super().setUp()
        config.ai.url = "https://openrouter.ai/api/v1"

    async def test_ask(self):
        answer = "<think>\nThe user greets me.\n</think>\n\nNot much."
        resp = {"choices": [{"message": {"role": "assistant", "content": answer}}], "usage": {}}
        self.responses.append((200, resp))
        self.assertEqual(await self.ask(), "Not much.")

        request = self.requests[0]
        self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(
            self.body(),
            {
                "model": "model",
                "messages": [
                    {"role": "system", "content": "Be brief"},
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                    {"role": "user", "content": "What's up?"},
                ],
            },
        )

    async def test_error_in_body(self):
        self.responses.append((200, {"error": {"message": "No credits", "code": 402}}))
        with self.assertRaisesRegex(RuntimeError, "No credits"):
            await self.ask()


class CanFetchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = (config.ai.provider, config.ai.tools)

    def tearDown(self) -> None:
        config.ai.provider, config.ai.tools = self.config

    def test_can_fetch(self):
        config.ai.tools = ["web_fetch"]
        for provider, expected in [
            ("openai", False),
            ("claude", True),
            ("gemini", True),
            ("compatible", False),
        ]:
            config.ai.provider = provider
            self.assertEqual(chat.can_fetch(), expected, provider)

    def test_no_tools(self):
        config.ai.tools = []
        config.ai.provider = "claude"
        self.assertFalse(chat.can_fetch())


class UnknownProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_unknown(self):
        provider = config.ai.provider
        config.ai.provider = "acme"
        self.addCleanup(setattr, config.ai, "provider", provider)
        with self.assertRaisesRegex(ValueError, "acme"):
            await chat.ask("model", prompt="", question="Hi", history=[])
