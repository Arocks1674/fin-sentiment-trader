"""Module 3: does historical news sentiment predict next-day returns?

Steps:
  1. FinBERT-scores every historical headline not scored yet (cached in SQLite).
  2. Builds one signal per (stock, news date).
  3. Event study: average ABNORMAL return (stock minus equal-weight market of the
     10 stocks) after negative / neutral / positive news, with t-statistics,
     with and without price-report headlines.
  4. Long-only strategy with trading costs vs equal-weight buy-and-hold:
     CAGR, Sharpe, max drawdown, split into 2001-2014 and 2015-2020.
     Settings are fixed up front (threshold 0.3, hold 1 and 5 days) and NOT tuned
     on the 2015-2020 period, so that period is a fair out-of-sample check.

Needs prices back to 2001:  python ingest.py --prices-only --start 2001-01-01

Usage:
    python backtest.py
    python backtest.py --cost 0.004 --threshold 0.5
"""
import argparse
import logging
from pathlib import Path

import pandas as pd

import config
from src.backtest import metrics
from src.backtest.engine import (Config, benchmark_returns, daily_signal, event_study, events,
                                 portfolio_returns, price_panels)
from src.ingest.prices import clean_prices
from src.sentiment.finbert import MODEL_NAME, FinBertScorer
from src.storage import db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("backtest")
SPLIT = "2015-01-01"
REPORTS = config.ROOT / "reports"


def score_history() -> None:
    todo = db.unscored_hist(config.DB_PATH, MODEL_NAME)
    if todo.empty:
        return
    log.info("Scoring %d historical headlines with FinBERT (one-time, a few minutes on CPU)", len(todo))
    recs = FinBertScorer().score(todo["headline"].tolist())
    db.save_hist_sentiment(config.DB_PATH, MODEL_NAME, pd.concat([todo, pd.DataFrame(recs)], axis=1))


def run(cfg: Config, scored: pd.DataFrame, opens, closes, rf: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    sig = daily_signal(scored, cfg.exclude_price_reports)
    ev = events(sig, opens, closes, cfg.hold)
    strat = portfolio_returns(ev, opens, closes, cfg, cash_return=rf / metrics.TRADING_DAYS)
    bench = benchmark_returns(closes)
    rows = []
    for label, lo, hi in [("2001-2014 (in-sample)", None, SPLIT), ("2015-2020 (out-of-sample)", SPLIT, None),
                          ("full period", None, None)]:
        s, b = strat.loc[lo:hi], bench.loc[lo:hi]
        if hi:
            s, b = s[s.index < hi], b[b.index < hi]
        rows.append({"period": label, "strategy": "news long-only", **metrics.summary(s, rf)})
        rows.append({"period": label, "strategy": "buy & hold (EW)", **metrics.summary(b, rf)})
    return event_study(ev, cfg.threshold), pd.DataFrame(rows), strat


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=float, default=0.3)
    p.add_argument("--cost", type=float, default=0.0025, help="round-trip cost, 0.0025 = 0.25%%")
    p.add_argument("--rf", type=float, default=0.065, help="annual risk-free rate for Sharpe")
    args = p.parse_args()

    db.init_db(config.DB_PATH)
    score_history()
    scored = db.load_hist_scored(config.DB_PATH, MODEL_NAME)
    prices = db.load_prices(config.DB_PATH)
    if scored.empty:
        raise SystemExit("No historical headlines. Run: python coverage.py")
    if prices.empty or prices["date"].min() > "2002-12-31":
        raise SystemExit("Prices start too late. Run: python ingest.py --prices-only --start 2001-01-01")

    prices, removed = clean_prices(prices)
    log.info("Price cleaning removed %d rows: %s", len(removed), removed["reason"].value_counts().to_dict())
    opens, closes = price_panels(prices)
    scored = scored[scored["date"] >= opens.index.min()]
    REPORTS.mkdir(exist_ok=True)
    pd.set_option("display.width", 200)
    fmt = lambda x: f"{x:.2f}"
    md = ["# Backtest results\n", f"Headlines: {len(scored)}  |  threshold {args.threshold}  |  "
          f"round-trip cost {args.cost:.2%}  |  risk-free {args.rf:.1%}\n",
          f"Price rows removed by cleaning: {len(removed)} "
          f"({', '.join(f'{k}: {v}' for k, v in removed['reason'].value_counts().items())})\n"]
    curves = {}

    for hold in (1, 5):
        for excl in (False, True):
            cfg = Config(hold=hold, threshold=args.threshold, cost=args.cost, exclude_price_reports=excl)
            study, perf, strat = run(cfg, scored, opens, closes, args.rf)
            title = f"Hold {hold} day(s), {'excluding' if excl else 'including'} price-report headlines"
            print(f"\n=== {title} ===\n\nEvent study (abnormal return after the news):")
            print(study.to_string(float_format=fmt))
            print("\nStrategy vs benchmark:")
            print(perf.to_string(index=False, float_format=fmt))
            md += [f"\n## {title}\n", "Event study (abnormal return vs equal-weight market):\n",
                   study.to_markdown(floatfmt=".2f"), "\n\nStrategy vs benchmark:\n",
                   perf.to_markdown(index=False, floatfmt=".2f"), "\n"]
            curves[title] = (1 + strat).cumprod()

    curves["Buy & hold, equal-weight 10 stocks"] = (1 + benchmark_returns(closes)).cumprod()
    (REPORTS / "results.md").write_text("\n".join(md), encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ax = pd.DataFrame(curves).set_index(pd.to_datetime(list(closes.index))).plot(
            figsize=(11, 5), logy=True, title="Growth of 1 rupee (log scale), costs included")
        ax.axvline(pd.Timestamp(SPLIT), color="grey", ls="--", lw=1)
        ax.set_xlabel("")
        plt.tight_layout()
        plt.savefig(REPORTS / "equity.png", dpi=120)
    except ImportError:
        log.warning("matplotlib not installed; skipping chart")
    log.info("Saved %s and %s", REPORTS / "results.md", REPORTS / "equity.png")


if __name__ == "__main__":
    main()
