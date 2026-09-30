"""Roll article scores up to one sentiment value per stock per day.

Dates are converted from UTC to India time (IST, UTC+5:30) before grouping,
because an article published at 20:00 UTC is already the next morning in
India. Module 3 goes one step further and maps each article to the next
*tradable* session (after 15:30 IST -> next trading day) to avoid lookahead.
"""
import pandas as pd

IST = "Asia/Kolkata"


def daily_sentiment(scored: pd.DataFrame) -> pd.DataFrame:
    """scored: rows from db.load_scored_articles.

    Returns one row per (ticker, date_ist) with:
      n_articles, mean_score, pos_share, neg_share
    """
    cols = ["ticker", "date_ist", "n_articles", "mean_score", "pos_share", "neg_share"]
    if scored.empty:
        return pd.DataFrame(columns=cols)

    df = scored.copy()
    df["date_ist"] = (pd.to_datetime(df["published_at"], utc=True)
                      .dt.tz_convert(IST).dt.strftime("%Y-%m-%d"))
    g = df.groupby(["ticker", "date_ist"])
    out = pd.DataFrame({
        "n_articles": g.size(),
        "mean_score": g["score"].mean(),
        "pos_share": g["label"].apply(lambda s: (s == "positive").mean()),
        "neg_share": g["label"].apply(lambda s: (s == "negative").mean()),
    }).reset_index()
    return out[cols].sort_values(["ticker", "date_ist"]).reset_index(drop=True)
