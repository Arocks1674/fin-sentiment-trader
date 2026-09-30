# Financial News Sentiment Trader (Nifty 50)

Ingests Indian market news and prices, scores news sentiment with FinBERT,
backtests a sentiment-driven strategy, and answers questions over the news
with a retrieval-augmented (RAG) LLM layer. Streamlit front end.

> Status: **Modules 1-2 of 5 complete** (ingestion, storage, entity-targeted FinBERT sentiment). This README only
> describes what is built. Later sections are added as modules land.

## Architecture (planned)

| # | Module | What it does | Status |
|---|--------|--------------|--------|
| 1 | Ingestion + storage | GNews REST API + yfinance -> SQLite, articles deduplicated and linked to every stock they mention | Done |
| 2 | Sentiment | Entity-targeted FinBERT: scores only sentences about each company, drops source-only mentions and syndicated copies, daily aggregate in IST | Done |
| 3 | Backtest | Historical headlines, next-day signals, Sharpe / max drawdown, costs, no lookahead | Next |
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
python -m pytest -q              :: 33 tests should pass
python ingest.py --prices-only   :: 2 years of daily prices for 10 Nifty stocks
python ingest.py                 :: prices + latest news (uses 10 GNews requests)
python score.py                  :: score new articles per company, print daily sentiment
python score.py --audit          :: list articles dropped as irrelevant, and why
python score.py --rescore        :: recompute all scores after changing the rules
```

Data lands in `data/trader.db` (SQLite):

- `articles`: one row per unique article (primary key = SHA-1 of the URL, so re-running never duplicates)
- `article_tickers`: which stocks each article is about. One story about two banks is stored once and linked to both.
- `prices`: one row per ticker per trading day (upsert, so re-running refreshes)
- `sentiment`: whole-article FinBERT scores (module 2, kept for comparison)
- `entity_sentiment`: per (article, company) score from only the sentences about that company, plus why an article was dropped

## Sentiment (modules 2, 2.1, 2.2)

A first version scored `title + description` for each article. Inspecting the most
positive and negative results showed three problems:

| Problem found | Example from the live data | Fix |
|---|---|---|
| Company is the source, not the subject | "Exports, rising power demand to support manufacturing growth: ICICI Bank" | Trailing `: Name`, "according to Name", "Name economists" do not count as a mention |
| Title is about the sector, description about the company | Title: "IT Stocks Rally"; description: "Infosys was the only stock trading lower" | Score only the sentences that mention the company |
| Same story, several URLs | One ICICI story counted 3 times | Collapse identical titles, or identical scored sentences, per stock per day |
| Company is one name in a list | "Stocks to watch: Rays of Belief, Prasol, Reliance, Bharti..." | Mentions inside a comma list of 4+ names are dropped |
| Sentence reports a price move | "Reliance Industries has fallen 25% in 2026" | Kept but flagged; `score_news` excludes these so the backtest can test whether sentiment adds anything beyond echoing past returns |

Sister companies ("ICICI Prudential", "ITC Hotels", "L&T Finance") are excluded before
matching. Job titles before the company ("Chief Economist, Kotak Mahindra Bank") count as source.
Rules live in `src/sentiment/entities.py`; every live example above is a test.

On the live data (102 stock-article pairs) these rules keep 84, and drop 14 list mentions and 4
source-only mentions.

Per (article, company) the score is the average of FinBERT's `positive - negative`
over the relevant sentences, in [-1, 1]. Daily values are grouped by India date (IST).

## Known limits

- The score is FinBERT's confidence about tone, not the size of the news: a 0.55% dip can score -0.97.
- A passing mention still counts: "HSBC competes with ICICI Bank" counts for ICICI, and a fire in a
  building that also houses a Kotak branch scores -0.84 for Kotak. Separating subject from
  passing mention needs more than rules; an LLM relevance check is planned for module 4.
- GNews free tier returns only recent articles (about 30 days) and ~100 requests/day,
  so it feeds the live dashboard. The backtest (module 3) uses a historical dataset.
- yfinance is an unofficial Yahoo wrapper; if it prints "possibly delisted", it is
  usually a network or rate-limit issue, not a delisting.
