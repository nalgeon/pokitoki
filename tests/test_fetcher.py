import unittest
from httpx import Request, Response

from bot.fetcher import Fetcher, Content


class FakeClient:
    def __init__(self, responses: dict[str, Response | Exception]) -> None:
        self.responses = responses

    async def get(self, url: str) -> Response:
        request = Request(method="GET", url=url)
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return Response(
            status_code=response.status_code,
            headers=response.headers,
            text=response.text,
            request=request,
        )


class FetcherTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fetcher = Fetcher()

    async def test_substitute_urls(self):
        resp_1 = Response(status_code=200, headers={"content-type": "text/plain"}, text="first")
        resp_2 = Response(status_code=200, headers={"content-type": "text/plain"}, text="second")
        self.fetcher.client = FakeClient(
            {
                "https://example.org/first": resp_1,
                "https://example.org/second": resp_2,
            }
        )
        text = "Compare https://example.org/first and https://example.org/second"
        text = await self.fetcher.substitute_urls(text)
        self.assertEqual(
            text,
            """Compare https://example.org/first and https://example.org/second

---
https://example.org/first contents:

first
---

---
https://example.org/second contents:

second
---""",
        )

    async def test_fetch_url(self):
        resp = Response(status_code=200, headers={"content-type": "text/plain"}, text="hello")
        exc = ConnectionError("timeout")
        self.fetcher.client = FakeClient({"https://success.org": resp, "https://failure.org": exc})
        text = await self.fetcher._fetch_url("https://success.org")
        self.assertEqual(text, "hello")
        text = await self.fetcher._fetch_url("https://failure.org")
        self.assertEqual(text, "Failed to fetch (builtins.ConnectionError)")

    async def test_ignore_quoted(self):
        src = "What is 'https://example.org/first'?"
        text = await self.fetcher.substitute_urls(src)
        self.assertEqual(text, src)

    async def test_nothing_to_substitute(self):
        src = "How are you?"
        text = await self.fetcher.substitute_urls(src)
        self.assertEqual(text, src)

    def test_extract_urls(self):
        text = "Compare https://example.org/first and https://example.org/second"
        urls = self.fetcher._extract_urls(text)
        self.assertEqual(urls, ["https://example.org/first", "https://example.org/second"])

        text = "Extract https://example.org/first."
        urls = self.fetcher._extract_urls(text)
        self.assertEqual(urls, ["https://example.org/first"])

        text = 'Extract "https://example.org/first"'
        urls = self.fetcher._extract_urls(text)
        self.assertEqual(urls, [])


class ContentTest(unittest.TestCase):
    def test_extract_as_is(self):
        resp = Response(
            status_code=200, headers={"content-type": "application/sql"}, text="select 42;"
        )
        content = Content(resp)
        text = content.extract_text()
        self.assertEqual(text, "select 42;")

    def test_extract_html(self):
        html = "<html><head></head><body><main>hello</main></body></html>"
        resp = Response(status_code=200, headers={"content-type": "text/html"}, text=html)
        content = Content(resp)
        text = content.extract_text()
        self.assertEqual(text, "hello")

    def test_extract_unknown(self):
        resp = Response(status_code=200, headers={"content-type": "application/pdf"}, text="...")
        content = Content(resp)
        text = content.extract_text()
        self.assertEqual(text, "Unknown binary content")
