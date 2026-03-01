# ============================================================
# config.py - 전역 설정 및 상수 관리
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ── 파일 경로 ─────────────────────────────────────────────
WATCHLIST_CSV   = "watchlist.csv"          # 종목 관심 리스트
ANALYSIS_CSV    = "analysis_results.csv"   # 분석 결과 캐시
PRICE_CSV       = "daily_prices.csv"       # 일별 시세 캐시

# ── 밸류에이션 가중치 (합계 = 1.0) ───────────────────────
WEIGHT_DCF        = 0.35   # 내재가치 (DCF)
WEIGHT_RELATIVE   = 0.25   # 상대가치 (PER/PBR)
WEIGHT_ASSET      = 0.15   # 자산가치
WEIGHT_EARNINGPOW = 0.15   # 수익력 가치
WEIGHT_WAVE       = 0.10   # 파동/모멘텀 조정

# ── 한국 시장 파라미터 ─────────────────────────────────
RISK_FREE_RATE    = 0.033   # 한국 10년물 국고채 수익률 (3.3%)
MARKET_RISK_PREM  = 0.075   # 한국 시장 위험 프리미엄 (7.5%)
TERMINAL_GROWTH   = 0.030   # 영구 성장률 (명목 GDP 3.0%)
KOREA_DISCOUNT    = 0.10    # 코리아 디스카운트 기본값

# ── 파동 분석 임계값 ──────────────────────────────────
WAVE_STRONG_UP    = 90      # 2단계 중기
WAVE_EARLY_UP     = 80      # 2단계 초기
WAVE_TRANSITION   = 70      # 1→2단계 전환
WAVE_GENERAL_UP   = 60      # 일반 상승

# ── 투자 판단 기준 (현재가 / 적정가) ────────────────────
SIGNAL_STRONG_BUY = 0.70    # 현재가 < 적정가×70% → Strong Buy
SIGNAL_BUY        = 0.85    # 현재가 < 적정가×85% → Buy
SIGNAL_HOLD_LOW   = 0.95    # 현재가 < 적정가×95% → Hold
SIGNAL_HOLD_HIGH  = 1.10    # 현재가 < 적정가×110% → Hold
SIGNAL_SELL       = 1.20    # 현재가 > 적정가×120% → Sell

# ── 산업 분류 및 기본 PER ────────────────────────────────
INDUSTRY_PER = {
    "반도체":       22, "전자":         18, "자동차":       8,
    "화학":         10, "정유":          8, "금융":         7,
    "바이오":       40, "2차전지":       25, "플랫폼":      30,
    "철강":          8, "통신":         12, "게임":         20,
    "건설":          8, "유통":         15, "기타":         13,
}
