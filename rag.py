"""Module 4: ask questions about the stored news, with cited answers.

Usage:
    python rag.py index                                   # embed new articles/headlines into Chroma
    python rag.py ask "Why did Infosys shares fall?"
    python rag.py ask "What did RIL announce?" --since 2026-09-01
    python rag.py ask "TCS deal wins" --k 10
    python rag.py models                                  # Gemini models your key can use

Embeddings run locally (sentence-transformers/all-MiniLM-L6-v2, ~90 MB first download).
Answers come from Gemini and may only use the retrieved news items.
"""
import argparse
import logging
import textwrap

import config
from src.rag import qa
from src.rag.corpus import all_documents
from src.rag.store import get_embeddings, get_llm, get_store, index
from src.storage import db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
for noisy in ("httpx", "httpcore", "huggingface_hub", "sentence_transformers", "chromadb", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
log = logging.getLogger("rag")


def cmd_index() -> None:
    db.init_db(config.DB_PATH)
    docs = all_documents(config.DB_PATH)
    store = get_store(config.CHROMA_DIR, get_embeddings(config.EMBED_MODEL))
    added = index(store, docs)
    log.info("%d documents in the database, %d newly embedded", len(docs), added)


def cmd_ask(args) -> None:
    store = get_store(config.CHROMA_DIR, get_embeddings(config.EMBED_MODEL))
    llm = get_llm(config.GEMINI_MODEL, config.GEMINI_API_KEY)
    a = qa.answer(args.question, store, llm, k=args.k, since=args.since, until=args.until)
    print(f"\nStocks detected: {', '.join(a.tickers) or 'none (searching all news)'}"
          + (f"  |  news since {a.since}" if a.since else "") + "\n")
    print(textwrap.fill(a.text, 100, replace_whitespace=False) if "\n" not in a.text else a.text)
    if a.sources:
        print("\nSources:")
        for i, d in enumerate(a.sources, 1):
            m = d.metadata
            print(f"  [{i}] {m['date_iso']}  {m['source']}  {m['title'][:90]}  {m['url']}")
    if a.invalid_citations:
        print(f"\nWARNING: the answer cites items that were not provided: {a.invalid_citations}")


def cmd_models() -> None:
    if not config.GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set in .env")
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    for m in client.models.list():
        if "generateContent" in (m.supported_actions or []):
            print(m.name.removeprefix("models/"))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index")
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--k", type=int, default=6)
    a.add_argument("--since", help="YYYY-MM-DD")
    a.add_argument("--until", help="YYYY-MM-DD")
    sub.add_parser("models")
    args = p.parse_args()
    {"index": cmd_index, "models": cmd_models}.get(args.cmd, lambda: cmd_ask(args))()


if __name__ == "__main__":
    main()
