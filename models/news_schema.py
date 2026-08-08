"""
models/news_schema.py
======================
Normalized article schema shared by every ingestion connector
(RSS, GDELT, NewsAPI, ...). This is the schema new connectors should
produce; `to_legacy_dict()` adapts it to the flat dict shape that
`ingestion/news_fetcher.py` and `preprocessing/preprocess.py` already
expect (id, source, title, summary, link, published, fetched_at), so
the existing pipeline keeps working unchanged.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


def make_article_id(title: str, url: str) -> str:
    """
    Stable unique ID based on title + URL. Matches the convention already
    used in ingestion/news_fetcher.py's _make_id(), so IDs generated here
    dedupe correctly against RSS-sourced articles already in raw_news.json.
    """
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()


class Article(BaseModel):
    id: str
    title: str
    text: str = ""
    url: str
    published_at: datetime | None = None
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "text", "url", "source", mode="before")
    @classmethod
    def _blank_to_empty_str(cls, v: Any) -> str:
        return (v or "").strip() if isinstance(v, str) else (v or "")

    @classmethod
    def from_raw(
        cls,
        *,
        title: str,
        url: str,
        source: str,
        text: str = "",
        published_at: datetime | str | None = None,
        article_id: str | None = None,
        **metadata: Any,
    ) -> "Article":
        """
        Convenience constructor for connectors: builds a stable id from
        title+url if one isn't already known, and tolerates a raw ISO
        string for published_at.
        """
        if isinstance(published_at, str) and published_at:
            try:
                published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError:
                published_at = None
        elif published_at == "":
            published_at = None

        return cls(
            id=article_id or make_article_id(title, url),
            title=title,
            text=text,
            url=url,
            published_at=published_at,
            source=source,
            metadata=metadata,
        )

    def to_legacy_dict(self) -> dict:
        """
        Adapter for the existing pipeline. Keep this in sync if
        ingestion/news_fetcher.py's raw_news.json shape ever changes.
        """
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "summary": self.text,
            "link": self.url,
            "published": self.published_at.isoformat() if self.published_at else "",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }