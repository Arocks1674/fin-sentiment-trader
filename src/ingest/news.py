"""News ingestion from the GNews REST API (https://gnews.io/docs).

Free tier limits (check your dashboard): ~100 requests/day, max 10 articles per
request, and only recent articles. That is why this module is for *live*
ingestion only; the backtest uses a separate historical dataset.
"""
import logging
import time

import requests

GNEWS_URL = "https://gnews.io/api/v4/search"
log = logging.getLogger(__name__)


class NewsAPIError(RuntimeError):
    pass


def fetch_gnews(query: str, api_key: str, max_results: int = 10,
                lang: str = "en", country: str = "in", retries: int = 2,
                session: requests.Session | None = None) -> list[dict]:
    """Return a list of normalized article dicts for one search query."""
    if not api_key:
        raise NewsAPIError("GNEWS_API_KEY is not set. Add it to your .env file.")

    params = {"q": f'"{query}"', "lang": lang, "country": country,
              "max": max_results, "apikey": api_key}
    http = session or requests

    for attempt in range(retries + 1):
        resp = http.get(GNEWS_URL, params=params, timeout=15)
        if resp.status_code == 429 and attempt < retries:      # rate limited
            wait = 2 ** attempt * 5
            log.warning("Rate limited on %r, retrying in %ss", query, wait)
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            raise NewsAPIError(f"GNews returned {resp.status_code}: {resp.text[:200]}")
        break

    return [normalize(a) for a in resp.json().get("articles", [])]


def normalize(a: dict) -> dict:
    return {
        "title": (a.get("title") or "").strip(),
        "description": (a.get("description") or "").strip(),
        "content": (a.get("content") or "").strip(),
        "source": (a.get("source") or {}).get("name"),
        "url": a.get("url"),
        "published_at": a.get("publishedAt"),
    }
