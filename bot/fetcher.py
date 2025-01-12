import logging
import re
import aiohttp
import httpx
import json
from bs4 import BeautifulSoup
from httpx import HTTPStatusError

from bot.config import config

logger = logging.getLogger(__name__)


class Fetcher:
    """Retrieves remote content over HTTP."""

    url_re = re.compile(r"(?:[^'\"]|^)\b(https?://\S+)\b(?:[^'\"]|$)")
    timeout = 3

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
        }
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers=headers
        )

    async def substitute_urls(self, text: str) -> str:
        urls = self._extract_urls(text)
        for url in urls:
            content = await self._fetch_url(url)
            text += f"\n\n---\n{url} contents:\n\n{content}\n---"
        return text

    async def close(self) -> None:
        await self.client.aclose()

    def _extract_urls(self, text: str) -> list[str]:
        return self.url_re.findall(text)

    async def _fetch_url(self, url: str) -> str:
        """
        1. Пробуем httpx.
        2. Если 403 -> fallback на ScrapingBot (aiohttp).
        """
        try:
            logger.debug(f"Trying to fetch URL with httpx: {url}")
            response = await self.client.get(url)
            response.raise_for_status()
            content = Content(response)
            return content.extract_text()

        except HTTPStatusError as exc:
            logger.debug(f"Got HTTP error {exc.response.status_code} for {url}")

            if exc.response.status_code == 403:
                username = config.scrappingbot.username
                api_key = config.scrappingbot.api_key

                logger.warning(f"Checking ScrapingBot credentials: username={username}, api_key={api_key}")

                if username and username.strip() and api_key and api_key.strip():
                    logger.warning(f"Switching to ScrapingBot for URL: {url}")
                    return await self._fetch_via_scrapingbot(url, username, api_key)
                else:
                    logger.warning("ScrapingBot credentials not configured")

            logger.error(f"HTTP error {exc.response.status_code} for {url}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error while fetching {url}: {str(e)}")
            raise

    async def _fetch_via_scrapingbot(self, url: str, username: str, api_key: str) -> str:
        """
        Делаем асинхронный POST-запрос к ScrapingBot c помощью aiohttp.
        """
        api_url = "http://api.scraping-bot.io/scrape/raw-html"  # Вернули http как в документации
        payload = json.dumps({"url": url})  # Явно сериализуем в JSON строку

        headers = {
            "Content-Type": "application/json"
        }

        logger.debug(f"ScrapingBot request details:")
        logger.debug(f"URL: {api_url}")
        logger.debug(f"Auth username: {username[:4]}..." if username else "None")
        logger.debug(f"Auth key: {api_key[:4]}..." if api_key else "None")
        logger.debug(f"Payload: {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url, 
                    data=payload,  # Используем data вместо json, так как payload уже сериализован
                    auth=aiohttp.BasicAuth(username, api_key),
                    headers=headers,
                    timeout=self.timeout
                ) as resp:
                    if resp.status == 403:
                        error_text = await resp.text()
                        logger.error(f"ScrapingBot authentication error: {error_text}")
                        raise ValueError(f"ScrapingBot authentication failed: {error_text}")

                    resp.raise_for_status()
                    html_text = await resp.text()
                    logger.debug("Successfully got response from ScrapingBot")

            # Парсим HTML, отдаём text
            soup = BeautifulSoup(html_text, "html.parser")
            article = soup.find("main") or soup.find("body")
            return article.get_text() if article else html_text

        except aiohttp.ClientError as e:
            logger.error(f"Network error with ScrapingBot: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error with ScrapingBot: {str(e)}")
            raise


class Content:
    """Extracts resource content as human-readable text."""

    allowed_content_types = {
        "application/json",
        "application/sql",
        "application/xml",
    }

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        content_type, _, _ = response.headers.get("content-type", "").partition(";")
        self.content_type = content_type

    def extract_text(self) -> str:
        if not self.is_text():
            return "Unknown binary content"
        if self.content_type != "text/html":
            return self.response.text

        html = BeautifulSoup(self.response.text, "html.parser")
        article = html.find("main") or html.find("body")
        return article.get_text() if article else "No <main> or <body> found."

    def is_text(self) -> bool:
        if not self.content_type:
            return False
        if self.content_type.startswith("text/"):
            return True
        return self.content_type in self.allowed_content_types