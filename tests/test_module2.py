"""Tests for module 2 (no model download needed). Run: python -m pytest -q"""
import sqlite3

import pandas as pd
import pytest

from src.sentiment.aggregate import daily_sentiment
from src.sentiment.finbert import article_text, to_record
from src.storage import db

MODEL = "test-model"


def art(url, when="2026-09-01T04:00:00Z", title="T"):
    return {"title": title, "description": "D", "url": url, "published_at": when}


@pytest.fixture
def tmp_db(tmp_path):
    p = tmp_path / "t.db"
    db.init_db(p)
    return p


def test_same_article_is_linked_to_every_stock(tmp_db):
    # The module 1 bug: a story about two banks was stored for only the first one.
    assert db.upsert_articles(tmp_db, "HDFCBANK.NS", [art("u1")]) == 1
    assert db.upsert_articles(tmp_db, "ICICIBANK.NS", [art("u1")]) == 1
    assert db.upsert_articles(tmp_db, "ICICIBANK.NS", [art("u1")]) == 0
    links = db.load_articles(tmp_db)
    assert sorted(links.ticker) == ["HDFCBANK.NS", "ICICIBANK.NS"]
    with db.connect(tmp_db) as c:
        assert c.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1


def test_migration_backfills_module1_database(tmp_path):
    p = tmp_path / "old.db"
    with sqlite3.connect(p) as c:  # a module-1 style DB with no link table
        c.execute("CREATE TABLE articles (id TEXT PRIMARY KEY, ticker TEXT NOT NULL, title TEXT NOT NULL, "
                  "description TEXT, content TEXT, source TEXT, url TEXT NOT NULL, published_at TEXT NOT NULL, "
                  "fetched_at TEXT NOT NULL DEFAULT (datetime('now')))")
        c.execute("INSERT INTO articles (id, ticker, title, url, published_at) VALUES ('a','INFY.NS','t','u','2026-09-01')")
    db.init_db(p)
    assert list(db.load_articles(p).ticker) == ["INFY.NS"]


def test_unscored_then_scored(tmp_db):
    db.upsert_articles(tmp_db, "INFY.NS", [art("u1"), art("u2")])
    todo = db.unscored_articles(tmp_db, MODEL)
    assert len(todo) == 2
    db.save_sentiment(tmp_db, MODEL, [{"article_id": todo.id[0], **to_record(0.8, 0.1, 0.1)}])
    assert len(db.unscored_articles(tmp_db, MODEL)) == 1
    assert len(db.unscored_articles(tmp_db, "other-model")) == 2   # scores are per model


def test_to_record():
    r = to_record(0.7, 0.2, 0.1)
    assert r["label"] == "positive" and r["score"] == pytest.approx(0.5)


def test_article_text_skips_duplicate_description():
    assert article_text("Infosys wins deal", "infosys wins deal") == "Infosys wins deal"
    assert article_text("Infosys wins deal", "Worth $1bn") == "Infosys wins deal. Worth $1bn"


def test_daily_sentiment_groups_by_india_date():
    scored = pd.DataFrame([
        # 20:00 UTC on 1 Sep is 01:30 IST on 2 Sep -> must land on 2 Sep
        {"ticker": "TCS.NS", "published_at": "2026-09-01T20:00:00Z", "score": 0.6, "label": "positive"},
        {"ticker": "TCS.NS", "published_at": "2026-09-02T05:00:00Z", "score": -0.2, "label": "negative"},
        {"ticker": "TCS.NS", "published_at": "2026-09-01T05:00:00Z", "score": 0.0, "label": "neutral"},
    ])
    out = daily_sentiment(scored, dedupe=False)
    assert list(out.date_ist) == ["2026-09-01", "2026-09-02"]
    sep2 = out[out.date_ist == "2026-09-02"].iloc[0]
    assert sep2.n_articles == 2 and sep2.mean_score == pytest.approx(0.2)
    assert sep2.pos_share == 0.5 and sep2.neg_share == 0.5
