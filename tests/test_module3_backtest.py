"""Module 3: backtest timing and metrics on hand-made prices."""
import numpy as np
import pandas as pd
import pytest

from src.backtest import metrics
from src.backtest.engine import (Config, daily_signal, event_study, events, portfolio_returns,
                                 price_panels)

DATES = ["2015-01-01", "2015-01-02", "2015-01-05", "2015-01-06", "2015-01-07"]


def make_prices():
    rows = []
    # INFY: flat, then jumps on the CLOSE of 01-02 (the news day), then +10% on 01-05 open->close
    infy = [(100, 100), (100, 120), (120, 132), (132, 132), (132, 132)]
    tcs = [(100, 100)] * 5
    for d, (o, c) in zip(DATES, infy):
        rows.append({"ticker": "INFY.NS", "date": d, "open": o, "close": c})
    for d, (o, c) in zip(DATES, tcs):
        rows.append({"ticker": "TCS.NS", "date": d, "open": o, "close": c})
    return price_panels(pd.DataFrame(rows))


def test_news_is_traded_next_session_open_not_same_day():
    opens, closes = make_prices()
    sig = pd.DataFrame([{"ticker": "INFY.NS", "date": "2015-01-02", "score": 0.9, "n": 1}])
    ev = events(sig, opens, closes, hold=1)
    # Entry must be 01-05 (next session), capturing 120 -> 132 (+10%), NOT the 100 -> 120 jump on the news day.
    assert ev.entry.iloc[0] == "2015-01-05"
    assert ev.ret.iloc[0] == pytest.approx(0.10)
    # Market = average of INFY (+10%) and TCS (0%) = +5%, so abnormal = +5%.
    assert ev.abn_ret.iloc[0] == pytest.approx(0.05)


def test_weekend_news_enters_next_trading_day():
    opens, closes = make_prices()
    sig = pd.DataFrame([{"ticker": "INFY.NS", "date": "2015-01-03", "score": 0.9, "n": 1}])  # a Saturday
    assert events(sig, opens, closes, hold=1).entry.iloc[0] == "2015-01-05"


def test_multi_day_hold_and_costs():
    opens, closes = make_prices()
    sig = pd.DataFrame([{"ticker": "INFY.NS", "date": "2015-01-02", "score": 0.9, "n": 1}])
    ev = events(sig, opens, closes, hold=2)
    assert ev.exit.iloc[0] == "2015-01-06"
    r = portfolio_returns(ev, opens, closes, Config(hold=2, threshold=0.3, cost=0.01))
    assert r["2015-01-05"] == pytest.approx(0.10 - 0.01)       # entry day: open->close minus cost
    assert r["2015-01-06"] == pytest.approx(0.0)               # 132 -> 132
    assert r["2015-01-02"] == 0.0                              # not invested before entry


def test_below_threshold_is_not_traded():
    opens, closes = make_prices()
    sig = pd.DataFrame([{"ticker": "INFY.NS", "date": "2015-01-02", "score": 0.1, "n": 1}])
    ev = events(sig, opens, closes, hold=1)
    assert (portfolio_returns(ev, opens, closes, Config(threshold=0.3)) == 0).all()


def test_daily_signal_can_exclude_price_reports():
    scored = pd.DataFrame([
        {"ticker": "INFY.NS", "date": "2015-01-02", "score": 0.8, "price_report": 1},
        {"ticker": "INFY.NS", "date": "2015-01-02", "score": -0.2, "price_report": 0}])
    assert daily_signal(scored).score.iloc[0] == pytest.approx(0.3)
    assert daily_signal(scored, exclude_price_reports=True).score.iloc[0] == pytest.approx(-0.2)


def test_event_study_buckets():
    ev = pd.DataFrame({"score": [-0.9, -0.8, 0.0, 0.9, 0.8], "abn_ret": [-0.02, -0.01, 0.0, 0.01, 0.03]})
    out = event_study(ev, 0.3)
    assert out.loc["positive", "events"] == 2 and out.loc["positive", "mean_abn_ret_%"] == pytest.approx(2.0)


def test_metrics():
    r = pd.Series([0.1, -0.5, 0.2])
    assert metrics.max_drawdown(r) == pytest.approx(-0.5)
    assert np.isnan(metrics.sharpe(pd.Series([0.0, 0.0])))
