"""Historical headlines for the backtest: Times of India headlines archive.

Source: "News Headlines of India" (Rohit Kulkarni), Harvard Dataverse,
doi:10.7910/DVN/DPQMQH, CC0 public domain. One CSV with
publish_date (yyyymmdd), headline_category, headline_text.

Limits to keep in mind:
- Date only, no time of day. The backtest therefore trades a headline dated D
  at the NEXT session's open, which can never use information from the future.
- It is a general newspaper, so company-specific coverage may be thin. That is
  what `coverage.py` measures before any backtest is built.
"""
import logging
import re
from pathlib import Path

import pandas as pd
import requests

from src.sentiment.entities import ENTITIES, relevant_sentences

URL = ("https://dataverse.harvard.edu/api/access/datafile/:persistentId"
       "?persistentId=doi:10.7910/DVN/DPQMQH/P2Z4PM")
log = logging.getLogger(__name__)


def download(dest: Path, url: str = URL) -> Path:
    """Stream the CSV to `dest` (a few hundred MB). Skips if it already exists."""
    if dest.exists() and dest.stat().st_size > 0:
        log.info("Using existing %s (%.0f MB)", dest, dest.stat().st_size / 1e6)
        return dest
    tmp = dest.with_suffix(".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        done = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                done += len(chunk)
                if done % (50 << 20) < (1 << 20):
                    log.info("  downloaded %d MB", done >> 20)
    tmp.replace(dest)
    return dest


def _any_name_pattern() -> re.Pattern:
    """One cheap regex that matches ANY of our company names; used to pre-filter millions of rows."""
    words = set()
    for e in ENTITIES.values():
        words.update(e.names)
        words.update(e.acronyms)
    alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?i)(?<![\w&])(?:{alt})(?![\w&])")


def extract(csv_path: Path, tickers: list[str], business_only: bool = True,
            chunksize: int = 500_000) -> pd.DataFrame:
    """Return one row per (ticker, date, headline) that passes the entity rules.

    Columns: date (YYYY-MM-DD), ticker, headline, category, price_report (bool)
    """
    any_name = _any_name_pattern()
    out = []
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunksize, dtype=str,
                                          on_bad_lines="skip", encoding_errors="replace")):
        chunk = chunk.dropna(subset=["publish_date", "headline_text"])
        if business_only:
            chunk = chunk[chunk["headline_category"].fillna("").str.startswith("business")]
        chunk = chunk[chunk["headline_text"].str.contains(any_name)]
        for row in chunk.itertuples(index=False):
            for t in tickers:
                rel = relevant_sentences(t, row.headline_text, "")
                if rel.reason == "ok":
                    out.append((row.publish_date, t, row.headline_text.strip(),
                                row.headline_category, any(rel.price_report)))
        log.info("  chunk %d: %d matches so far", i + 1, len(out))

    df = pd.DataFrame(out, columns=["publish_date", "ticker", "headline", "category", "price_report"])
    df["date"] = pd.to_datetime(df.pop("publish_date"), format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
    return df.dropna(subset=["date"]).drop_duplicates(["ticker", "date", "headline"]).reset_index(drop=True)


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Headlines per stock per year, plus distinct days with news (what a daily signal needs)."""
    if df.empty:
        return pd.DataFrame()
    d = df.assign(year=df["date"].str[:4])
    heads = d.pivot_table(index="ticker", columns="year", values="headline", aggfunc="count", fill_value=0)
    days = d.groupby("ticker")["date"].nunique().rename("days_with_news")
    return heads.join(days)
