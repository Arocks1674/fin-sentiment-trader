"""Score every not-yet-scored article with FinBERT, then print daily sentiment.

Usage:
    python score.py              # score new articles, show last 10 days per stock
    python score.py --show 30    # show more days

The first run downloads the model (~440 MB) into your Hugging Face cache.
"""
import argparse
import logging
import time

import config
from src.sentiment.aggregate import daily_sentiment
from src.sentiment.finbert import MODEL_NAME, FinBertScorer, article_text
from src.storage import db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("score")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--show", type=int, default=10, help="days of daily sentiment to print per stock")
    args = p.parse_args()

    db.init_db(config.DB_PATH)
    todo = db.unscored_articles(config.DB_PATH, MODEL_NAME)
    log.info("%d articles to score", len(todo))

    if len(todo):
        t0 = time.time()
        scorer = FinBertScorer()
        texts = [article_text(r.title, r.description) for r in todo.itertuples()]
        records = scorer.score(texts)
        for rec, aid in zip(records, todo["id"]):
            rec["article_id"] = aid
        db.save_sentiment(config.DB_PATH, MODEL_NAME, records)
        log.info("Scored %d articles in %.1fs", len(records), time.time() - t0)

    daily = daily_sentiment(db.load_scored_articles(config.DB_PATH, MODEL_NAME))
    if daily.empty:
        log.info("No scored articles yet. Run ingest.py first.")
        return
    recent = daily.groupby("ticker").tail(args.show)
    print(recent.to_string(index=False, float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
