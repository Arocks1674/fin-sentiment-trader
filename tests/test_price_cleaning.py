"""Bad Yahoo ticks found in the real data must be removed before backtesting."""
import pandas as pd

from src.ingest.prices import clean_prices


def rows(ticker, closes, start="2004-04-22", volume=1000):
    dates = pd.bdate_range(start, periods=len(closes)).strftime("%Y-%m-%d")
    return [{"ticker": ticker, "date": d, "open": c, "high": c, "low": c, "close": c, "volume": volume}
            for d, c in zip(dates, closes)]


def test_unadjusted_bonus_day_spike_is_removed():
    # Real pattern (Kotak, Apr 2004): 3.88 -> 18.69 (+381%) -> 3.70 (-80%)
    df = pd.DataFrame(rows("KOTAKBANK.NS", [3.9, 3.88, 18.69, 3.70, 3.75]))
    clean, removed = clean_prices(df)
    assert removed["reason"].tolist() == ["bad_tick"] and removed["close"].iloc[0] == 18.69
    assert clean["close"].pct_change().abs().max() < 0.05


def test_real_crash_that_does_not_reverse_is_kept():
    df = pd.DataFrame(rows("AXISBANK.NS", [420, 383, 307, 300, 310]))   # Mar 2020: -20%, no reversal
    clean, removed = clean_prices(df)
    assert removed.empty and len(clean) == 5


def test_before_listing_and_zero_volume_removed():
    df = pd.DataFrame(rows("TCS.NS", [10, 11, 12, 13, 14], start="2004-08-20") + rows("INFY.NS", [50, 50], volume=0))
    clean, removed = clean_prices(df)
    assert set(removed["reason"]) == {"before_listing", "zero_volume"}
    assert clean["date"].min() >= "2004-08-25" and "INFY.NS" not in set(clean["ticker"])
