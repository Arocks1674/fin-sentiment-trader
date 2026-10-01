"""Module 5: dashboard data shaping, charts, and an app smoke test."""
import numpy as np
import pandas as pd
import pytest

from src.app import views


def scored_rows():
    base = {"ticker": "INFY.NS", "label": "positive", "url": "u"}
    return pd.DataFrame([
        {**base, "published_at": "2026-09-28T04:00:00Z", "title": "Infosys wins deal", "score": 0.8,
         "sentences": "Infosys won a large deal."},
        # syndicated copy of the same story, different URL
        {**base, "published_at": "2026-09-28T06:00:00Z", "title": "Infosys wins deal - Mint", "score": 0.8,
         "sentences": "Infosys won a large deal."},
        {**base, "published_at": "2026-09-29T20:00:00Z", "title": "Infosys cuts guidance", "score": -0.7,
         "label": "negative", "sentences": "Infosys cut its guidance."},
        {**base, "ticker": "TCS.NS", "published_at": "2026-09-29T05:00:00Z", "title": "TCS news", "score": 0.1,
         "label": "neutral", "sentences": "TCS said something."},
    ])


def price_rows(tickers=("INFY.NS", "TCS.NS"), start="2026-08-01", n=60, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=n).strftime("%Y-%m-%d")
    rows = []
    for t in tickers:
        close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
        for d, c in zip(dates, close):
            rows.append({"ticker": t, "date": d, "open": c, "high": c, "low": c, "close": c, "volume": 1000})
    return pd.DataFrame(rows)


def test_recent_articles_dedupes_and_sorts_newest_first_in_ist():
    arts = views.recent_articles(scored_rows(), "INFY.NS")
    assert len(arts) == 2                                   # syndicated copy removed, TCS excluded
    assert arts["title"].iloc[0] == "Infosys cuts guidance"  # newest first
    # 20:00 UTC on 29 Sep is 01:30 IST on 30 Sep
    assert arts["published_at"].iloc[0] == "2026-09-30 01:30 IST"


def test_recent_articles_empty_for_unknown_stock():
    assert views.recent_articles(scored_rows(), "ITC.NS").empty


def test_stock_daily_window_and_tone():
    s, p = views.stock_daily(scored_rows(), price_rows(), "INFY.NS", days=30)
    assert p["date"].min() >= (pd.Timestamp(p["date"].max()) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    assert set(p.columns) == {"date", "close"}
    assert list(s["tone"]) == ["positive", "negative"]
    assert list(s["date"]) == ["2026-09-28", "2026-09-30"]  # IST dates


def test_stock_daily_without_news_returns_prices_only():
    s, p = views.stock_daily(scored_rows().iloc[0:0], price_rows(), "INFY.NS", days=30)
    assert s.empty and not p.empty


def test_charts_render_to_vega_spec():
    s, p = views.stock_daily(scored_rows(), price_rows(), "INFY.NS", days=30)
    dom = [p["date"].min(), p["date"].max()]
    for chart in (views.price_chart(p, dom), views.sentiment_chart(s, dom)):
        assert "$schema" in chart.to_dict()


def test_backtest_tables_shape():
    prices = price_rows(n=200)
    days = sorted(prices["date"].unique())[20:150:5]
    rng = np.random.default_rng(1)
    hist = pd.DataFrame({"ticker": "INFY.NS", "date": days, "score": rng.uniform(-1, 1, len(days)),
                         "price_report": False})
    long, curves = views.backtest_tables(hist, prices, hold=5)
    assert set(long["window"]) == {"5 days before", "5 days after"}
    assert set(long["news"].astype(str)) <= {"negative", "neutral", "positive"}
    assert set(curves["series"]) == {"News strategy", "Buy & hold (equal-weight)"}
    assert curves["growth"].gt(0).all()
    assert views.event_chart(long).to_dict() and views.equity_chart(curves).to_dict()


def test_app_runs_on_empty_database(tmp_path, monkeypatch):
    """Fresh clone, nothing ingested yet: every tab shows guidance instead of crashing."""
    from streamlit.testing.v1 import AppTest
    import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "empty.db")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not at.exception
    infos = " ".join(i.value for i in at.info)
    assert "ingest.py" in infos and "coverage.py" in infos
    assert any("GEMINI_API_KEY" in w.value for w in at.warning)
