"""Run ingestion: fetch news + prices for every ticker and store them.

Usage (from the project folder):
    python ingest.py                 # news + last 2 years of prices
    python ingest.py --prices-only   # skip GNews (saves your daily quota)
    python ingest.py --start 2023-01-01
"""
import argparse
import logging
import time
from datetime import date, timedelta

import config
from src.ingest.news import NewsAPIError, fetch_gnews
from src.ingest.prices import fetch_prices
from src.storage import db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("ingest")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default=str(date.today() - timedelta(days=730)))
    p.add_argument("--prices-only", action="store_true")
    args = p.parse_args()

    db.init_db(config.DB_PATH)
    total_new = 0

    for name, ticker in config.TICKERS.items():
        n = db.upsert_prices(config.DB_PATH, ticker, fetch_prices(ticker, args.start))
        log.info("%-12s prices: %d rows", ticker, n)

        if not args.prices_only:
            try:
                arts = fetch_gnews(name, config.GNEWS_API_KEY, config.GNEWS_MAX_PER_QUERY)
            except NewsAPIError as e:
                log.error("%s news failed: %s", ticker, e)
                continue
            new = db.upsert_articles(config.DB_PATH, ticker, arts)
            total_new += new
            log.info("%-12s news:   %d fetched, %d new", ticker, len(arts), new)
            time.sleep(config.REQUEST_PAUSE_SEC)

    log.info("Done. %d new articles. Database: %s", total_new, config.DB_PATH)


if __name__ == "__main__":
    main()
