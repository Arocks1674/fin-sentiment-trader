"""Performance metrics on daily returns."""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def sharpe(r: pd.Series, rf_annual: float = 0.0) -> float:
    """Annualised Sharpe ratio. rf_annual: risk-free rate per year (e.g. 0.065 for Indian T-bills)."""
    ex = r - rf_annual / TRADING_DAYS
    sd = ex.std()
    return float(ex.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")


def max_drawdown(r: pd.Series) -> float:
    """Largest peak-to-trough fall of the equity curve, as a negative fraction."""
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def cagr(r: pd.Series) -> float:
    years = len(r) / TRADING_DAYS
    return float((1 + r).prod() ** (1 / years) - 1) if years > 0 else float("nan")


def summary(r: pd.Series, rf_annual: float = 0.0) -> dict:
    return {"CAGR_%": cagr(r) * 100, "Sharpe": sharpe(r, rf_annual),
            "MaxDD_%": max_drawdown(r) * 100}
