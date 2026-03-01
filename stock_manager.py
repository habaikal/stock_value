# ============================================================
# stock_manager.py - 종목 CSV 저장·조회·삭제 관리
# ============================================================
import pandas as pd
import os
from datetime import datetime
from config import WATCHLIST_CSV


def _load() -> pd.DataFrame:
    """watchlist.csv 로드. 없으면 빈 DataFrame 반환."""
    if os.path.exists(WATCHLIST_CSV):
        df = pd.read_csv(WATCHLIST_CSV, dtype=str)
        # 필수 컬럼 보정
        for col in ["ticker", "name", "market", "added_date", "memo"]:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame(columns=["ticker", "name", "market", "added_date", "memo"])


def _save(df: pd.DataFrame):
    """DataFrame → watchlist.csv 저장."""
    df.to_csv(WATCHLIST_CSV, index=False, encoding="utf-8-sig")


# ── 공개 API ─────────────────────────────────────────────

def add_stock(ticker: str, name: str = "", market: str = "KOSPI", memo: str = "") -> dict:
    """
    종목 추가. 한국어 6자리 및 미국 티커(AAPL 등) 섞어 사용가능.
    반환: {"status": "added"|"exists", "ticker": ..., "name": ...}
    """
    ticker = ticker.strip().upper()
    
    if market.upper() in ["KOSPI", "KOSDAQ"]:
        # 한국 주식 처리
        raw = ticker.replace(".KS", "").replace(".KQ", "").replace(".KR", "")
        if raw.isdigit():
            raw = raw.zfill(6)
    else:
        # 글로벌 주식 처리 (US)
        raw = ticker

    df = _load()
    if raw in df["ticker"].values:
        return {"status": "exists", "ticker": raw, "name": name}

    new_row = pd.DataFrame([{
        "ticker":     raw,
        "name":       name,
        "market":     market,
        "added_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "memo":       memo,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    _save(df)
    return {"status": "added", "ticker": raw, "name": name}


def remove_stock(ticker: str) -> bool:
    """종목 삭제. 성공하면 True."""
    ticker = ticker.strip()
    df = _load()
    before = len(df)
    df = df[df["ticker"] != ticker]
    if len(df) < before:
        _save(df)
        return True
    return False


def get_watchlist() -> pd.DataFrame:
    """전체 관심 종목 목록 반환."""
    return _load()


def update_name(ticker: str, name: str):
    """종목명 업데이트 (데이터 수집 후 자동 호출)."""
    ticker = ticker.strip()
    df = _load()
    mask = df["ticker"] == ticker
    if mask.any():
        df.loc[mask, "name"] = name
        _save(df)


def ticker_to_yf(ticker: str, market: str = "KOSPI") -> str:
    """티커를 yfinance 형식으로 변환 (KOSPI/KOSDAQ 자동 접미사 적용, US는 원형)."""
    raw = ticker.strip()
    if market.upper() == "KOSPI":
        return raw.zfill(6) + ".KS"
    elif market.upper() == "KOSDAQ":
        return raw.zfill(6) + ".KQ"
    else:  # US or GLOBAL
        return raw
