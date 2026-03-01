# ============================================================
# data_collector.py - 실시간/과거 데이터 수집 (yfinance 기반)
# ============================================================
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from stock_manager import ticker_to_yf
import warnings
warnings.filterwarnings("ignore")


# ── 기본 주가 데이터 ─────────────────────────────────────

def fetch_price_history(ticker: str, market: str = "KOSPI", period: str = "2y") -> pd.DataFrame:
    """
    yfinance로 주가 히스토리 수집.
    반환 컬럼: open, high, low, close, volume (소문자)
    """
    yf_ticker = ticker_to_yf(ticker, market)
    try:
        df = yf.download(yf_ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c.lower() for c in df.columns]
        df.index.name = "date"
        return df
    except Exception as e:
        print(f"[데이터수집 오류] {ticker}: {e}")
        return pd.DataFrame()


def fetch_fundamentals(ticker: str, market: str = "KOSPI") -> dict:
    """
    yfinance Info에서 펀더멘털 지표 추출.
    반환 dict 키: current_price, market_cap, per, pbr, roe, eps,
                  bps, revenue, net_income, operating_income,
                  total_debt, total_equity, free_cashflow,
                  dividend_yield, sector, name, beta
    """
    yf_ticker = ticker_to_yf(ticker, market)
    try:
        info = yf.Ticker(yf_ticker).info
    except Exception:
        info = {}

    def _get(key, default=None):
        v = info.get(key, default)
        return v if v not in [None, "N/A", float("inf"), float("-inf")] else default

    # 직접 EPS/BPS 계산 보조
    shares = _get("sharesOutstanding") or _get("impliedSharesOutstanding")
    net_income = _get("netIncomeToCommon")
    book_val = _get("bookValue")  # per share
    eps_raw = _get("trailingEps")
    current = _get("currentPrice") or _get("regularMarketPrice")

    # PER, PBR 직접 계산 (info 값 우선, 없으면 계산)
    per = _get("trailingPE")
    if per is None and eps_raw and current:
        per = round(current / eps_raw, 2) if eps_raw > 0 else None

    pbr = _get("priceToBook")
    if pbr is None and book_val and current:
        pbr = round(current / book_val, 2) if book_val > 0 else None

    roe = _get("returnOnEquity")
    if roe:
        roe = round(roe * 100, 2)  # % 단위

    return {
        "name":             _get("longName") or _get("shortName", ticker),
        "sector":           _get("sector", "기타"),
        "current_price":    current,
        "market_cap":       _get("marketCap"),
        "per":              per,
        "pbr":              pbr,
        "roe":              roe,
        "eps":              eps_raw,
        "bps":              book_val,
        "revenue":          _get("totalRevenue"),
        "net_income":       _get("netIncomeToCommon"),
        "operating_income": _get("operatingCashflow"),  # 근사
        "total_debt":       _get("totalDebt"),
        "total_equity":     _get("totalStockholderEquity"),
        "free_cashflow":    _get("freeCashflow"),
        "dividend_yield":   (_get("dividendYield") or 0) * 100,
        "beta":             _get("beta", 1.0),
        "shares":           shares,
        "52w_high":         _get("fiftyTwoWeekHigh"),
        "52w_low":          _get("fiftyTwoWeekLow"),
        "target_price":     _get("targetMeanPrice"),   # 애널리스트 컨센서스
    }


def fetch_financial_history(ticker: str, market: str = "KOSPI") -> dict:
    """
    최근 4개 연도 재무제표 수집.
    반환: {"income": df, "balance": df, "cashflow": df}
    """
    yf_ticker = ticker_to_yf(ticker, market)
    try:
        t = yf.Ticker(yf_ticker)
        return {
            "income":    t.financials,
            "balance":   t.balance_sheet,
            "cashflow":  t.cashflow,
        }
    except Exception:
        return {"income": pd.DataFrame(), "balance": pd.DataFrame(), "cashflow": pd.DataFrame()}


def fetch_current_price(ticker: str, market: str = "KOSPI") -> float | None:
    """현재가만 빠르게 수집."""
    yf_ticker = ticker_to_yf(ticker, market)
    try:
        data = yf.download(yf_ticker, period="1d", progress=False, auto_adjust=True)
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception:
        pass
    return None
