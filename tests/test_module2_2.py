"""Module 2.2: list mentions, price reports, role-title sources, sentence-level dedup.
Cases are real sentences from the live database."""
import sqlite3

import pandas as pd

from src.sentiment.aggregate import daily_sentiment, drop_syndicated
from src.sentiment.entities import is_price_report, relevant_sentences
from src.storage import db


def test_role_title_before_company_is_source():
    t = "Manufacturing a bright spot; services presents a mixed bag: Upasna Bhardwaj, Chief Economist, Kotak Mahindra Bank"
    assert relevant_sentences("KOTAKBANK.NS", t, "").reason == "source_only"


def test_list_mentions_are_dropped():
    d = ("Stocks like Rays of Belief, Prasol Chemicals, Reliance Industries, Bharti Airtel, Vodafone Idea, "
         "Honasa Consumer, HCL Technologies will be in focus.")
    assert relevant_sentences("RELIANCE.NS", "Stocks to Watch, 29 Sept", d).reason == "list_only"
    d2 = "Top picks include Bharti Airtel, ICICI Bank, SBI, Titan Company, Adani Enterprises."
    assert relevant_sentences("ICICIBANK.NS", "Motilal Oswal's top picks", d2).reason == "list_only"


def test_two_company_sentence_is_not_a_list():
    rel = relevant_sentences("RELIANCE.NS", "Reliance, Nayara restrict fuel sales as crude hits $107", "")
    assert rel.reason == "ok"


def test_price_reports_are_flagged_not_dropped():
    rel = relevant_sentences("RELIANCE.NS", "Reliance Industries fell 25% this year: which funds are exposed",
                             "Reliance Industries has fallen 25% in 2026.")
    assert rel.reason == "ok" and rel.price_report == [True, True]
    assert not is_price_report("Reliance goes ahead with Rs 12,000 crore bond issue amid rising borrowing costs")
    assert is_price_report("Infosys was the only stock in the list trading lower, at Rs 1,009.80, down 0.55%.")


def test_same_sentences_under_different_titles_count_once():
    s = "Executive Vice President, Reliance Industries Ltd. was re-elected as Vice President at AMAI."
    base = {"ticker": "RELIANCE.NS", "sentences": s, "score": 0.07, "label": "neutral",
            "published_at": "2026-09-29T04:00:00Z"}
    df = pd.DataFrame([{**base, "title": "AMAI elects new board"},
                       {**base, "title": "Marketing body picks leaders"},
                       {**base, "title": "AMAI AGM held in Delhi"}])
    assert len(drop_syndicated(df)) == 1


def test_score_news_excludes_price_reports():
    base = {"ticker": "RELIANCE.NS", "published_at": "2026-09-29T04:00:00Z", "label": "negative"}
    df = pd.DataFrame([{**base, "title": "a", "sentences": "x", "score": -0.9, "score_news": None},
                       {**base, "title": "b", "sentences": "y", "score": 0.8, "score_news": 0.8}])
    assert abs(daily_sentiment(df).mean_score.iloc[0] - (-0.05)) < 1e-9
    assert daily_sentiment(df, score_col="score_news").n_articles.iloc[0] == 1


def test_module21_database_gets_new_columns(tmp_path):
    p = tmp_path / "old.db"
    with sqlite3.connect(p) as c:
        c.execute("CREATE TABLE entity_sentiment (article_id TEXT, ticker TEXT, model TEXT, reason TEXT, "
                  "n_sentences INTEGER, sentences TEXT, positive REAL, negative REAL, neutral REAL, label TEXT, "
                  "score REAL, scored_at TEXT, PRIMARY KEY (article_id, ticker, model))")
    db.init_db(p)
    with sqlite3.connect(p) as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(entity_sentiment)")}
    assert {"score_news", "n_price_sentences"} <= cols


def test_fundamental_moves_are_not_price_reports():
    assert not is_price_report("Infosys Q3 profit rises 12%, beats estimates")
    assert not is_price_report("Axis Bank NPAs rise sharply")
    assert not is_price_report("ICICI Bank net interest income jumps 20%")
    assert is_price_report("HDFC Bank shares dip as Q2 results near")
    assert is_price_report("ITC market cap slips below Rs 3.4 lakh crore")
