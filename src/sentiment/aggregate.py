"""Roll article scores up to one sentiment value per stock per day.

Dates are converted from UTC to India time (IST, UTC+5:30) before grouping,
because an article published at 20:00 UTC is already the next morning in
India. Module 3 goes one step further and maps each article to the next
*tradable* session (after 15:30 IST -> next trading day) to avoid lookahead.

Syndicated copies (same story, different URL) are collapsed first so one
story is not counted three times.
"""
import pandas as pd

from src.sentiment.entities import normalize_title

IST = "Asia/Kolkata"


def add_ist_date(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date_ist"] = (pd.to_datetime(df["published_at"], utc=True)
                      .dt.tz_convert(IST).dt.strftime("%Y-%m-%d"))
    return df


def drop_syndicated(scored: pd.DataFrame) -> pd.DataFrame:
    """Keep the earliest copy of each (ticker, IST date, normalized title)."""
    if scored.empty:
        return scored
    df = add_ist_date(scored)
    df["_norm"] = df["title"].map(normalize_title)
    df = df.sort_values("published_at").drop_duplicates(["ticker", "date_ist", "_norm"], keep="first")
    return df.drop(columns="_norm")


def daily_sentiment(scored: pd.DataFrame, dedupe: bool = True) -> pd.DataFrame:
    """scored: rows with ticker, published_at, score, label (and title if dedupe).

    Returns one row per (ticker, date_ist) with:
      n_articles, mean_score, pos_share, neg_share
    """
    cols = ["ticker", "date_ist", "n_articles", "mean_score", "pos_share", "neg_share"]
    if scored.empty:
        return pd.DataFrame(columns=cols)

    df = drop_syndicated(scored) if dedupe else add_ist_date(scored)
    g = df.groupby(["ticker", "date_ist"])
    out = pd.DataFrame({
        "n_articles": g.size(),
        "mean_score": g["score"].mean(),
        "pos_share": g["label"].apply(lambda s: (s == "positive").mean()),
        "neg_share": g["label"].apply(lambda s: (s == "negative").mean()),
    }).reset_index()
    return out[cols].sort_values(["ticker", "date_ist"]).reset_index(drop=True)
