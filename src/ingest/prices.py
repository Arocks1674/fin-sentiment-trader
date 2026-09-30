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


# First real trading day on NSE. Yahoo returns earlier rows for some stocks that are not real prices.
LISTING_DATES = {"TCS.NS": "2004-08-25"}


def clean_prices(prices: pd.DataFrame, spike: float = 0.30, reversal_band: float = 0.15) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove bad rows from Yahoo daily data. Returns (clean, removed-with-reason).

    Rules:
      - before_listing: rows before the stock's NSE listing date
      - zero_volume:    days with no trading (holidays Yahoo filled with the previous price)
      - bad_tick:       a one-day jump of more than `spike` that is undone the next day
                        (the two-day move nets to within +-reversal_band). This is what an
                        unadjusted split/bonus day looks like, e.g. Kotak +381% then -80%.
    """
    df = prices.sort_values(["ticker", "date"]).reset_index(drop=True)
    reason = pd.Series("", index=df.index)

    listing = df["ticker"].map(LISTING_DATES)
    reason[listing.notna() & (df["date"] < listing)] = "before_listing"
    reason[(reason == "") & (df["volume"] == 0)] = "zero_volume"

    keep = df[reason == ""]
    r = keep.groupby("ticker")["close"].pct_change()
    r_next = keep.groupby("ticker")["close"].pct_change().groupby(keep["ticker"]).shift(-1)
    two_day = (1 + r) * (1 + r_next) - 1
    bad = (r.abs() > spike) & (two_day.abs() < reversal_band)
    reason[bad[bad].index] = "bad_tick"

    removed = df[reason != ""].assign(reason=reason[reason != ""])
    return df[reason == ""].reset_index(drop=True), removed
