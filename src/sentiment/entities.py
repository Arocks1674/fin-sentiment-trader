"""Which sentences of an article are actually about a given company?

Three problems found in the first real run, and the rule for each:

1. Sister companies share a name ("ICICI Prudential" is not "ICICI Bank").
   -> EXCLUDE phrases are removed before matching.
2. The company is the SOURCE, not the subject
   ("Exports ... to support manufacturing growth: ICICI Bank").
   -> source patterns (trailing ": Name", "according to Name",
      "Name economists/research/report") do not count as a mention.
3. The title can be about the sector while the description is about the
   company ("IT stocks rally" / "Infosys was the only stock trading lower").
   -> we score only the sentences that mention the company.

These are deliberately simple, explainable rules. They will miss some cases;
an LLM relevance check (module 4) can handle the hard ones.
"""
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Entity:
    names: tuple[str, ...]                 # matched case-insensitively, whole words
    acronyms: tuple[str, ...] = ()         # matched case-SENSITIVELY, whole words (e.g. "ITC")
    exclude: tuple[str, ...] = field(default=())  # sister companies, removed before matching


ENTITIES: dict[str, Entity] = {
    "RELIANCE.NS": Entity(("Reliance Industries", "Reliance Jio", "Jio Platforms", "Reliance Retail", "Reliance"),
                          ("RIL",),
                          ("Reliance Power", "Reliance Infrastructure", "Reliance Infra", "Reliance Capital",
                           "Reliance Communications", "Reliance Home Finance", "Reliance General Insurance",
                           "Reliance Nippon", "Reliance Mutual Fund")),
    "HDFCBANK.NS": Entity(("HDFC Bank",), (),
                          ("HDFC Life", "HDFC AMC", "HDFC Asset Management", "HDFC Mutual Fund",
                           "HDFC Securities", "HDFC Ergo", "HDFC Credila")),
    "ICICIBANK.NS": Entity(("ICICI Bank",), (),
                           ("ICICI Prudential", "ICICI Lombard", "ICICI Securities", "ICICI Direct")),
    "INFY.NS": Entity(("Infosys",), ("INFY", "Infy")),
    "TCS.NS": Entity(("Tata Consultancy Services",), ("TCS",)),
    "KOTAKBANK.NS": Entity(("Kotak Mahindra Bank", "Kotak Bank", "Kotak Mahindra"), (),
                           ("Kotak Mahindra AMC", "Kotak Mutual Fund", "Kotak Life", "Kotak Securities",
                            "Kotak Alternate")),
    "LT.NS": Entity(("Larsen & Toubro", "Larsen and Toubro", "Larsen"), ("L&T",),
                    ("L&T Finance", "L&T Technology Services", "L&T Tech", "LTIMindtree", "L&T Mindtree",
                     "L&T Mutual Fund")),
    "HINDUNILVR.NS": Entity(("Hindustan Unilever",), ("HUL",)),
    "ITC.NS": Entity((), ("ITC",), ("ITC Hotels",)),
    "AXISBANK.NS": Entity(("Axis Bank",), (),
                          ("Axis Mutual Fund", "Axis AMC", "Axis Securities", "Axis Max Life", "Axis Finance")),
}

# Sentence boundary: . ! ? followed by whitespace and a capital letter / digit / quote.
# "Rs 1,009.80" is safe because the '.' is not followed by whitespace.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'‘“])")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text or "") if s.strip()]


def _alt(words) -> str:
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))


def _name_pattern(e: Entity) -> re.Pattern:
    parts = []
    if e.names:
        parts.append(rf"(?i:{_alt(e.names)})")
    if e.acronyms:
        parts.append(_alt(e.acronyms))
    # Custom word boundaries so "L&T" and "ITC" work and "ITC" does not match "ITCs" or "SITC".
    return re.compile(rf"(?<![\w&])(?:{'|'.join(parts)})(?![\w&])")


def _source_patterns(name_re: str) -> list[re.Pattern]:
    return [
        re.compile(rf":\s*(?:{name_re})\s*[.!]?\s*$"),                                 # "...growth: ICICI Bank"
        re.compile(rf"(?i:according to|as per|said|says|report by|research by|analysts at|economists at)\s+(?:{name_re})"),
        re.compile(rf"(?:{name_re})\s+(?i:economists?|research|securities research|analysts?|global markets)\b"),
    ]


_COMPILED: dict[str, tuple[re.Pattern, list[re.Pattern], re.Pattern | None]] = {}


def _compiled(ticker: str):
    if ticker not in _COMPILED:
        e = ENTITIES[ticker]
        name = _name_pattern(e)
        excl = re.compile(rf"(?i:{_alt(e.exclude)})") if e.exclude else None
        _COMPILED[ticker] = (name, _source_patterns(name.pattern), excl)
    return _COMPILED[ticker]


@dataclass
class Relevance:
    sentences: list[str]          # sentences about the company (what gets scored)
    reason: str                   # "ok" | "not_mentioned" | "source_only"


def relevant_sentences(ticker: str, title: str, description: str | None) -> Relevance:
    """Return the sentences of title + description that are about `ticker`."""
    if ticker not in ENTITIES:
        raise KeyError(f"No entity rules for {ticker}; add it to ENTITIES")
    name, sources, excl = _compiled(ticker)

    sentences = split_sentences(title) + split_sentences(description or "")
    keep, source_hits = [], 0
    for s in sentences:
        cleaned = excl.sub(" ", s) if excl else s
        if not name.search(cleaned):
            continue
        if any(p.search(cleaned) for p in sources):
            # Mentioned only as the source. Keep it if the company is ALSO named elsewhere
            # in the sentence as a subject, e.g. "ICICI Bank profit rises, says ICICI Bank".
            stripped = cleaned
            for p in sources:
                stripped = p.sub(" ", stripped)
            if not name.search(stripped):
                source_hits += 1
                continue
        keep.append(s)

    if keep:
        return Relevance(keep, "ok")
    return Relevance([], "source_only" if source_hits else "not_mentioned")


def normalize_title(title: str) -> str:
    """For spotting syndicated copies: lowercase, drop a trailing ' - Source', keep letters/digits."""
    t = re.sub(r"\s+[-|]\s+[^-|]{2,40}$", "", (title or "").strip())
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
