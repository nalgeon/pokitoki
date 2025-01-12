import logging
import re
import aiohttp
import httpx
import urllib.parse

from bs4 import BeautifulSoup
from httpx import HTTPStatusError

from bot.config import config

logger = logging.getLogger(__name__)


class Fetcher:
    """Retrieves remote content over HTTP."""

    # Шаблон для поиска URL'ов в тексте
    url_re = re.compile(r"(?:[^'\"]|^)\b(https?://\S+)\b(?:[^'\"]|$)")
    timeout = 3  # seconds

    def __init__(self):
        # Браузероподобные заголовки
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
        # Клиент для обычных запросов
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers=headers
        )

    async def substitute_urls(self, text: str) -> str:
        """
        Находит все URL в тексте, для каждого URL получает HTML
        и добавляет блок:
            ---
            <url> contents:

            <полученный текст>
            ---
        """
        urls = self._extract_urls(text)
        for url in urls:
            content = await self._fetch_url(url)
            text += f"\n\n---\n{url} contents:\n\n{content}\n---"
        return text

    async def close(self) -> None:
        """
        Закрываем httpx-клиент (освобождаем соединения).
        """
        await self.client.aclose()

    def _extract_urls(self, text: str) -> list[str]:
        """Находит все URL в тексте по регулярному выражению."""
        return self.url_re.findall(text)

    async def _fetch_url(self, url: str) -> str:
        """
        1) Пробуем загрузить страницу через httpx (self.client).
        2) Если получаем 403, а в конфиге есть token Scrap.do,
           пробуем GET через Scrap.do.
        3) Если всё проваливается — пробрасываем исключение.
        """
        try:
            logger.debug(f"Trying to fetch URL with httpx: {url}")
            response = await self.client.get(url)
            logger.warning(f"got response {response}")
            response.raise_for_status()

            content = Content(response)
            extr = content.extract_text()
            logger.warning(f"extract text: {extr}")
            return extr

        except HTTPStatusError as exc:
            logger.warning(f"Got HTTP error {exc.response.status_code} for {url}")

            if exc.response.status_code == 403:
                token = config.scrapdo.token
                logger.debug(f"Scrap.do token present? {bool(token and token.strip())}")

                # Если токен не пустой
                if token and token.strip():
                    logger.info(f"Falling back to Scrap.do for URL: {url}")
                    return await self._fetch_via_scrapdo(url, token)

            # Если не 403 или нет токена — просто пробрасываем ошибку
            raise

        except Exception as e:
            logger.error(f"Unexpected error while fetching {url}: {str(e)}")
            raise

    async def _fetch_via_scrapdo(self, url: str, token: str) -> str:
        """
        Делает запрос к Scrap.do (https://scrape.do/docs).
        """
        encoded_url = urllib.parse.quote(url)
        api_url = "http://api.scrape.do"
        params = {
            "token": token,
            "url": encoded_url,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{api_url}?{query_string}"

        logger.debug(f"Scrap.do request: {full_url}")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    full_url,
                    timeout=self.timeout,
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
                        "Accept-Encoding": "gzip, deflate"
                    }
                ) as resp:
                    logger.warning(f"Scrap.do response status: {resp.status}")
                    logger.warning(f"Scrap.do response headers: {resp.headers}")

                    if resp.status == 401:
                        logger.error("Scrap.do authentication failed - invalid token")
                        raise ValueError("Invalid Scrap.do token")

                    if resp.status == 429:
                        logger.error("Scrap.do rate limit exceeded")
                        raise ValueError("Scrap.do rate limit exceeded")

                    resp.raise_for_status()

                    # aiohttp автоматически декодирует gzip
                    html_text = await resp.text(encoding='utf-8')

                    logger.warning(f"Received HTML content length: {len(html_text)}")
                    if len(html_text) < 100:  # Если контент подозрительно короткий
                        logger.warning(f"Unusually short response: {html_text}")

                    # Дополнительно логируем информацию от scrape.do
                    remaining_credits = resp.headers.get("Scrape.do-Remaining-Credits")
                    request_cost = resp.headers.get("Scrape.do-Request-Cost")
                    if remaining_credits and request_cost:
                        logger.debug(f"Remaining credits: {remaining_credits}, Request cost: {request_cost}")

                    # Проверяем, что получили HTML
                    if not html_text or "<!DOCTYPE html>" not in html_text.lower():
                        logger.warning("Response doesn't look like HTML")
                        if html_text:
                            logger.warning(f"Response preview: {html_text[:200]}")

                    fake_resp = FakeHttpxResponse(html_text, resp.headers)
                    content = Content(fake_resp)
                    extracted_text = content.extract_text()

                    # Проверяем результат
                    if not extracted_text or extracted_text == "No <main> or <body> found.":
                        logger.warning("Failed to extract text from HTML")
                        # Возможно, стоит вернуть весь HTML если не удалось извлечь текст
                        return html_text
                    logger.warning(f"extracted_text: {extracted_text}")
                    return extracted_text

            except aiohttp.ClientError as e:
                logger.error(f"Network error with Scrap.do: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error with Scrap.do: {str(e)}")
                raise


class FakeHttpxResponse:
    """
    Минималистичная «заглушка», чтобы эмулировать некоторые поля httpx.Response
    """

    def __init__(self, text: str, headers):
        self._text = text  # уже получили текст через await resp.text()
        self.headers = headers

    @property  # Важно! В httpx это свойство, а не метод
    def text(self) -> str:
        return self._text


class Content:
    """
    Извлекает ресурс как человекочитаемый текст.
    Рассчитан на объект, схожий с httpx.Response:
      - response.text
      - response.headers
    """

    allowed_content_types = {
        "application/json",
        "application/sql",
        "application/xml",
    }

    def __init__(self, response):
        self.response = response
        # в httpx.Response заголовки — это словарь
        content_type = response.headers.get("content-type", "")
        content_type, _, _ = content_type.partition(";")
        self.content_type = content_type.strip().lower()

    def extract_text(self) -> str:
        """
        Если контент не text/html,
        просто возвращаем .text
        Иначе — парсим через BeautifulSoup и пытаемся найти контент
        в разных возможных местах.
        """
        if not self.is_text():
            return "Unknown binary content"

        if self.content_type != "text/html":
            return self.response.text

        # Парсим HTML
        html = BeautifulSoup(self.response.text, "html.parser")

        # Пробуем разные селекторы, от специфичных к общим
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
            # Удаляем ненужные элементы
            for tag in content.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()

            # Получаем текст с сохранением структуры
            text = content.get_text(separator='\n', strip=True)

            # Убираем лишние пустые строки
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines)

        # Если совсем ничего не нашли - берем весь текст
        text = html.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)

    def is_text(self) -> bool:
        """
        Проверяем, является ли контент «текстовым».
        """
        if not self.content_type:
            return False

        if self.content_type.startswith("text/"):
            return True

        return self.content_type in self.allowed_content_types