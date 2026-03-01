# ============================================================
# wave_analyzer.py - 파동 분석 엔진 (StockAI 방법론 + 확장)
# ============================================================
import pandas as pd
import numpy as np
from config import (
    WAVE_STRONG_UP, WAVE_EARLY_UP, WAVE_TRANSITION, WAVE_GENERAL_UP
)


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series):
    ema12 = _ema(series, 12)
    ema26 = _ema(series, 26)
    macd  = ema12 - ema26
    signal = _ema(macd, 9)
    return macd, signal, macd - signal


def _bollinger(series: pd.Series, window: int = 20):
    mid  = series.rolling(window).mean()
    std  = series.rolling(window).std()
    return mid + 2*std, mid, mid - 2*std


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    OHLCV DataFrame에 기술적 지표 컬럼 추가.
    필수 입력 컬럼: close, volume
    """
    df = df.copy()
    close = df["close"]
    vol   = df["volume"]

    # 이동평균선
    df["ma20"]  = close.rolling(20).mean()
    df["ma50"]  = close.rolling(50).mean()
    df["ma200"] = close.rolling(200).mean()

    # RSI
    df["rsi"] = _rsi(close)

    # MACD
    df["macd"], df["macd_signal"], df["macd_hist"] = _macd(close)

    # 볼린저밴드
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = _bollinger(close)

    # 거래량 이동평균
    df["vol_ma20"] = vol.rolling(20).mean()
    df["vol_ratio"] = vol / df["vol_ma20"]

    # 52주 위치 (0~100%)
    high52 = close.rolling(252).max()
    low52  = close.rolling(252).min()
    df["pos_52w"] = (close - low52) / (high52 - low52 + 1e-9) * 100

    # 20일 수익률
    df["ret_20d"] = close.pct_change(20) * 100

    return df


def classify_wave(df: pd.DataFrame) -> dict:
    """
    최신 행 기준 파동 단계 분류.
    반환: {wave_stage, wave_score, wave_label, detail}
    """
    if df.empty or len(df) < 60:
        return {
            "wave_stage": "데이터부족", "wave_score": 50,
            "wave_label": "분석불가",   "detail": {}
        }

    r = df.iloc[-1]
    detail = {
        "ma20":      round(r.get("ma20",  0), 0),
        "ma50":      round(r.get("ma50",  0), 0),
        "ma200":     round(r.get("ma200", 0), 0),
        "rsi":       round(r.get("rsi",   50), 1),
        "pos_52w":   round(r.get("pos_52w", 50), 1),
        "vol_ratio": round(r.get("vol_ratio", 1.0), 2),
        "ret_20d":   round(r.get("ret_20d", 0), 2),
        "macd_hist": round(r.get("macd_hist", 0), 2),
    }

    ma20, ma50, ma200 = detail["ma20"], detail["ma50"], detail["ma200"]
    rsi  = detail["rsi"]
    pos  = detail["pos_52w"]
    vr   = detail["vol_ratio"]
    ret  = detail["ret_20d"]

    # ── 2단계 중기 (Strong Uptrend) ─────────────────────
    if (ma20 > ma50 > ma200
            and 60 <= pos <= 92
            and vr >= 1.3
            and 55 <= rsi <= 78
            and ret >= 10):
        return {"wave_stage": "2단계_중기", "wave_score": WAVE_STRONG_UP,
                "wave_label": "🚀 강한 상승추세 (최적 보유 구간)", "detail": detail}

    # ── 2단계 초기 (Early Uptrend) ──────────────────────
    if (ma20 > ma50
            and 40 <= pos <= 76
            and vr >= 1.2
            and 48 <= rsi <= 70):
        return {"wave_stage": "2단계_초기", "wave_score": WAVE_EARLY_UP,
                "wave_label": "📈 상승 초기 (이상적 진입 구간)", "detail": detail}

    # ── 1→2단계 전환 (Transition) ───────────────────────
    if (abs(ma20 - ma50) / (ma50 + 1e-9) < 0.03   # 수렴
            and 25 <= pos <= 62
            and 45 <= rsi <= 66):
        return {"wave_stage": "전환구간", "wave_score": WAVE_TRANSITION,
                "wave_label": "🔄 추세 전환 시도 (선제 매수 고려)", "detail": detail}

    # ── 일반 상승 ────────────────────────────────────────
    if ma20 > ma50 and 30 <= pos <= 72:
        return {"wave_stage": "일반상승", "wave_score": WAVE_GENERAL_UP,
                "wave_label": "📊 일반 상승 흐름", "detail": detail}

    # ── 하락/조정 ────────────────────────────────────────
    if ma20 < ma50 and rsi < 45:
        return {"wave_stage": "하락추세", "wave_score": 40,
                "wave_label": "⚠️ 하락 추세 (매수 주의)", "detail": detail}

    # ── 과열 ─────────────────────────────────────────────
    if rsi > 78 and pos > 90:
        return {"wave_stage": "과열구간", "wave_score": 50,
                "wave_label": "🔥 과열 구간 (차익 실현 고려)", "detail": detail}

    return {"wave_stage": "중립", "wave_score": 55,
            "wave_label": "➖ 방향성 불명확 (관망)", "detail": detail}


def get_support_resistance(df: pd.DataFrame, lookback: int = 60) -> dict:
    """최근 N일 지지선/저항선 계산."""
    if len(df) < lookback:
        return {}
    sub = df.tail(lookback)
    return {
        "resistance": round(sub["high"].max(), 0) if "high" in sub else None,
        "support":    round(sub["low"].min(),  0) if "low"  in sub else None,
        "pivot":      round((sub["high"].max() + sub["low"].min() +
                             sub["close"].iloc[-1]) / 3, 0),
    }
