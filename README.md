# Financial News Sentiment Trader (Nifty 50)

Ingests Indian market news and prices, scores news sentiment with FinBERT,
backtests a sentiment-driven strategy, and answers questions over the news
with a retrieval-augmented (RAG) LLM layer. Streamlit front end.

> Status: **Module 1 of 5 complete** (ingestion + storage). This README only
> describes what is built. Later sections are added as modules land.

## Architecture (planned)

| # | Module | What it does | Status |
|---|--------|--------------|--------|
| 1 | Ingestion + storage | GNews REST API + yfinance -> SQLite, deduplicated | Done |
| 2 | Sentiment | FinBERT scores per article, daily aggregate per ticker | Next |
| 3 | Backtest | Historical headlines, next-day signals, Sharpe / max drawdown, costs, no lookahead | Planned |
| 4 | RAG | sentence-transformers embeddings, Chroma vector store, LangChain + Gemini, cited answers | Planned |
| 5 | Front end | Streamlit dashboard: signals, equity curve, "ask the news" | Planned |

## Setup (Windows, Command Prompt)

```bat
cd fin-sentiment-trader
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```
Put your GNews key in `.env` (get one at https://gnews.io). `.env` is git-ignored.

## Run

```bat
python -m pytest -q              :: 5 tests should pass
python ingest.py --prices-only   :: 2 years of daily prices for 10 Nifty stocks
python ingest.py                 :: prices + latest news (uses 10 GNews requests)
```

Data lands in `data/trader.db` (SQLite):

- `articles`: one row per unique article (primary key = SHA-1 of the URL, so re-running never duplicates)
- `prices`: one row per ticker per trading day (upsert, so re-running refreshes)

## Known limits

- GNews free tier returns only recent articles (about 30 days) and ~100 requests/day,
  so it feeds the live dashboard. The backtest (module 3) uses a historical dataset.
- yfinance is an unofficial Yahoo wrapper; if it prints "possibly delisted", it is
  usually a network or rate-limit issue, not a delisting.
