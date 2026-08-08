"""
ingestion/base_connector.py
=============================
Common interface for historical news API connectors (GDELT, NewsAPI, ...).
Each connector wraps one external API and normalizes its response into
models.news_schema.Article objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from models.news_schema import Article


class BaseNewsConnector(ABC):
    """
    Every connector must implement `fetch_articles`. Connectors are async
    (httpx.AsyncClient) so ingestion_runner.py can fetch from multiple
    sources concurrently with asyncio.gather().
    """

    #: Short, stable identifier used in cache keys and logs (e.g. "gdelt").
    name: str = "base"

    @abstractmethod
    async def fetch_articles(
        self,
        query: str,
        start_date: datetime | date,
        end_date: datetime | date,
        **kwargs,
    ) -> list[Article]:
        """
        Fetch and normalize articles matching `query` published between
        `start_date` and `end_date` (inclusive). Implementations should
        raise on unrecoverable errors and let tenacity retry transient
        ones (429/5xx) — see gdelt_connector.py / newsapi_connector.py
        for the retry decorator pattern.
        """
        raise NotImplementedError

    async def aclose(self) -> None:
        """Override if the connector owns a client that needs closing."""
        return None