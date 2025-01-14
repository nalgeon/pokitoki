import json
import re
import urllib.parse

import aiohttp
import httpx
from bs4 import BeautifulSoup
from httpx import HTTPStatusError, RequestError

from bot.config import config

# todo make scrape.do and httpx output similar

class Fetcher:
    """Retrieves remote content over HTTP."""

    # Matches non-quoted URLs in text
    url_re = re.compile(r"(?:[^'\"]|^)\b(https?://\S+)\b(?:[^'\"]|$)")
    timeout = 5  # seconds (you can increase if needed)

    def __init__(self):
        """
        By default, we use an httpx.AsyncClient with browser-like headers.
        If the server returns 403, or we face network issues,
        we'll attempt to use Scrap.do as a fallback (if a token is provided).
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/108.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers=headers
        )

    async def substitute_urls(self, text: str) -> str:
        """
        Extracts URLs from the given text, fetches their contents,
        and appends the content to the text in a separated block.
        """
        urls = self._extract_urls(text)
        for url in urls:
            content_str = await self._fetch_url(url)
            text += f"\n\n---\n{url} contents:\n\n{content_str}\n---"
        return text

    async def close(self) -> None:
        """Closes the underlying httpx client."""
        await self.client.aclose()

    def _extract_urls(self, text: str) -> list[str]:
        """Finds all URLs in the text by regex."""
        return self.url_re.findall(text)

    async def _fetch_url(self, url: str) -> str:
        """
        1) Try loading the page via httpx (self.client).
        2) If we get 403 Forbidden, or certain network errors (timeout, etc.),
           and we have a valid Scrap.do token, try Scrap.do as fallback.
        3) Otherwise, re-raise the exception.
        """
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return Content(response).extract_text()

        except HTTPStatusError as exc:
            # If it's a 403, let's try fallback
            if exc.response.status_code == 403:
                token = config.scrapdo.token
                if token and token.strip():
                    return await self._fetch_via_scrapdo(url, token)
            # Not a 403 or no token -> re-raise
            raise

        except (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError, httpx.TooManyRedirects) as net_exc:
            # If we face typical network issues, fallback to Scrap.do if token is set
            token = config.scrapdo.token
            if token and token.strip():
                return await self._fetch_via_scrapdo(url, token)
            else:
                raise net_exc

        except RequestError as req_err:
            # A generic request error, could be anything
            # Try fallback if token is available
            token = config.scrapdo.token
            if token and token.strip():
                return await self._fetch_via_scrapdo(url, token)
            else:
                raise req_err

    async def _fetch_via_scrapdo(self, url: str, token: str) -> str:
        """
        Makes a request to Scrap.do (https://scrape.do/docs):
          GET http://api.scrape.do?token=<token>&url=<encoded_url>
        Returns the extracted text or the raw HTML.
        """
        encoded_url = urllib.parse.quote(url, safe="")
        base_api = "http://api.scrape.do"
        params = f"token={token}&url={encoded_url}"
        full_url = f"{base_api}?{params}"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                    full_url,
                    timeout=self.timeout,
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
                        "Accept-Encoding": "gzip, deflate",
                    }
            ) as resp:
                if resp.status == 401:
                    raise ValueError("Invalid Scrap.do token")
                if resp.status == 429:
                    raise ValueError("Scrap.do rate limit exceeded")

                resp.raise_for_status()

                html_text = await resp.text(encoding="utf-8")
                fake_resp = FakeHttpxResponse(html_text, resp.headers)
                return Content(fake_resp).extract_text()


class FakeHttpxResponse:
    """
    Minimalistic mock object to emulate some of the httpx.Response interface
    that our Content class depends on.
    """

    def __init__(self, text: str, headers):
        self._text = text
        self.headers = headers

    @property
    def text(self) -> str:
        return self._text


class Content:
    """Extracts resource content as human-readable text."""

    allowed_content_types = {
        "application/json",
        "application/sql",
        "application/xml",
    }

    def __init__(self, response):
        # Expecting response.headers to be a dict-like
        content_type = response.headers.get("content-type", "")
        content_type, _, _ = content_type.partition(";")
        self.content_type = content_type.strip().lower()
        self.response = response

    def extract_text(self) -> str:
        """
        If the response is not text/html, return its text as is.
        Otherwise, parse the HTML with BeautifulSoup and extract text from
        <main> or <body>.
        """
        if not self.is_text():
            return "Unknown binary content"

        if self.content_type != "text/html":
            return self.response.text

        html = BeautifulSoup(self.response.text, "html.parser")

        json_scripts = html.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                # Ищем articleBody в JSON
                if 'articleBody' in data:
                    return data['articleBody']
            except (json.JSONDecodeError, AttributeError):
                continue

        content = (
                html.find("main") or
                html.find("article") or
                html.find("div", class_="content") or
                html.find("div", class_="article") or
                html.find("div", {"id": "content"}) or
                html.find("div", {"id": "main"}) or
                html.find("body")
        )

        if content:
            for tag in content.find_all(['script', 'style', 'nav', 'header', 'footer']):
                if tag.get('type') != 'application/ld+json':
                    tag.decompose()

            text = content.get_text(separator='\n', strip=True)

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines)

        text = html.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)

    def is_text(self) -> bool:
        if not self.content_type:
            return False
        if self.content_type.startswith("text/"):
            return True
        return self.content_type in self.allowed_content_types
