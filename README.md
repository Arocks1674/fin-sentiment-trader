# Financial News Sentiment Trader (Nifty 50)

Ingests Indian market news and prices, scores news sentiment with FinBERT,
backtests a sentiment-driven strategy, and answers questions over the news
with a retrieval-augmented (RAG) LLM layer. Streamlit front end.

> Status: **Modules 1-3 of 5 complete** (ingestion, storage, entity-targeted FinBERT sentiment). This README only
> describes what is built. Later sections are added as modules land.

## Architecture (planned)

| # | Module | What it does | Status |
|---|--------|--------------|--------|
| 1 | Ingestion + storage | GNews REST API + yfinance -> SQLite, articles deduplicated and linked to every stock they mention | Done |
| 2 | Sentiment | Entity-targeted FinBERT: scores only sentences about each company, drops source-only mentions and syndicated copies, daily aggregate in IST | Done |
| 3 | Backtest | Event-driven, pooled across stocks; next-session entry; abnormal returns, Sharpe, max drawdown, costs; in/out-of-sample split | Done |
| 4 | RAG | sentence-transformers embeddings, Chroma vector store, LangChain + Gemini, cited answers | Next |
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
python -m pytest -q              :: 45 tests should pass
python ingest.py --prices-only   :: 2 years of daily prices for 10 Nifty stocks
python ingest.py                 :: prices + latest news (uses 10 GNews requests)
python score.py                  :: score new articles per company, print daily sentiment
python score.py --audit          :: list articles dropped as irrelevant, and why
python score.py --rescore        :: recompute all scores after changing the rules
python coverage.py               :: download historical headlines, report usable news per stock per year
python ingest.py --prices-only --start 2001-01-01   :: price history for the backtest
python backtest.py               :: event study + strategy vs buy-and-hold -> reports/results.md, reports/equity.png
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

## Backtest (module 3)

**Data.** Times of India headlines archive ("News Headlines of India", Harvard Dataverse,
doi:10.7910/DVN/DPQMQH, CC0), 2001 to mid-2020. `coverage.py` keeps business-section
headlines that pass the same entity rules as the live pipeline. Checking coverage first
changed the design: most stocks have news on only 10-40 days a year, so a daily
all-stocks strategy would mostly trade noise. The backtest is therefore **event-driven
and pooled** across the 10 stocks.

Coverage also exposed two data problems, both fixed in the entity rules and tested:
30% of bare-"Reliance" headlines were Anil Ambani group companies (Reliance Infocomm,
Reliance MF...), so only unambiguous names count for RIL; and the archive writes lists
with semicolons ("TCS; Wipro; Infosys"), which the list rule now handles.

**Timing (no lookahead).** The archive has dates but no times, so a headline dated D is
traded at the **open of the first session after D** and held 1 or 5 sessions.

**What is measured.**
- Event study: mean *abnormal* return (stock minus the equal-weight average return of all
  10 stocks over the same window) after negative, neutral and positive news, with t-stats.
- Strategy: long-only on positive news (Indian cash equities cannot be shorted overnight),
  0.25% round-trip cost, idle cash earns the risk-free rate, vs equal-weight buy-and-hold.
  CAGR, Sharpe and max drawdown for 2001-2014 and 2015-2020 separately.
- Everything is run **with and without price-report headlines**, to check whether any edge
  is just sentiment echoing past price moves.

Settings (threshold 0.3, hold 1 and 5 days) were fixed before looking at results, so
2015-2020 is an honest out-of-sample check. As a placebo, random sentiment scores produce
t-stats near zero and a losing strategy after costs.

Results: see `reports/results.md` and `reports/equity.png`.

## Known limits

- The score is FinBERT's confidence about tone, not the size of the news: a 0.55% dip can score -0.97.
- A passing mention still counts: "HSBC competes with ICICI Bank" counts for ICICI, and a fire in a
  building that also houses a Kotak branch scores -0.84 for Kotak. Separating subject from
  passing mention needs more than rules; an LLM relevance check is planned for module 4.
- GNews free tier returns only recent articles (about 30 days) and ~100 requests/day,
  so it feeds the live dashboard; the backtest uses the historical archive instead.
- The historical archive is one general newspaper, headlines only, ending mid-2020.
- yfinance is an unofficial Yahoo wrapper; if it prints "possibly delisted", it is
  usually a network or rate-limit issue, not a delisting.
