"""
Unit tests for the ingestion connectors. All HTTP calls are mocked —
no real network access, no API keys required to run these.

Run: uv run pytest tests/test_ingestion.py -v
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from ingestion.base_connector import BaseNewsConnector
from ingestion.gdelt_connector import GDELTConnector
from ingestion.newsapi_connector import NewsAPIAuthError, NewsAPIConnector
from models.news_schema import Article, make_article_id


def _json_response(status_code: int, payload: dict, url: str = "https://example.test") -> httpx.Response:
    """Builds a real httpx.Response with no network I/O — good enough for
    .raise_for_status() / .json() / .status_code to behave correctly."""
    request = httpx.Request("GET", url)
    return httpx.Response(status_code, json=payload, request=request)


# ── Article schema ──────────────────────────────────────────────────────────

def test_article_from_raw_generates_stable_id():
    a1 = Article.from_raw(title="Same Title", url="https://x.test/a", source="X")
    a2 = Article.from_raw(title="Same Title", url="https://x.test/a", source="X")
    assert a1.id == a2.id == make_article_id("Same Title", "https://x.test/a")


def test_article_from_raw_parses_iso_published_at():
    a = Article.from_raw(
        title="T", url="https://x.test/a", source="X",
        published_at="2026-08-05T09:03:20Z",
    )
    assert a.published_at == datetime(2026, 8, 5, 9, 3, 20, tzinfo=timezone.utc)


def test_article_from_raw_handles_missing_published_at():
    a = Article.from_raw(title="T", url="https://x.test/a", source="X", published_at="")
    assert a.published_at is None


def test_article_to_legacy_dict_matches_raw_news_json_shape():
    a = Article.from_raw(
        title="T", url="https://x.test/a", source="X", text="body",
        published_at="2026-08-05T09:03:20Z",
    )
    legacy = a.to_legacy_dict()
    assert set(legacy.keys()) == {"id", "source", "title", "summary", "link", "published", "fetched_at"}
    assert legacy["summary"] == "body"
    assert legacy["link"] == "https://x.test/a"


def test_base_connector_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseNewsConnector()  # abstract — fetch_articles not implemented


# ── GDELT connector ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gdelt_connector_parses_response(monkeypatch):
    # Disable Redis caching for this test so we exercise the real HTTP path.
    monkeypatch.setattr("ingestion.gdelt_connector.get_cached_response", lambda *a, **k: None)
    monkeypatch.setattr("ingestion.gdelt_connector.set_cached_response", lambda *a, **k: None)

    fake_payload = {
        "articles": [
            {
                "url": "https://ndtv.com/article-1",
                "title": "Parliament Monsoon Session Adjourned",
                "seendate": "20260805T090320Z",
                "domain": "ndtv.com",
                "language": "English",
                "sourcecountry": "India",
            },
            {"url": "", "title": "Missing URL, should be dropped"},  # invalid — filtered
        ]
    }

    connector = GDELTConnector(client=httpx.AsyncClient())
    connector._client.get = AsyncMock(return_value=_json_response(200, fake_payload))

    articles = await connector.fetch_articles(
        "parliament", datetime(2026, 8, 4), datetime(2026, 8, 6)
    )

    assert len(articles) == 1
    assert isinstance(articles[0], Article)
    assert articles[0].title == "Parliament Monsoon Session Adjourned"
    assert articles[0].source == "ndtv.com"
    assert articles[0].text == ""  # GDELT DOC API has no body text
    await connector.aclose()


@pytest.mark.asyncio
async def test_gdelt_connector_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("ingestion.gdelt_connector.get_cached_response", lambda *a, **k: None)
    monkeypatch.setattr("ingestion.gdelt_connector.set_cached_response", lambda *a, **k: None)

    connector = GDELTConnector(client=httpx.AsyncClient())
    connector._client.get = AsyncMock(side_effect=[
        _json_response(503, {}),                     # transient failure
        _json_response(200, {"articles": []}),        # then succeeds
    ])

    articles = await connector.fetch_articles(
        "test", datetime(2026, 8, 4), datetime(2026, 8, 6)
    )

    assert articles == []
    assert connector._client.get.call_count == 2  # confirms the retry happened
    await connector.aclose()


@pytest.mark.asyncio
async def test_gdelt_connector_uses_cache_on_hit(monkeypatch):
    cached_dump = [Article.from_raw(title="Cached", url="https://x.test/a", source="X").model_dump(mode="json")]
    monkeypatch.setattr("ingestion.gdelt_connector.get_cached_response", lambda *a, **k: cached_dump)

    connector = GDELTConnector(client=httpx.AsyncClient())
    connector._client.get = AsyncMock(side_effect=AssertionError("should not hit network on cache hit"))

    articles = await connector.fetch_articles("q", datetime(2026, 8, 4), datetime(2026, 8, 6))

    assert len(articles) == 1
    assert articles[0].title == "Cached"
    connector._client.get.assert_not_called()
    await connector.aclose()


# ── NewsAPI connector ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_newsapi_connector_requires_api_key(monkeypatch):
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    connector = NewsAPIConnector(api_key=None, client=httpx.AsyncClient())
    with pytest.raises(NewsAPIAuthError):
        await connector.fetch_articles("test", datetime(2026, 8, 4), datetime(2026, 8, 6))
    await connector.aclose()


@pytest.mark.asyncio
async def test_newsapi_connector_parses_response(monkeypatch):
    monkeypatch.setattr("ingestion.newsapi_connector.get_cached_response", lambda *a, **k: None)
    monkeypatch.setattr("ingestion.newsapi_connector.set_cached_response", lambda *a, **k: None)

    fake_payload = {
        "status": "ok",
        "totalResults": 1,
        "articles": [{
            "source": {"id": "ndtv", "name": "NDTV"},
            "author": "Jane Doe",
            "title": "Stocks Rise After Monsoon Session",
            "description": "Markets reacted positively.",
            "url": "https://ndtv.com/article-2",
            "urlToImage": "https://ndtv.com/img.jpg",
            "publishedAt": "2026-08-05T09:03:20Z",
            "content": "Full body text here...",
        }],
    }

    connector = NewsAPIConnector(api_key="test-key", client=httpx.AsyncClient())
    connector._client.get = AsyncMock(return_value=_json_response(200, fake_payload))

    articles = await connector.fetch_articles(
        "monsoon session", datetime(2026, 8, 4), datetime(2026, 8, 6)
    )

    assert len(articles) == 1
    assert articles[0].title == "Stocks Rise After Monsoon Session"
    assert articles[0].source == "NDTV"
    assert articles[0].metadata["author"] == "Jane Doe"
    await connector.aclose()


@pytest.mark.asyncio
async def test_newsapi_connector_stops_pagination_when_exhausted(monkeypatch):
    monkeypatch.setattr("ingestion.newsapi_connector.get_cached_response", lambda *a, **k: None)
    monkeypatch.setattr("ingestion.newsapi_connector.set_cached_response", lambda *a, **k: None)

    def _article(i):
        return {
            "source": {"name": "X"}, "author": None,
            "title": f"Article {i}", "description": "", "url": f"https://x.test/{i}",
            "urlToImage": None, "publishedAt": "2026-08-05T09:00:00Z", "content": "",
        }

    # totalResults=2, first page returns exactly 2 -> loop should stop after 1 call
    fake_payload = {"status": "ok", "totalResults": 2, "articles": [_article(1), _article(2)]}

    connector = NewsAPIConnector(api_key="test-key", client=httpx.AsyncClient())
    connector._client.get = AsyncMock(return_value=_json_response(200, fake_payload))

    articles = await connector.fetch_articles(
        "test", datetime(2026, 8, 4), datetime(2026, 8, 6), page_size=100, max_pages=5
    )

    assert len(articles) == 2
    assert connector._client.get.call_count == 1  # stopped once totalResults was met
    await connector.aclose()


@pytest.mark.asyncio
async def test_newsapi_connector_raises_on_bad_key(monkeypatch):
    monkeypatch.setattr("ingestion.newsapi_connector.get_cached_response", lambda *a, **k: None)

    connector = NewsAPIConnector(api_key="bad-key", client=httpx.AsyncClient())
    connector._client.get = AsyncMock(
        return_value=_json_response(401, {"status": "error", "message": "apiKey is invalid"})
    )

    with pytest.raises(NewsAPIAuthError):
        await connector.fetch_articles("test", datetime(2026, 8, 4), datetime(2026, 8, 6))
    await connector.aclose()