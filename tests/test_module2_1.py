"""Tests for module 2.1: entity relevance, source filter, syndicated duplicates.
The cases are real headlines from the first live run."""
import pandas as pd
import pytest

import config
import score
from src.sentiment.aggregate import daily_sentiment
from src.sentiment.entities import ENTITIES, normalize_title, relevant_sentences
from src.storage import db


def test_every_configured_ticker_has_entity_rules():
    assert set(config.TICKERS.values()) <= set(ENTITIES)


def test_sector_title_but_company_in_description():
    rel = relevant_sentences(
        "INFY.NS",
        "IT Stocks Rally: Coforge, Mphasis, Persistent Systems Share Price Rallies In Green Ahead Of Accenture Q4",
        "Infosys was the only stock in the list trading lower, at Rs 1,009.80, down 0.55%. "
        "Its intraday high remained marginally below the previous close.")
    assert rel.reason == "ok"
    assert rel.sentences == ["Infosys was the only stock in the list trading lower, at Rs 1,009.80, down 0.55%."]


@pytest.mark.parametrize("title", [
    "Exports, rising power demand to support manufacturing growth despite rural weakness: ICICI Bank",
    "Rupee to weaken further, according to ICICI Bank",
    "ICICI Bank economists see repo rate cut in December",
])
def test_company_as_source_is_dropped(title):
    assert relevant_sentences("ICICIBANK.NS", title, "").reason == "source_only"


def test_company_as_subject_is_kept_even_with_attribution():
    rel = relevant_sentences("TCS.NS", "Tata Consultancy Services wins $1bn deal, says TCS", "")
    assert rel.reason == "ok"


@pytest.mark.parametrize("ticker,title", [
    ("ICICIBANK.NS", "ICICI Prudential Life Q2 profit jumps 20%"),
    ("ITC.NS", "ITC Hotels shares surge after listing"),
    ("HDFCBANK.NS", "HDFC Life premium growth slows"),
    ("LT.NS", "L&T Finance raises Rs 500 crore"),
    ("RELIANCE.NS", "Reliance Power shares hit upper circuit"),
])
def test_sister_companies_are_excluded(ticker, title):
    assert relevant_sentences(ticker, title, "").reason == "not_mentioned"


def test_acronyms_are_whole_word_and_case_sensitive():
    assert relevant_sentences("ITC.NS", "ITC shares fall 3%", "").reason == "ok"
    assert relevant_sentences("ITC.NS", "Pitch perfect: startup raises funds", "").reason == "not_mentioned"
    assert relevant_sentences("TCS.NS", "tcs is a lowercase word here", "").reason == "not_mentioned"


def test_syndicated_copies_counted_once():
    base = {"ticker": "ICICIBANK.NS", "score": 0.9, "label": "positive"}
    scored = pd.DataFrame([
        {**base, "title": "ICICI Bank Q2 profit rises 15% - Moneycontrol", "published_at": "2026-09-29T04:00:00Z"},
        {**base, "title": "ICICI Bank Q2 profit rises 15% | Economic Times", "published_at": "2026-09-29T05:00:00Z"},
        {**base, "title": "ICICI Bank Q2 profit rises 15%", "published_at": "2026-09-29T06:00:00Z"},
    ])
    assert daily_sentiment(scored).n_articles.tolist() == [1]
    assert daily_sentiment(scored, dedupe=False).n_articles.tolist() == [3]


def test_normalize_title_keeps_real_differences():
    assert normalize_title("ICICI Bank Q2 profit rises") != normalize_title("ICICI Bank Q2 profit falls")


class FakeScorer:
    """Stands in for FinBERT: 'lower'/'fall' -> negative, everything else positive."""
    def score(self, texts):
        out = []
        for t in texts:
            neg = any(w in t.lower() for w in ("lower", "fall"))
            p, n = (0.05, 0.9) if neg else (0.9, 0.05)
            out.append({"positive": p, "negative": n, "neutral": 0.05,
                        "label": "negative" if neg else "positive", "score": p - n})
        return out


def test_score_pipeline_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(score, "FinBertScorer", FakeScorer)
    db.init_db(config.DB_PATH)
    art = lambda url, title, desc: {"title": title, "description": desc, "url": url,
                                    "published_at": "2026-09-29T04:00:00Z"}
    db.upsert_articles(config.DB_PATH, "INFY.NS", [art("u1", "IT Stocks Rally in green",
                                                       "Infosys was the only stock trading lower.")])
    db.upsert_articles(config.DB_PATH, "ICICIBANK.NS", [art("u2", "Exports to support growth: ICICI Bank", "")])

    score.score_new_pairs()
    kept = db.load_entity_scored(config.DB_PATH, score.MODEL_NAME)
    assert kept.ticker.tolist() == ["INFY.NS"] and kept.score.iloc[0] < 0      # company-specific, negative
    everything = db.load_entity_scored(config.DB_PATH, score.MODEL_NAME, relevant_only=False)
    assert set(everything.reason) == {"ok", "source_only"}

    score.score_new_pairs()                                                     # idempotent
    assert len(db.load_entity_scored(config.DB_PATH, score.MODEL_NAME, relevant_only=False)) == 2
