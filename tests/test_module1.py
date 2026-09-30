"""Tests for module 1. Run with:  python -m pytest -q"""
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.ingest.news import NewsAPIError, fetch_gnews
from src.storage import db

ARTICLE = {"title": "Reliance Q2 profit rises", "description": "d", "content": "c",
           "source": "ET", "url": "https://x.com/a1", "published_at": "2026-09-01T10:00:00Z"}


@pytest.fixture
def tmp_db(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    return path


def test_articles_are_deduplicated_by_url(tmp_db):
    assert db.upsert_articles(tmp_db, "RELIANCE.NS", [ARTICLE]) == 1
    assert db.upsert_articles(tmp_db, "RELIANCE.NS", [ARTICLE]) == 0
    assert len(db.load_articles(tmp_db)) == 1


def test_articles_missing_required_fields_are_skipped(tmp_db):
    bad = dict(ARTICLE, url=None)
    assert db.upsert_articles(tmp_db, "RELIANCE.NS", [bad]) == 0


def test_prices_upsert_overwrites_same_day(tmp_db):
    df = pd.DataFrame([{"date": "2026-09-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10}])
    db.upsert_prices(tmp_db, "INFY.NS", df)
    db.upsert_prices(tmp_db, "INFY.NS", df.assign(close=9.9))
    out = db.load_prices(tmp_db, "INFY.NS")
    assert len(out) == 1 and out.close.iloc[0] == 9.9


def test_gnews_requires_key():
    with pytest.raises(NewsAPIError):
        fetch_gnews("Infosys", api_key="")


def test_gnews_normalizes_response():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"articles": [{"title": " T ", "description": "D", "content": "C",
                                            "source": {"name": "Mint"}, "url": "u",
                                            "publishedAt": "2026-09-01T00:00:00Z"}]}
    session = MagicMock(); session.get.return_value = resp
    out = fetch_gnews("Infosys", "key", session=session)
    assert out == [{"title": "T", "description": "D", "content": "C", "source": "Mint",
                    "url": "u", "published_at": "2026-09-01T00:00:00Z"}]
