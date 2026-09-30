"""Daily OHLCV prices from Yahoo Finance via yfinance."""
import pandas as pd
import yfinance as yf


def fetch_prices(ticker: str, start: str, end: str | None = None) -> pd.DataFrame:
    """Return columns: date (YYYY-MM-DD), open, high, low, close, volume.

    Uses split/dividend-adjusted prices so returns are comparable over time.
    """
    raw = yf.download(ticker, start=start, end=end, auto_adjust=True,
                      progress=False, multi_level_index=False)
    if raw.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    df = raw.reset_index().rename(columns=str.lower)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
