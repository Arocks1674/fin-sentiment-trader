"""Data shaping and charts for the Streamlit dashboard (kept out of app.py so they can be tested).

Chart conventions (from the project's data-viz rules):
  - one y-axis per chart: price and sentiment are two stacked charts sharing the date axis
  - sentiment is diverging around zero: blue = positive, red = negative
  - every mark has a tooltip; series identity is never colour alone (legend + labels)
"""
import altair as alt
import pandas as pd

from src.backtest.engine import (Config, benchmark_returns, daily_signal, event_study, events,
                                 portfolio_returns, price_panels, trim_to_events)
from src.ingest.prices import clean_prices
from src.sentiment.aggregate import daily_sentiment, drop_syndicated

POS, NEG = "#2a78d6", "#e34948"            # diverging poles
SERIES = ["#2a78d6", "#eb6834"]            # categorical slots 1-2
MUTED = "#898781"


def recent_articles(scored: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Scored articles for one stock, newest first, syndicated copies removed."""
    arts = scored[scored["ticker"] == ticker]
    if arts.empty:
        return arts
    arts = drop_syndicated(arts).sort_values("published_at", ascending=False).copy()
    ist = pd.to_datetime(arts["published_at"], utc=True).dt.tz_convert("Asia/Kolkata")
    arts["published_at"] = ist.dt.strftime("%Y-%m-%d %H:%M IST")
    return arts


def stock_daily(scored: pd.DataFrame, prices: pd.DataFrame, ticker: str, days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Last `days` of daily sentiment and closing prices for one stock."""
    s = daily_sentiment(scored[scored["ticker"] == ticker]) if not scored.empty else pd.DataFrame()
    p = prices[prices["ticker"] == ticker][["date", "close"]].copy()
    if p.empty:
        return s, p
    start = (pd.Timestamp(p["date"].max()) - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    p = p[p["date"] >= start]
    if not s.empty:
        s = s[s["date_ist"] >= start].rename(columns={"date_ist": "date"})
        s["tone"] = s["mean_score"].map(lambda x: "positive" if x >= 0 else "negative")
    return s, p


def price_chart(p: pd.DataFrame, x_domain: list[str]) -> alt.Chart:
    return alt.Chart(p, height=220, title="Close price (INR)").mark_line(strokeWidth=2, color=SERIES[0]).encode(
        x=alt.X("date:T", title=None, scale=alt.Scale(domain=x_domain), axis=alt.Axis(format="%d %b", tickCount=8, labelOverlap=True)),
        y=alt.Y("close:Q", title=None, scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip("close:Q", format=",.2f", title="close")])


def sentiment_chart(s: pd.DataFrame, x_domain: list[str]) -> alt.Chart:
    bars = alt.Chart(s).mark_bar(cornerRadiusEnd=4, size=8).encode(
        x=alt.X("date:T", title=None, scale=alt.Scale(domain=x_domain), axis=alt.Axis(format="%d %b", tickCount=8, labelOverlap=True)),
        y=alt.Y("mean_score:Q", title=None, scale=alt.Scale(domain=[-1, 1]),
                axis=alt.Axis(values=[-1, -0.5, 0, 0.5, 1], format=".1f")),
        color=alt.Color("tone:N", scale=alt.Scale(domain=["positive", "negative"], range=[POS, NEG]),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip("mean_score:Q", format="+.2f", title="sentiment"),
                 alt.Tooltip("n_articles:Q", title="articles")])
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=MUTED, strokeWidth=1).encode(y="y:Q")
    return alt.layer(zero, bars).properties(height=220, title="Daily news sentiment (FinBERT, -1 to +1)")


def backtest_tables(hist_scored: pd.DataFrame, prices: pd.DataFrame, hold: int = 5,
                    exclude_price_reports: bool = True, rf: float = 0.065) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Event study (before vs after) and equity curves, using the same engine as backtest.py."""
    clean, _ = clean_prices(prices)
    opens, closes = price_panels(clean)
    cfg = Config(hold=hold, exclude_price_reports=exclude_price_reports)
    ev = events(daily_signal(hist_scored[hist_scored["date"] >= opens.index.min()], exclude_price_reports),
                opens, closes, hold)
    study = event_study(ev, cfg.threshold).reset_index().rename(columns={"score": "news"})
    long = pd.concat([
        study.assign(window="5 days before", value=study["pre_5d_abn_ret_%"], t=study["pre_t_stat"]),
        study.assign(window=f"{hold} days after", value=study["mean_abn_ret_%"], t=study["t_stat"]),
    ])[["news", "window", "value", "t", "events"]]

    strat = trim_to_events(portfolio_returns(ev, opens, closes, cfg, cash_return=rf / 252), ev)
    bench = trim_to_events(benchmark_returns(closes), ev)
    curves = pd.DataFrame({"News strategy": (1 + strat).cumprod(),
                           "Buy & hold (equal-weight)": (1 + bench).cumprod()})
    curves = curves.reset_index(names="date").melt("date", var_name="series", value_name="growth")
    return long, curves


def event_chart(long: pd.DataFrame) -> alt.Chart:
    order = ["5 days before", next(w for w in long["window"].unique() if w.endswith("after"))]
    bars = alt.Chart(long).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("news:N", title="sentiment of the headline", sort=["negative", "neutral", "positive"],
                axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("window:N", sort=order),
        y=alt.Y("value:Q", title=None),
        color=alt.Color("window:N", sort=order, scale=alt.Scale(domain=order, range=SERIES),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=["news", "window", alt.Tooltip("value:Q", format="+.2f", title="abnormal return %"),
                 alt.Tooltip("t:Q", format=".1f", title="t-stat"), "events"])
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=MUTED, strokeWidth=1).encode(y="y:Q")
    return alt.layer(bars, zero).properties(height=280, title="Abnormal return around the headline (%)")


def equity_chart(curves: pd.DataFrame) -> alt.Chart:
    names = list(curves["series"].unique())
    return alt.Chart(curves, height=300, title="Growth of 1 rupee (log scale, after costs)").mark_line(
        strokeWidth=2).encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("growth:Q", title=None, scale=alt.Scale(type="log"),
                axis=alt.Axis(values=[0.25, 1, 4, 16, 64], format="~g")),
        color=alt.Color("series:N", scale=alt.Scale(domain=names, range=SERIES),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("date:T"), "series", alt.Tooltip("growth:Q", format=".2f")])
