"""Turn stored news into LangChain Documents for the vector store.

Two sources, one document per story:
  live    - GNews articles (title + description), with source and URL
  archive - Times of India headlines 2001-2020 (headline only, no URL)

Metadata is kept flat because Chroma only filters on scalar values:
  - one boolean key per stock ("INFY": True) so a question about Infosys can be
    filtered to Infosys news even when an article mentions several companies
  - date as an int (20260929) so date ranges can be filtered with $gte / $lte
"""
import hashlib

import pandas as pd
from langchain_core.documents import Document

from src.storage import db


def ticker_key(ticker: str) -> str:
    return ticker.split(".")[0]          # "INFY.NS" -> "INFY"


def _date_int(iso: str) -> int:
    return int(str(iso)[:10].replace("-", ""))


def live_documents(db_path) -> list[Document]:
    arts = db.load_articles(db_path)
    if arts.empty:
        return []
    docs = []
    for aid, g in arts.groupby("id", sort=False):
        a = g.iloc[0]
        text = a["title"] if not a["description"] else f"{a['title']}. {a['description']}"
        meta = {"kind": "live", "date": _date_int(a["published_at"]), "date_iso": str(a["published_at"])[:10],
                "source": a["source"] or "", "url": a["url"], "title": a["title"]}
        meta.update({ticker_key(t): True for t in g["ticker"].unique()})
        docs.append(Document(page_content=text, metadata=meta, id=f"live-{aid}"))
    return docs


def archive_documents(db_path) -> list[Document]:
    h = db.load_hist_headlines(db_path)
    if h.empty:
        return []
    docs = []
    for (date, headline), g in h.groupby(["date", "headline"], sort=False):
        hid = hashlib.sha1(f"{date}|{headline}".encode("utf-8")).hexdigest()
        meta = {"kind": "archive", "date": _date_int(date), "date_iso": date,
                "source": "Times of India", "url": "", "title": headline}
        meta.update({ticker_key(t): True for t in g["ticker"].unique()})
        docs.append(Document(page_content=headline, metadata=meta, id=f"arch-{hid}"))
    return docs


def all_documents(db_path) -> list[Document]:
    return live_documents(db_path) + archive_documents(db_path)
