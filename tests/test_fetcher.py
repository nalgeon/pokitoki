import unittest
from httpx import Request, Response

from bot.fetcher import Fetcher, Content


class FakeClient:
    def __init__(self, responses: dict[str, Response]) -> None:
        self.responses = responses

    async def get(self, url: str) -> Response:
        request = Request(method="GET", url=url)
        template = self.responses[url]
        return Response(
            status_code=template.status_code,
            headers=template.headers,
            text=template.text,
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

    async def test_nothing_to_substitute(self):
        text = "How are you?"
        text = await self.fetcher.substitute_urls(text)
        self.assertEqual(text, "How are you?")


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
