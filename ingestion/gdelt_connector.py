"""
ingestion/gdelt_connector.py
==============================
Connector for the GDELT DOC 2.0 API (https://api.gdeltproject.org/api/v2/doc/doc).
No API key required, but GDELT rate-limits aggressively — retries with backoff
on 429/5xx via tenacity, and caches raw responses in Redis via cache/api_cache.py.

Note: GDELT's DOC API returns article *metadata* (title, url, domain, tone,
seen-date) — not full article body text. `Article.text` will be empty unless
you separately fetch/scrape the URL; that's a GDELT limitation, not a bug here.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

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

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


def _fmt_gdelt_dt(dt: datetime | date) -> str:
    """GDELT wants STARTDATETIME/ENDDATETIME as YYYYMMDDHHMMSS (UTC)."""
    if isinstance(dt, datetime):
        return dt.strftime("%Y%m%d%H%M%S")
    return datetime(dt.year, dt.month, dt.day).strftime("%Y%m%d%H%M%S")


class GDELTConnector(BaseNewsConnector):
    name = "gdelt"

    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 20.0):
        # Accepts an injected client for testing; owns one otherwise.
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
        resp = await client.get(GDELT_DOC_URL, params=params)
        resp.raise_for_status()
        # GDELT sometimes returns HTML/empty body on transient hiccups
        # instead of a proper 5xx — treat unparsable JSON as retryable too.
        try:
            return resp.json()
        except ValueError as e:
            raise httpx.TransportError(f"GDELT returned non-JSON response: {e}") from e

    async def fetch_articles(
        self,
        query: str,
        start_date: datetime | date,
        end_date: datetime | date,
        max_records: int = 250,
        min_tone: float | None = None,
        max_tone: float | None = None,
        sort: str = "DateDesc",
        use_cache: bool = True,
        **kwargs,
    ) -> list[Article]:
        gdelt_query = query
        if min_tone is not None:
            gdelt_query += f" tone>{min_tone}"
        if max_tone is not None:
            gdelt_query += f" tone<{max_tone}"

        start_str = _fmt_gdelt_dt(start_date)
        end_str = _fmt_gdelt_dt(end_date)
        cache_extra = f"max={max_records}|sort={sort}|tone={min_tone},{max_tone}"

        if use_cache:
            cached = get_cached_response(self.name, query, start_str, end_str, cache_extra)
            if cached is not None:
                return [Article(**a) for a in cached]

        params = {
            "query": gdelt_query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": min(max(max_records, 1), 250),
            "startdatetime": start_str,
            "enddatetime": end_str,
            "sort": sort,
        }

        data = await self._request(params)
        raw_articles = data.get("articles", []) or []

        articles = [
            Article.from_raw(
                title=a.get("title", ""),
                url=a.get("url", ""),
                source=a.get("domain", "GDELT"),
                text="",  # DOC API returns metadata only, not body text
                published_at=a.get("seendate"),
                language=a.get("language"),
                source_country=a.get("sourcecountry"),
                social_image=a.get("socialimage"),
                connector="gdelt",
            )
            for a in raw_articles
            if a.get("title") and a.get("url")
        ]

        if use_cache:
            set_cached_response(
                self.name, query, start_str, end_str,
                [a.model_dump(mode="json") for a in articles], cache_extra,
            )

        return articles