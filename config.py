"""Central configuration. Secrets come from a .env file, never from code."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# --- Secrets (set these in .env; see .env.example) ---
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")

# --- Storage ---
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "trader.db"))

# --- Universe: company name used as the news query -> Yahoo Finance ticker ---
TICKERS = {
    "Reliance Industries": "RELIANCE.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Infosys": "INFY.NS",
    "Tata Consultancy Services": "TCS.NS",
    "Kotak Mahindra Bank": "KOTAKBANK.NS",
    "Larsen & Toubro": "LT.NS",
    "Hindustan Unilever": "HINDUNILVR.NS",
    "ITC": "ITC.NS",
    "Axis Bank": "AXISBANK.NS",
}

# --- Ingestion ---
GNEWS_MAX_PER_QUERY = int(os.getenv("GNEWS_MAX_PER_QUERY", "10"))  # free tier caps at 10
REQUEST_PAUSE_SEC = float(os.getenv("REQUEST_PAUSE_SEC", "1.0"))    # be polite to the API
