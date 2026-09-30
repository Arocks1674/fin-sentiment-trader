"""SQLite storage.

Tables:
  articles         - one row per unique article (primary key = SHA-1 of URL)
  article_tickers  - which stocks each article is about (many-to-many)
  prices           - one row per (ticker, trading day)
  sentiment        - one FinBERT score per article per model

Why article_tickers exists: one story can mention two companies. Keying the
article on its URL alone meant the second company's copy was dropped as a
duplicate (seen in the first real run: 100 fetched, 90 stored). The article
is still stored once, but it is linked to every stock it was found for.
"""
import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id           TEXT PRIMARY KEY,      -- sha1 of the article URL
    ticker       TEXT NOT NULL,         -- first stock it was found for (kept for compatibility)
    title        TEXT NOT NULL,
    description  TEXT,
    content      TEXT,
    source       TEXT,
    url          TEXT NOT NULL,
    published_at TEXT NOT NULL,         -- ISO-8601 UTC
    fetched_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS article_tickers (
    article_id TEXT NOT NULL REFERENCES articles(id),
    ticker     TEXT NOT NULL,
    PRIMARY KEY (article_id, ticker)
);
CREATE INDEX IF NOT EXISTS idx_article_tickers_ticker ON article_tickers (ticker);

CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,               -- YYYY-MM-DD (exchange trading day)
    open   REAL, high REAL, low REAL, close REAL NOT NULL, volume INTEGER,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS sentiment (
    article_id TEXT NOT NULL REFERENCES articles(id),
    model      TEXT NOT NULL,
    positive   REAL NOT NULL,
    negative   REAL NOT NULL,
    neutral    REAL NOT NULL,
    label      TEXT NOT NULL,            -- argmax of the three probabilities
    score      REAL NOT NULL,            -- positive - negative, in [-1, 1]
    scored_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (article_id, model)
);

-- Module 2.1: sentiment about ONE company, from only the sentences that mention it.
CREATE TABLE IF NOT EXISTS entity_sentiment (
    article_id  TEXT NOT NULL REFERENCES articles(id),
    ticker      TEXT NOT NULL,
    model       TEXT NOT NULL,
    reason      TEXT NOT NULL,           -- ok | not_mentioned | source_only
    n_sentences INTEGER NOT NULL,
    sentences   TEXT,                    -- the sentences that were scored, joined by ' || '
    positive REAL, negative REAL, neutral REAL,   -- NULL when reason != ok
    label    TEXT,
    score    REAL,
    scored_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (article_id, ticker, model)
);
"""

# Backfill links for databases created by module 1 (before article_tickers existed).
MIGRATION = """
INSERT OR IGNORE INTO article_tickers (article_id, ticker)
SELECT id, ticker FROM articles;
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
        conn.executescript(MIGRATION)


def upsert_articles(db_path: Path, ticker: str, articles: list[dict]) -> int:
    """Store articles once and link each to `ticker`.

    Returns the number of NEW (article, ticker) links, so an article already
    stored for another stock still counts as new for this one.
    """
    valid = [a for a in articles if a.get("url") and a.get("title") and a.get("published_at")]
    art_rows = [(article_id(a["url"]), ticker, a["title"], a.get("description"), a.get("content"),
                 a.get("source"), a["url"], a["published_at"]) for a in valid]
    link_rows = [(r[0], ticker) for r in art_rows]
    with connect(db_path) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO articles "
            "(id, ticker, title, description, content, source, url, published_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", art_rows)
        before = conn.total_changes
        conn.executemany("INSERT OR IGNORE INTO article_tickers (article_id, ticker) VALUES (?, ?)",
                         link_rows)
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
    """One row per (article, ticker) link; `ticker` column is the linked stock."""
    q = ("SELECT a.id, t.ticker, a.title, a.description, a.content, a.source, a.url, "
         "a.published_at, a.fetched_at FROM articles a JOIN article_tickers t ON t.article_id = a.id")
    params: tuple = ()
    if ticker:
        q, params = q + " WHERE t.ticker = ?", (ticker,)
    with connect(db_path) as conn:
        return pd.read_sql_query(q + " ORDER BY a.published_at", conn, params=params)


def load_prices(db_path: Path, ticker: str | None = None) -> pd.DataFrame:
    q, params = "SELECT * FROM prices", ()
    if ticker:
        q, params = q + " WHERE ticker = ?", (ticker,)
    with connect(db_path) as conn:
        return pd.read_sql_query(q + " ORDER BY ticker, date", conn, params=params)


# --- sentiment ---------------------------------------------------------------

def unscored_articles(db_path: Path, model: str) -> pd.DataFrame:
    q = ("SELECT a.id, a.title, a.description FROM articles a "
         "LEFT JOIN sentiment s ON s.article_id = a.id AND s.model = ? "
         "WHERE s.article_id IS NULL ORDER BY a.published_at")
    with connect(db_path) as conn:
        return pd.read_sql_query(q, conn, params=(model,))


def save_sentiment(db_path: Path, model: str, rows: list[dict]) -> int:
    """rows: dicts with article_id, positive, negative, neutral, label, score."""
    data = [(r["article_id"], model, r["positive"], r["negative"], r["neutral"], r["label"], r["score"])
            for r in rows]
    with connect(db_path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO sentiment "
            "(article_id, model, positive, negative, neutral, label, score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", data)
    return len(data)


def load_scored_articles(db_path: Path, model: str, ticker: str | None = None) -> pd.DataFrame:
    """Articles joined with their links and scores: one row per (article, ticker)."""
    q = ("SELECT t.ticker, a.id, a.title, a.source, a.url, a.published_at, "
         "s.positive, s.negative, s.neutral, s.label, s.score "
         "FROM articles a JOIN article_tickers t ON t.article_id = a.id "
         "JOIN sentiment s ON s.article_id = a.id AND s.model = ?")
    params: tuple = (model,)
    if ticker:
        q, params = q + " WHERE t.ticker = ?", (model, ticker)
    with connect(db_path) as conn:
        return pd.read_sql_query(q + " ORDER BY a.published_at", conn, params=params)


# --- entity sentiment (module 2.1) ---------------------------------------------

def unscored_pairs(db_path: Path, model: str) -> pd.DataFrame:
    """(article, ticker) links that have no entity score for this model yet."""
    q = ("SELECT a.id AS article_id, t.ticker, a.title, a.description "
         "FROM articles a JOIN article_tickers t ON t.article_id = a.id "
         "LEFT JOIN entity_sentiment e ON e.article_id = a.id AND e.ticker = t.ticker AND e.model = ? "
         "WHERE e.article_id IS NULL ORDER BY a.published_at")
    with connect(db_path) as conn:
        return pd.read_sql_query(q, conn, params=(model,))


def save_entity_sentiment(db_path: Path, model: str, rows: list[dict]) -> int:
    """rows: article_id, ticker, reason, sentences (list), and for reason == 'ok' the score fields."""
    data = [(r["article_id"], r["ticker"], model, r["reason"], len(r["sentences"]),
             " || ".join(r["sentences"]) or None,
             r.get("positive"), r.get("negative"), r.get("neutral"), r.get("label"), r.get("score"))
            for r in rows]
    with connect(db_path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO entity_sentiment (article_id, ticker, model, reason, n_sentences, "
            "sentences, positive, negative, neutral, label, score) VALUES (?,?,?,?,?,?,?,?,?,?,?)", data)
    return len(data)


def load_entity_scored(db_path: Path, model: str, ticker: str | None = None,
                       relevant_only: bool = True) -> pd.DataFrame:
    q = ("SELECT e.ticker, a.id, a.title, a.source, a.url, a.published_at, e.reason, e.n_sentences, "
         "e.sentences, e.positive, e.negative, e.neutral, e.label, e.score "
         "FROM entity_sentiment e JOIN articles a ON a.id = e.article_id WHERE e.model = ?")
    params: list = [model]
    if relevant_only:
        q += " AND e.reason = 'ok'"
    if ticker:
        q += " AND e.ticker = ?"
        params.append(ticker)
    with connect(db_path) as conn:
        return pd.read_sql_query(q + " ORDER BY a.published_at", conn, params=tuple(params))
