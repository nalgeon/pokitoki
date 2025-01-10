"""Retrieves remote content over HTTP."""

import re
import httpx
from bs4 import BeautifulSoup


class Fetcher:
    """Retrieves remote content over HTTP."""

    # Matches non-quoted URLs in text
    url_re = re.compile(r"(?:[^'\"]|^)\b(https?://\S+)\b(?:[^'\"]|$)")
    timeout = 3  # seconds

    def __init__(self):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/108.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,"
                      "application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            # и т.д.
            }
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers=headers
            )

    async def substitute_urls(self, text: str) -> str:
        """
        Extracts URLs from text, fetches their contents,
        and appends the contents to the text.
        """
        urls = self._extract_urls(text)
        for url in urls:
            content = await self._fetch_url(url)
            text += f"\n\n---\n{url} contents:\n\n{content}\n---"
        return text

    async def close(self) -> None:
        """Frees network connections."""
        await self.client.aclose()

    def _extract_urls(self, text: str) -> list[str]:
        """Extracts URLs from text."""
        urls = self.url_re.findall(text)
        return urls

    async def _fetch_url(self, url: str) -> str:
        """Retrieves URL content and returns it as text."""
        response = await self.client.get(url)
        response.raise_for_status()
        content = Content(response)
        return content.extract_text()


class Content:
    """Extracts resource content as human-readable text."""

    allowed_content_types = set(
        [
            "application/json",
            "application/sql",
            "application/xml",
        ]
    )

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        content_type, _, _ = response.headers.get("content-type").partition(";")
        self.content_type = content_type

    def extract_text(self) -> str:
        """Extracts resource content as human-readable text."""
        if not self.is_text():
            return "Unknown binary content"
        if self.content_type != "text/html":
            return self.response.text
        html = BeautifulSoup(self.response.text, "html.parser")
        article = html.find("main") or html.find("body")
        return article.get_text()

    def is_text(self) -> bool:
        """Checks if the content type is plain text."""
        if not self.content_type:
            return False
        if self.content_type.startswith("text/"):
            return True
        if self.content_type in self.allowed_content_types:
            return True
        return False
