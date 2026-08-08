"""
ingestion/newsapi_connector.py
=================================
Connector for NewsAPI.org's /v2/everything endpoint. Requires NEWS_API_KEY
in your .env (get one at https://newsapi.org/register).

Known free-tier ("Developer") limits as of 2026 — not a bug here, just the
provider's terms: 100 requests/day, results delayed ~24h, and historical
articles limited to roughly the last month. For real historical backfill
beyond that window, GDELTConnector (no such limit) is the better source.
"""

from __future__ import annotations

import os
from datetime import date, datetime

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from cache.api_cache import get_cached_response, set_cached_response
from ingestion.base_connector import BaseNewsConnector
from models.news_schema import Article

NEWSAPI_URL = "https://newsapi.org/v2/everything"
NEWSAPI_PAGE_SIZE_MAX = 100


class NewsAPIAuthError(RuntimeError):
    """Raised when NEWS_API_KEY is missing or rejected — not retryable."""


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


def _fmt_date(dt: datetime | date) -> str:
    """NewsAPI wants from/to as YYYY-MM-DD."""
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else str(dt)


class NewsAPIConnector(BaseNewsConnector):
    name = "newsapi"

    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None,
                 timeout: float = 20.0):
        self._api_key = api_key or os.getenv("NEWS_API_KEY")
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    async def _request(self, params: dict) -> dict:
        client = await self._get_client()
        resp = await client.get(NEWSAPI_URL, params=params)

        if resp.status_code in (401, 426):
            body = resp.json() if resp.content else {}
            raise NewsAPIAuthError(
                f"NewsAPI rejected the request ({resp.status_code}): "
                f"{body.get('message', 'check NEWS_API_KEY')}"
            )

        resp.raise_for_status()
        return resp.json()

    async def fetch_articles(
        self,
        query: str,
        start_date: datetime | date,
        end_date: datetime | date,
        sort_by: str = "publishedAt",
        page_size: int = 100,
        max_pages: int = 5,
        language: str | None = "en",
        use_cache: bool = True,
        **kwargs,
    ) -> list[Article]:
        if not self._api_key:
            raise NewsAPIAuthError(
                "NEWS_API_KEY is not set. Add it to your .env — get a free "
                "key at https://newsapi.org/register"
            )

        start_str = _fmt_date(start_date)
        end_str = _fmt_date(end_date)
        page_size = min(max(page_size, 1), NEWSAPI_PAGE_SIZE_MAX)
        cache_extra = f"sort={sort_by}|pages={max_pages}|lang={language}"

        if use_cache:
            cached = get_cached_response(self.name, query, start_str, end_str, cache_extra)
            if cached is not None:
                return [Article(**a) for a in cached]

        all_raw: list[dict] = []
        for page in range(1, max_pages + 1):
            params = {
                "q": query,
                "from": start_str,
                "to": end_str,
                "sortBy": sort_by,
                "pageSize": page_size,
                "page": page,
                "apiKey": self._api_key,
            }
            if language:
                params["language"] = language

            data = await self._request(params)
            page_articles = data.get("articles", []) or []
            all_raw.extend(page_articles)

            total_results = data.get("totalResults", 0)
            if len(all_raw) >= total_results or len(page_articles) < page_size:
                break  # no more pages

        articles = [
            Article.from_raw(
                title=a.get("title", ""),
                url=a.get("url", ""),
                source=(a.get("source") or {}).get("name", "NewsAPI"),
                text=a.get("content") or a.get("description") or "",
                published_at=a.get("publishedAt"),
                author=a.get("author"),
                description=a.get("description"),
                image_url=a.get("urlToImage"),
                connector="newsapi",
            )
            for a in all_raw
            if a.get("title") and a.get("url") and a.get("title") != "[Removed]"
        ]

        if use_cache:
            set_cached_response(
                self.name, query, start_str, end_str,
                [a.model_dump(mode="json") for a in articles], cache_extra,
            )

        return articles