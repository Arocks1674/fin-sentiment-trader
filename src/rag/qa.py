"""Retrieval-augmented question answering over the stored news.

Flow: question -> detect which stocks it is about -> retrieve the k most similar
news items (filtered to those stocks and an optional date range) -> the LLM
answers ONLY from those items and cites them as [1], [2]...

Guardrails against made-up answers:
  - if retrieval returns nothing, we answer "no news found" without calling the LLM
  - the prompt forbids outside knowledge and requires a citation per claim
  - citations in the answer are checked against the numbers we supplied
"""
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from src.rag.corpus import ticker_key
from src.sentiment.entities import ENTITIES, _compiled

PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You answer questions about Indian listed companies using ONLY the numbered news items provided. "
     "Rules: (1) Every factual sentence must end with the citation(s) it relies on, like [2] or [1][3]. "
     "(2) Do not use outside knowledge, even if you know the answer. "
     "(3) If the items do not answer the question, say exactly what is missing. "
     "(4) Mention dates when they matter; archive items end in mid-2020. "
     "(5) This is information, not investment advice; never recommend buying or selling."),
    ("human", "News items:\n{context}\n\nQuestion: {question}"),
])

NO_NEWS = "I couldn't find any stored news relevant to that question."


@dataclass
class Answer:
    text: str
    sources: list[Document] = field(default_factory=list)
    tickers: list[str] = field(default_factory=list)
    invalid_citations: list[int] = field(default_factory=list)
    since: str | None = None


def tickers_in(question: str) -> list[str]:
    """Stocks named in the question, using the same entity rules as the sentiment pipeline."""
    found = []
    for t in ENTITIES:
        name_re, _, excl = _compiled(t)
        q = excl.sub(" ", question) if excl else question
        if name_re.search(q):
            found.append(t)
    return found


def build_filter(tickers: list[str], since: str | None = None, until: str | None = None) -> dict | None:
    clauses = []
    if tickers:
        ors = [{ticker_key(t): True} for t in tickers]
        clauses.append(ors[0] if len(ors) == 1 else {"$or": ors})
    if since:
        clauses.append({"date": {"$gte": int(since.replace("-", ""))}})
    if until:
        clauses.append({"date": {"$lte": int(until.replace("-", ""))}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def format_context(docs: list[Document]) -> str:
    lines = []
    for i, d in enumerate(docs, 1):
        m = d.metadata
        lines.append(f"[{i}] ({m.get('date_iso', '')}, {m.get('source', '')}) {d.page_content}")
    return "\n".join(lines)


def check_citations(text: str, n_sources: int) -> list[int]:
    """Citation numbers in the answer that do not match any supplied item."""
    cited = {int(x) for x in re.findall(r"\[(\d+)\]", text)}
    return sorted(c for c in cited if c < 1 or c > n_sources)


RECENT = re.compile(r"(?i)\b(recent|recently|latest|lately|this (?:week|month|quarter)|today|yesterday|now|currently)\b")
RECENT_DAYS = 60


def default_since(question: str, today: date | None = None) -> str | None:
    """Similarity search has no sense of time: 'recently' must become a date filter."""
    if RECENT.search(question):
        return str((today or date.today()) - timedelta(days=RECENT_DAYS))
    return None


def reply_text(reply) -> str:
    """Plain answer text from a chat reply.

    Newer Gemini models return content as a list of parts (text plus signed 'thought'
    blocks); only the text parts are the answer.
    """
    content = reply.content
    if isinstance(content, str):
        return content
    parts = []
    for part in content or []:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict) and part.get("type") == "text":
            parts.append(part.get("text", ""))
    return "".join(parts).strip()


def answer(question: str, vectorstore, llm, k: int = 6, since: str | None = None,
           until: str | None = None, tickers: list[str] | None = None) -> Answer:
    tickers = tickers if tickers is not None else tickers_in(question)
    since = since or default_since(question)
    flt = build_filter(tickers, since, until)
    docs = vectorstore.similarity_search(question, k=k, filter=flt)
    if not docs:
        return Answer(NO_NEWS, [], tickers, since=since)
    msg = PROMPT.format_messages(context=format_context(docs), question=question)
    text = reply_text(llm.invoke(msg))
    return Answer(text, docs, tickers, check_citations(text, len(docs)), since)
