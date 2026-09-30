"""Score news sentiment per company with FinBERT, then print daily sentiment.

Module 2.1 (default): for every (article, stock) pair, score only the
sentences that are about that stock, skip articles where the stock is not
mentioned or is only the source, and collapse syndicated copies.

Usage:
    python score.py              # score new pairs, show last 10 days per stock
    python score.py --show 30
    python score.py --audit      # print what was dropped and why

The first run downloads the model (~440 MB) into your Hugging Face cache.
"""
import argparse
import logging
import time

import pandas as pd

import config
from src.sentiment.aggregate import daily_sentiment, drop_syndicated
from src.sentiment.entities import relevant_sentences
from src.sentiment.finbert import MODEL_NAME, FinBertScorer
from src.storage import db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("score")


def score_new_pairs() -> None:
    todo = db.unscored_pairs(config.DB_PATH, MODEL_NAME)
    log.info("%d (article, stock) pairs to check", len(todo))
    if todo.empty:
        return

    rows, flat = [], []                      # flat: (row index, sentence) for batching
    for r in todo.itertuples():
        rel = relevant_sentences(r.ticker, r.title, r.description)
        rows.append({"article_id": r.article_id, "ticker": r.ticker,
                     "reason": rel.reason, "sentences": rel.sentences})
        flat += [(len(rows) - 1, s) for s in rel.sentences]

    if flat:
        t0 = time.time()
        scores = FinBertScorer().score([s for _, s in flat])
        by_row: dict[int, list[dict]] = {}
        for (i, _), sc in zip(flat, scores):
            by_row.setdefault(i, []).append(sc)
        for i, scs in by_row.items():
            p = sum(s["positive"] for s in scs) / len(scs)
            n = sum(s["negative"] for s in scs) / len(scs)
            u = sum(s["neutral"] for s in scs) / len(scs)
            probs = {"positive": p, "negative": n, "neutral": u}
            rows[i].update(probs, label=max(probs, key=probs.get), score=p - n)
        log.info("Scored %d sentences in %.1fs", len(flat), time.time() - t0)

    db.save_entity_sentiment(config.DB_PATH, MODEL_NAME, rows)
    counts = pd.Series([r["reason"] for r in rows]).value_counts().to_dict()
    log.info("Kept %d, not mentioned %d, company only the source %d",
             counts.get("ok", 0), counts.get("not_mentioned", 0), counts.get("source_only", 0))


def audit() -> None:
    all_rows = db.load_entity_scored(config.DB_PATH, MODEL_NAME, relevant_only=False)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 90)
    for reason in ["source_only", "not_mentioned"]:
        sub = all_rows[all_rows.reason == reason]
        print(f"\n== {reason}: {len(sub)} ==")
        print(sub[["ticker", "title"]].head(15).to_string(index=False))
    kept = all_rows[all_rows.reason == "ok"]
    dups = len(kept) - len(drop_syndicated(kept))
    print(f"\n== syndicated copies collapsed: {dups} ==")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--show", type=int, default=10, help="days of daily sentiment to print per stock")
    p.add_argument("--audit", action="store_true", help="list dropped articles and why")
    args = p.parse_args()

    db.init_db(config.DB_PATH)
    score_new_pairs()

    if args.audit:
        audit()
        return

    daily = daily_sentiment(db.load_entity_scored(config.DB_PATH, MODEL_NAME))
    if daily.empty:
        log.info("No relevant scored articles yet. Run ingest.py first.")
        return
    print(daily.groupby("ticker").tail(args.show).to_string(index=False, float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
