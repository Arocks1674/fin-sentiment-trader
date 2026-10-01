"""Module 4: RAG pipeline with fake embeddings and a fake LLM (no downloads, no API key)."""
import pandas as pd
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src.rag import qa
from src.rag.corpus import all_documents
from src.rag.store import get_store, index
from src.storage import db


@pytest.fixture
def populated_db(tmp_path):
    p = tmp_path / "t.db"
    db.init_db(p)
    art = lambda url, title, when: {"title": title, "description": "", "url": url, "published_at": when}
    db.upsert_articles(p, "INFY.NS", [art("u1", "Infosys wins $1bn deal", "2026-09-20T05:00:00Z")])
    db.upsert_articles(p, "TCS.NS", [art("u2", "TCS and Infosys bid for UK contract", "2026-09-25T05:00:00Z")])
    db.upsert_articles(p, "INFY.NS", [art("u2", "TCS and Infosys bid for UK contract", "2026-09-25T05:00:00Z")])
    db.save_hist_headlines(p, pd.DataFrame([
        {"date": "2017-08-19", "ticker": "INFY.NS", "headline": "Vishal Sikka resigns as Infosys CEO",
         "category": "business", "price_report": 0},
        {"date": "2011-08-31", "ticker": "RELIANCE.NS", "headline": "RIL completes $7 billion deal with BP",
         "category": "business", "price_report": 0}]))
    return p


@pytest.fixture
def store(tmp_path, populated_db):
    s = get_store(tmp_path / "chroma", DeterministicFakeEmbedding(size=32))
    index(s, all_documents(populated_db))
    return s


def test_one_document_per_story_with_all_stock_flags(populated_db):
    docs = {d.id: d for d in all_documents(populated_db)}
    assert len(docs) == 4
    shared = docs["live-" + db.article_id("u2")]
    assert shared.metadata["TCS"] and shared.metadata["INFY"]
    assert docs["live-" + db.article_id("u1")].metadata["date"] == 20260920


def test_indexing_is_incremental(store, populated_db):
    assert index(store, all_documents(populated_db)) == 0


def test_question_detects_stocks():
    assert qa.tickers_in("Why did infosys shares fall?") == ["INFY.NS"]
    assert set(qa.tickers_in("Compare TCS and Infosys")) == {"INFY.NS", "TCS.NS"}
    assert qa.tickers_in("What is ICICI Prudential doing?") == []      # sister company is not ICICI Bank


def test_retrieval_respects_stock_and_date_filters(store):
    docs = store.similarity_search("deal", k=10, filter=qa.build_filter(["RELIANCE.NS"]))
    assert [d.metadata["title"] for d in docs] == ["RIL completes $7 billion deal with BP"]
    docs = store.similarity_search("deal", k=10, filter=qa.build_filter(["INFY.NS"], since="2026-01-01"))
    assert {d.metadata["kind"] for d in docs} == {"live"} and len(docs) == 2


def test_answer_cites_supplied_items_only(store):
    llm = FakeListChatModel(responses=["Infosys won a $1bn deal [1] and bid for a UK contract [2] [9]."])
    a = qa.answer("What has Infosys won recently?", store, llm, k=2, since="2026-01-01")
    assert a.tickers == ["INFY.NS"] and len(a.sources) == 2
    assert a.invalid_citations == [9]              # the model cited an item we never gave it


def test_no_matching_news_skips_the_llm(store):
    class Boom:
        def invoke(self, _):
            raise AssertionError("LLM must not be called without context")
    a = qa.answer("Kotak Mahindra Bank results", store, Boom())
    assert a.text == qa.NO_NEWS and a.sources == []


def test_prompt_numbers_items_with_date_and_source(store):
    docs = store.similarity_search("x", k=10, filter=qa.build_filter(["INFY.NS"], until="2020-12-31"))
    ctx = qa.format_context(docs)
    assert ctx.startswith("[1] (2017-08-19, Times of India) Vishal Sikka resigns")


def test_gemini_list_content_is_reduced_to_text():
    from langchain_core.messages import AIMessage
    msg = AIMessage(content=[{"type": "text", "text": "Infosys fell [1]."},
                             {"type": "thinking", "signature": "EpIbCkYIBxgCKkA...very long base64..."}])
    assert qa.reply_text(msg) == "Infosys fell [1]."


def test_recency_words_become_a_date_filter():
    from datetime import date
    assert qa.default_since("Why did Infosys fall recently?", date(2026, 10, 1)) == "2026-08-02"
    assert qa.default_since("What happened to Infosys in 2017?") is None


def test_recent_question_ignores_old_archive(store):
    llm = FakeListChatModel(responses=["ok [1]"])
    a = qa.answer("What has Infosys done recently?", store, llm, k=10)
    assert a.since and all(d.metadata["kind"] == "live" for d in a.sources)
