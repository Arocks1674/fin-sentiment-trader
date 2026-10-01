"""Event-driven backtest of news sentiment on Nifty stocks.

Timing (the part that prevents lookahead):
  A headline dated D (no time of day known) is only acted on at the OPEN of
  the first trading session strictly after D. The position is held for
  `hold` sessions and exited at that session's CLOSE.

Why event-driven: most stocks have news on only 10-40 days a year in the
archive, so a strategy that must hold every stock every day would mostly
trade noise. Instead each (stock, news day) is an event, pooled across stocks.

Returns are measured two ways:
  raw      - the stock's own return over the holding window
  abnormal - raw minus the equal-weight average return of all 10 stocks over
             the same window, i.e. what the news added beyond the market move
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Config:
    hold: int = 1                    # sessions held
    threshold: float = 0.3           # |daily score| needed to act
    cost: float = 0.0025             # round-trip cost as a fraction (brokerage + STT + slippage)
    exclude_price_reports: bool = False
    long_only: bool = True           # cash equities in India cannot be shorted overnight


def daily_signal(scored: pd.DataFrame, exclude_price_reports: bool = False) -> pd.DataFrame:
    """One row per (ticker, news date): mean headline score and headline count."""
    df = scored[~scored["price_report"].astype(bool)] if exclude_price_reports else scored
    g = df.groupby(["ticker", "date"])["score"]
    return pd.DataFrame({"score": g.mean(), "n": g.size()}).reset_index()


def price_panels(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Wide open/close tables: index = trading date (str), columns = tickers."""
    o = prices.pivot(index="date", columns="ticker", values="open").sort_index()
    c = prices.pivot(index="date", columns="ticker", values="close").sort_index()
    return o, c


def events(signal: pd.DataFrame, opens: pd.DataFrame, closes: pd.DataFrame, hold: int) -> pd.DataFrame:
    """Attach entry/exit dates and raw + abnormal returns to every news day."""
    dates = opens.index.to_numpy()
    rows = []
    for r in signal.itertuples(index=False):
        if r.ticker not in opens.columns:
            continue
        i = np.searchsorted(dates, r.date, side="right")   # first session strictly AFTER the news date
        j = i + hold - 1
        if j >= len(dates):
            continue
        o = opens.iat[i, opens.columns.get_loc(r.ticker)]
        c = closes.iat[j, closes.columns.get_loc(r.ticker)]
        if not (np.isfinite(o) and np.isfinite(c)) or o <= 0:
            continue
        raw = c / o - 1
        # Abnormal return over the 5 sessions BEFORE entry (up to the news-day close):
        # tells us whether the headline arrived after the market had already moved.
        pre = np.nan
        if i >= 6:
            pc = closes.iloc[i - 1] / closes.iloc[i - 6] - 1
            pre = float(pc[r.ticker] - pc.mean(skipna=True))
        # Equal-weight market: the AVERAGE of each stock's own return over the same window
        # (averaging prices instead would overweight high-priced stocks).
        mkt = float((closes.iloc[j] / opens.iloc[i] - 1).mean(skipna=True))
        rows.append((r.ticker, r.date, dates[i], dates[j], r.score, r.n, raw, raw - mkt, pre))
    return pd.DataFrame(rows, columns=["ticker", "news_date", "entry", "exit", "score", "n",
                                       "ret", "abn_ret", "pre_abn_ret"])


def event_study(ev: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Mean abnormal return by sentiment bucket, with t-statistics."""
    b = pd.cut(ev["score"], [-1.01, -threshold, threshold, 1.01], labels=["negative", "neutral", "positive"])
    g = ev.groupby(b, observed=False)["abn_ret"]
    out = pd.DataFrame({"events": g.size(), "mean_abn_ret_%": g.mean() * 100,
                        "hit_rate_%": g.apply(lambda s: (s > 0).mean() * 100)})
    se = g.std() / np.sqrt(g.size())
    out["t_stat"] = g.mean() / se
    if "pre_abn_ret" in ev:
        gp = ev.groupby(b, observed=False)["pre_abn_ret"]
        out["pre_5d_abn_ret_%"] = gp.mean() * 100
        out["pre_t_stat"] = gp.mean() / (gp.std() / np.sqrt(gp.count()))
    return out


def portfolio_returns(ev: pd.DataFrame, opens: pd.DataFrame, closes: pd.DataFrame,
                      cfg: Config, cash_return: float = 0.0) -> pd.Series:
    """Daily returns of a portfolio that equally splits capital across open positions.

    Long when score >= threshold (and short when <= -threshold unless long_only).
    Days with no open position earn `cash_return` (daily risk-free rate), like idle cash would.
    """
    trades = ev[ev["score"] >= cfg.threshold].assign(side=1)
    if not cfg.long_only:
        trades = pd.concat([trades, ev[ev["score"] <= -cfg.threshold].assign(side=-1)])
    dates = closes.index
    pos_ret = {d: [] for d in dates}
    for t in trades.itertuples(index=False):
        i, j = dates.get_loc(t.entry), dates.get_loc(t.exit)
        col = closes.columns.get_loc(t.ticker)
        for k in range(i, j + 1):
            prev = opens.iat[k, col] if k == i else closes.iat[k - 1, col]
            r = closes.iat[k, col] / prev - 1
            if k == i:
                r -= cfg.cost                       # whole round-trip cost charged at entry
            pos_ret[dates[k]].append(t.side * r)
    return pd.Series({d: (np.mean(v) if v else cash_return) for d, v in pos_ret.items()}).sort_index()


def spread_permutation_test(ev: pd.DataFrame, threshold: float, n: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Is the positive-minus-negative return spread bigger than chance?

    Per-group t-stats can mislead: every news day (whatever its tone) is followed by a
    small negative drift, so even random "positive" labels look significant. The fair test
    shuffles the sentiment scores across events (same events, same score distribution, no
    link between tone and returns) and asks how often the shuffled spread is as extreme
    as the real one.
    """
    ev = ev.dropna(subset=["pre_abn_ret"])
    rng = np.random.default_rng(seed)
    out = []
    for col, label in [("pre_abn_ret", "5 days before"), ("abn_ret", "after entry")]:
        x = ev[col].to_numpy()

        def spread(scores):
            pos, neg = scores >= threshold, scores <= -threshold
            return x[pos].mean() - x[neg].mean()

        real = spread(ev["score"].to_numpy())
        null = np.array([spread(rng.permutation(ev["score"].to_numpy())) for _ in range(n)])
        out.append({"window": label, "pos_minus_neg_%": real * 100,
                    "placebo_2.5%": np.percentile(null, 2.5) * 100,
                    "placebo_97.5%": np.percentile(null, 97.5) * 100,
                    "p_value": (np.sum(np.abs(null) >= abs(real)) + 1) / (n + 1),
                    "all_news_mean_%": x.mean() * 100,
                    "all_news_t": x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))})
    return pd.DataFrame(out).set_index("window")


def trim_to_events(returns: pd.Series, ev: pd.DataFrame) -> pd.Series:
    """Keep only the days the news sample covers: first entry to last exit.

    Prices run to today but the headline archive ends in mid-2020. Without this cut,
    the strategy would earn the risk-free rate for years with no news while the
    benchmark keeps compounding, and both would be scored on a period with no signal.
    """
    if ev.empty:
        return returns.iloc[0:0]
    return returns[(returns.index >= ev["entry"].min()) & (returns.index <= ev["exit"].max())]


def benchmark_returns(closes: pd.DataFrame) -> pd.Series:
    """Equal-weight buy-and-hold of all stocks, rebalanced daily."""
    return closes.pct_change(fill_method=None).mean(axis=1).fillna(0.0)
