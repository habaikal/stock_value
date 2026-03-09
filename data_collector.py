# ============================================================
# data_collector.py - 다중 소스 데이터 수집 (yfinance + FinanceDataReader)
# ============================================================
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import logging
from datetime import datetime, timedelta
from stock_manager import ticker_to_yf
from config import TIMEOUT_SECONDS, RETRY_ATTEMPTS
import warnings
warnings.filterwarnings("ignore")

# ── 로깅 설정 ──────────────────────────────────────────
logger = logging.getLogger("StockAI.DataCollector")

# ── 한국 API 추가 임포트 ───────────────────────────────
try:
    from pykrx import stock as pykrx_stock  # 한국거래소 공시 API
    HAS_PYKRX = True
except ImportError:
    HAS_PYKRX = False
    logger.warning("pykrx 설치 안 됨. `pip install pykrx` 추천")

try:
    import FinanceDataReader as fdr
    HAS_FDR = True
except ImportError:
    HAS_FDR = False
    logger.warning("FinanceDataReader 설치 안 됨. `pip install financedata reader` 추천")


# ── 기본 주가 데이터 ─────────────────────────────────────

def fetch_price_history(ticker: str, market: str = "KOSPI", period: str = "2y") -> pd.DataFrame:
    """
    한국 주식: FinanceDataReader로 수집 (더 정확)
    미국 주식: yfinance로 수집.
    반환 컬럼: open, high, low, close, volume (소문자)
    """
    if market.lower() in ["kospi", "kosdaq"]:
        # 한국 우선 (FDR 또는 yfinance)
        df = fetch_korea_price_with_fdr(ticker, period)
        if not df.empty:
            logger.info(f"한국 주식 {ticker} 수집 완료 ({len(df)} 행)")
            return df
    
    # 폴백: yfinance
    yf_ticker = ticker_to_yf(ticker, market)
    try:
        df = yf.download(yf_ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            logger.warning(f"{ticker} yfinance 데이터 없음")
            return pd.DataFrame()
        df.columns = [c.lower() for c in df.columns]
        df.index.name = "date"
        logger.info(f"yfinance {ticker} 수집 완료 ({len(df)} 행)")
        return df
    except Exception as e:
        logger.error(f"데이터 수집 오류 ({ticker}): {e}")
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


# ──────────────────────────────────────────────────────────────
# 한국 시장 특화: 외국인/기관 매매 추적
# ──────────────────────────────────────────────────────────────

def fetch_foreign_institutional_trades(ticker: str, days: int = 60) -> dict:
    """
    한국 주식의 외국인/기관 순매수 추적 (pykrx 기반).
    반환: {"date": [...], "foreign_net": [...], "institutional_net": [...], ...}
    """
    if not HAS_PYKRX:
        logger.warning("pykrx 없음. 외국인/기관 데이터 수집 불가")
        return {"error": "pykrx 필요"}
    
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        
        # 티커 정규화 (예: 000660 형태)
        clean_ticker = ticker.replace(".KS", "").replace(".KQ", "")
        if not clean_ticker.isdigit():
            clean_ticker = clean_ticker.zfill(6)
        
        df = pykrx_stock.get_market_trading_volume_by_investor(
            fromdate=start_date, todate=end_date, ticker=clean_ticker
        )
        
        if df.empty:
            return {"error": f"No data for {ticker}"}
        
        return {
            "date": df.index.strftime("%Y-%m-%d").tolist(),
            "foreign_net": df.get("외국인", [0]).tolist(),
            "institutional_net": df.get("기관", [0]).tolist(),
            "individual_net": df.get("개인", [0]).tolist(),
            "trend": "상승" if df.get("외국인", [0]).iloc[-1] > 0 else "하락",
            "latest": df.iloc[-1].to_dict() if not df.empty else {}
        }
    except Exception as e:
        logger.error(f"외국인/기관 데이터 수집 실패 ({ticker}): {e}")
        return {"error": str(e)}


def fetch_korea_price_with_fdr(ticker: str, period: str = "2y") -> pd.DataFrame:
    """
    FinanceDataReader로 한국 주식 수집 (yfinance보다 정확함).
    """
    if not HAS_FDR:
        logger.warning("FinanceDataReader 없음. yfinance 사용")
        return fetch_price_history(ticker, market="KOSPI", period=period)
    
    try:
        clean_ticker = ticker.replace(".KS", "").replace(".KQ", "").upper()
        
        # 기간 계산
        end_date = datetime.now()
        if period == "2y":
            start_date = end_date - timedelta(days=730)
        elif period == "5y":
            start_date = end_date - timedelta(days=1825)
        else:  # "1y"
            start_date = end_date - timedelta(days=365)
        
        df = fdr.DataReader(clean_ticker, start=start_date.date(), end=end_date.date())
        
        if df.empty:
            return pd.DataFrame()
        
        # 컬럼 정규화
        df.columns = [c.lower() for c in df.columns]
        df.index.name = "date"
        
        logger.info(f"FinanceDataReader로 {ticker} 수집 성공 ({len(df)} 행)")
        return df
        
    except Exception as e:
        logger.warning(f"FinanceDataReader 실패 ({ticker}): {e}. yfinance로 대체")
        return fetch_price_history(ticker, market="KOSPI", period=period)


def fetch_dividend_history(ticker: str) -> list[dict]:
    """
    배당금 이력 수집.
    반환: [{"date": "YYYY-MM-DD", "amount": 1000, "yield": 3.5}, ...]
    """
    try:
        t = yf.Ticker(ticker_to_yf(ticker, "KOSPI"))
        divs = t.dividends
        
        if divs.empty:
            return []
        
        result = []
        for date, div in divs.items():
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "amount": float(div),
                "yield": None  # 나중에 채움
            })
        
        return result[-10:]  # 최근 10개
        
    except Exception as e:
        logger.warning(f"배당금 수집 실패 ({ticker}): {e}")
        return []


def fetch_earnings_calendar(sector: str = "all") -> pd.DataFrame:
    """
    실적 발표 예정 일정 조회 (향후 30일).
    반환: DataFrame with ["date", "company", "sector"]
    """
    # 실제로는 외부 API 활용 필요 (naver finance 크롤링 등)
    logger.info(f"실적 캘린더 조회 ({sector})")
    return pd.DataFrame(columns=["date", "company", "sector"])


def estimate_foreign_position(ticker: str, current_price: float, 
                             recent_foreign_trades: dict) -> dict:
    """
    외국인 보유 황금비 추정 (최근 매매 추세 기반).
    """
    try:
        if "error" in recent_foreign_trades:
            return {"estimate": None, "signal": "데이터없음"}
        
        latest = recent_foreign_trades.get("latest", {})
        trend = recent_foreign_trades.get("trend", "")
        
        # 간단한 휴리스틱: 최근 매수 추세 → 긍정신호
        if trend == "상승" and latest.get("외국인", 0) > 0:
            signal = "긍정 (외자 매수중)"
            strength = min(100, 60 + abs(latest.get("외국인", 0)) / 1_000_000_000 * 10)
        elif trend == "하락" and latest.get("외국인", 0) < 0:
            signal = "부정 (외자 매도중)"
            strength = max(0, 40 - abs(latest.get("외국인", 0)) / 1_000_000_000 * 10)
        else:
            signal = "중립"
            strength = 50
        
        return {
            "current_price": current_price,
            "signal": signal,
            "strength": round(strength, 1),  # 0~100
        }
    except Exception as e:
        logger.error(f"외국인 포지션 추정 실실: {e}")
        return {"estimate": None, "signal": "오류"}