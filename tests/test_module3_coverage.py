"""Module 3 step 1: historical headline extraction (uses a tiny fake CSV, no download)."""
import pandas as pd

from src.ingest.historical import coverage, extract
from src.storage import db


def test_extract_keeps_business_company_headlines(tmp_path):
    csv = tmp_path / "h.csv"
    pd.DataFrame({
        "publish_date": ["20150105", "20150105", "20150106", "20160301", "20160301", "20160302"],
        "headline_category": ["business.india-business", "city.mumbai", "business.india-business",
                              "business.india-business", "business.india-business", "business.india-business"],
        "headline_text": [
            "Infosys Q3 profit rises 12%, beats estimates",            # keep; earnings news, NOT a price report
            "Infosys campus hosts cultural fest",                       # city section -> dropped
            "ICICI Prudential launches new fund",                        # sister company -> dropped
            "Reliance Industries to invest Rs 1 lakh crore in telecom",  # keep
            "Sensex falls; ICICI Bank, HDFC Bank, Infosys, TCS, ITC drag", # list -> dropped
            "Rupee to weaken, says ICICI Bank",                          # source only -> dropped
        ],
    }).to_csv(csv, index=False)

    df = extract(csv, ["INFY.NS", "ICICIBANK.NS", "RELIANCE.NS", "TCS.NS"], chunksize=2)
    assert sorted(zip(df.date, df.ticker)) == [("2015-01-05", "INFY.NS"), ("2016-03-01", "RELIANCE.NS")]
    assert not df.set_index("ticker").loc["INFY.NS", "price_report"]   # profit news, not a price move

    cov = coverage(df)
    assert cov.loc["INFY.NS", "2015"] == 1 and cov.loc["INFY.NS", "days_with_news"] == 1

    p = tmp_path / "t.db"
    db.init_db(p)
    assert db.save_hist_headlines(p, df) == 2
    assert db.save_hist_headlines(p, df) == 0          # idempotent
    assert len(db.load_hist_headlines(p, "INFY.NS")) == 1
