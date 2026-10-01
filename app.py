"""Module 5: Streamlit dashboard.

Run:  streamlit run app.py

Tabs:
  Live sentiment - price and daily news sentiment for one stock, plus the scored articles
  Backtest       - what 20 years of headlines say about sentiment and returns
  Ask the news   - cited answers from the stored news (RAG, needs GEMINI_API_KEY)
"""
import pandas as pd
import streamlit as st

import config
from src.app import views
from src.sentiment.finbert import MODEL_NAME
from src.storage import db

st.set_page_config(page_title="Nifty News Sentiment", layout="wide")
db.init_db(config.DB_PATH)
NAMES = {t: n for n, t in config.TICKERS.items()}


@st.cache_data(ttl=600)
def load_live():
    return db.load_entity_scored(config.DB_PATH, MODEL_NAME), db.load_prices(config.DB_PATH)


@st.cache_data(ttl=3600)
def load_backtest(hold: int, exclude: bool):
    hist = db.load_hist_scored(config.DB_PATH, MODEL_NAME)
    if hist.empty:
        return None, None
    return views.backtest_tables(hist, db.load_prices(config.DB_PATH), hold, exclude)


@st.cache_resource
def rag_components():
    from src.rag.store import get_embeddings, get_llm, get_store
    store = get_store(config.CHROMA_DIR, get_embeddings(config.EMBED_MODEL))
    return store, get_llm(config.GEMINI_MODEL, config.GEMINI_API_KEY)


st.title("Nifty 50 news sentiment")
st.caption("FinBERT sentiment on company-specific sentences · event-study backtest 2001-2020 · "
           "cited Q&A over the news. Research project, not investment advice.")

live_tab, bt_tab, ask_tab = st.tabs(["Live sentiment", "Backtest", "Ask the news"])

with live_tab:
    scored, prices = load_live()
    c1, c2 = st.columns([2, 1])
    ticker = c1.selectbox("Stock", list(NAMES), format_func=lambda t: f"{NAMES[t]} ({t})")
    days = c2.select_slider("Window", options=[30, 90, 180, 365], value=30, format_func=lambda d: f"{d} days")
    s, p = views.stock_daily(scored, prices, ticker, days)
    if p.empty:
        st.info("No prices yet. Run `python ingest.py --prices-only`.")
    else:
        domain = [p["date"].min(), p["date"].max()]
        st.altair_chart(views.price_chart(p, domain), width="stretch")
        if s.empty:
            st.info("No scored news for this stock in this window. Run `python ingest.py` then `python score.py`.")
        else:
            st.altair_chart(views.sentiment_chart(s, domain), width="stretch")
            first = scored["published_at"].min()[:10] if not scored.empty else ""
            st.caption(f"Live news collection started {first}; earlier days have no sentiment bars.")
        arts = views.recent_articles(scored, ticker)
        if not arts.empty:
            st.subheader("Scored articles")
            st.dataframe(
                arts[["published_at", "score", "label", "title", "sentences", "url"]].rename(
                    columns={"published_at": "published", "sentences": "sentences scored"}),
                column_config={"score": st.column_config.NumberColumn(format="%+.2f"),
                               "url": st.column_config.LinkColumn("link", display_text="open")},
                hide_index=True, width="stretch")

with bt_tab:
    c1, c2 = st.columns(2)
    hold = c1.radio("Holding period", [1, 5], index=1, horizontal=True, format_func=lambda h: f"{h} day(s)")
    exclude = c2.toggle("Exclude price-report headlines", value=True)
    long, curves = load_backtest(hold, exclude)
    if long is None:
        st.info("No historical headlines yet. Run `python coverage.py` and `python backtest.py`.")
    else:
        st.markdown("**Finding:** stocks move *before* the newspaper prints the headline, so trading "
                    "after publication does not beat buy-and-hold. Entry is the next session's open; "
                    "abnormal return = stock minus the equal-weight average of the 10 stocks.")
        st.altair_chart(views.event_chart(long), width="stretch")
        st.altair_chart(views.equity_chart(curves), width="stretch")
        with st.expander("Event study table"):
            st.dataframe(long, hide_index=True, width="stretch")
        st.caption("Limits: one newspaper, dates without times, today's large caps chosen with hindsight "
                   "(survivorship bias). Full tables in reports/results.md.")

with ask_tab:
    if not config.GEMINI_API_KEY:
        st.warning("Add GEMINI_API_KEY to .env to enable questions.")
    q = st.text_input("Ask about the stored news", placeholder="Why did Infosys shares fall recently?")
    c1, c2, c3 = st.columns(3)
    k = c1.slider("Sources", 3, 12, 6)
    since = c2.date_input("Since", value=None)
    until = c3.date_input("Until", value=None)
    if q and config.GEMINI_API_KEY:
        from src.rag import qa
        store, llm = rag_components()
        with st.spinner("Searching the news and drafting a cited answer..."):
            a = qa.answer(q, store, llm, k=k, since=str(since) if since else None,
                          until=str(until) if until else None)
        st.caption(f"Stocks detected: {', '.join(a.tickers) or 'none (all news)'}"
                   + (f" · news since {a.since}" if a.since else ""))
        st.markdown(a.text)
        if a.invalid_citations:
            st.error(f"The answer cites items that were not provided: {a.invalid_citations}")
        if a.sources:
            st.dataframe(pd.DataFrame([{"#": i, "date": d.metadata["date_iso"], "source": d.metadata["source"],
                                        "headline": d.metadata["title"], "url": d.metadata["url"]}
                                       for i, d in enumerate(a.sources, 1)]),
                         column_config={"url": st.column_config.LinkColumn("link", display_text="open")},
                         hide_index=True, width="stretch")
