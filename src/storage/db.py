"""SQLite storage for articles and daily prices.

Two tables:
  articles  - one row per unique news article (deduplicated by URL hash)
  prices    - one row per (ticker, trading day)
"""
import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id           TEXT PRIMARY KEY,      -- sha1 of the article URL
    ticker       TEXT NOT NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    content      TEXT,
    source       TEXT,
    url          TEXT NOT NULL,
    published_at TEXT NOT NULL,         -- ISO-8601 UTC
    fetched_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_articles_ticker_time ON articles (ticker, published_at);

CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,               -- YYYY-MM-DD (exchange trading day)
    open   REAL, high REAL, low REAL, close REAL NOT NULL, volume INTEGER,
    PRIMARY KEY (ticker, date)
);
"""


def article_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


@contextmanager
def connect(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def upsert_articles(db_path: Path, ticker: str, articles: list[dict]) -> int:
    """Insert new articles; skip ones already stored. Returns number of new rows."""
    rows = [
        (article_id(a["url"]), ticker, a["title"], a.get("description"), a.get("content"),
         a.get("source"), a["url"], a["published_at"])
        for a in articles if a.get("url") and a.get("title") and a.get("published_at")
    ]
    with connect(db_path) as conn:
        before = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO articles "
            "(id, ticker, title, description, content, source, url, published_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        return conn.total_changes - before


def upsert_prices(db_path: Path, ticker: str, df: pd.DataFrame) -> int:
    """Insert or update daily OHLCV rows. df needs columns: date, open, high, low, close, volume."""
    if df.empty:
        return 0
    rows = [(ticker, str(r.date), r.open, r.high, r.low, r.close, int(r.volume))
            for r in df.itertuples(index=False)]
    with connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO prices (ticker, date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(ticker, date) DO UPDATE SET open=excluded.open, high=excluded.high, "
            "low=excluded.low, close=excluded.close, volume=excluded.volume", rows)
    return len(rows)


def load_articles(db_path: Path, ticker: str | None = None) -> pd.DataFrame:
    q, params = "SELECT * FROM articles", ()
    if ticker:
        q, params = q + " WHERE ticker = ?", (ticker,)
    with connect(db_path) as conn:
        return pd.read_sql_query(q + " ORDER BY published_at", conn, params=params)


def load_prices(db_path: Path, ticker: str | None = None) -> pd.DataFrame:
    q, params = "SELECT * FROM prices", ()
    if ticker:
        q, params = q + " WHERE ticker = ?", (ticker,)
    with connect(db_path) as conn:
        return pd.read_sql_query(q + " ORDER BY ticker, date", conn, params=params)
