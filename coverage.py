"""Module 3, step 1: is there enough historical company news to backtest?

Downloads the Times of India headlines archive (once), keeps business headlines
that pass our entity rules for each stock, stores them, and prints how many
usable headlines each stock has per year.

Usage:
    python coverage.py                    # download + extract + report
    python coverage.py --csv path.csv     # use a CSV you already downloaded (e.g. from Kaggle)
    python coverage.py --all-categories   # also search non-business sections
"""
import argparse
import logging
import time
from pathlib import Path

import pandas as pd

import config
from src.ingest.historical import coverage, download, extract
from src.storage import db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("coverage")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, help="path to india-news-headlines.csv")
    p.add_argument("--all-categories", action="store_true")
    args = p.parse_args()

    csv_path = args.csv or download(config.DATA_DIR / "india-news-headlines.csv")
    t0 = time.time()
    df = extract(csv_path, list(config.TICKERS.values()), business_only=not args.all_categories)
    log.info("Extracted %d headlines in %.0fs", len(df), time.time() - t0)

    db.init_db(config.DB_PATH)
    db.save_hist_headlines(config.DB_PATH, df)

    pd.set_option("display.width", 250)
    print("\nUsable headlines per stock per year:\n")
    print(coverage(df).to_string())
    print(f"\nShare that are price reports: {df.price_report.mean():.0%}")
    print("\nSample:")
    print(df.sample(min(10, len(df)), random_state=0)[["date", "ticker", "headline"]].to_string(index=False))


if __name__ == "__main__":
    main()
