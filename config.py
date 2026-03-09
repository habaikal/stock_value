# ============================================================
# config.py - 전역 설정 및 상수 관리
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ── 파일 경로 ─────────────────────────────────────────────
WATCHLIST_CSV      = "watchlist.csv"          # 종목 관심 리스트
ANALYSIS_CSV       = "analysis_results.csv"   # 분석 결과 캐시
PRICE_CSV          = "daily_prices.csv"       # 일별 시세 캐시
PORTFOLIO_CSV      = "portfolio.csv"          # 포트폴리오 (매수/매도/보유)
BACKTEST_CSV       = "backtest_results.csv"   # 백테스팅 결과
LOG_FILE           = "stockai.log"            # 로그 파일

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

# ── 포트폴리오 관리 ─────────────────────────────────────
PORTFOLIO_CASH_INIT = 100_000_000   # 초기 자본금 (1억원)
PORTFOLIO_REBALANCE_INTERVAL = 30   # 리밸런싱 주기 (일)

# ── 백테스팅 파라미터 ───────────────────────────────────
BACKTEST_START_DATE = "2023-01-01"
BACKTEST_END_DATE   = "2026-03-10"
BACKTEST_INITIAL_CAPITAL = 100_000_000  # 1억원
BACKTEST_COMMISSION = 0.003             # 거래수수료 0.3%
BACKTEST_SLIPPAGE   = 0.002             # 슬리피지 0.2%

# ── AI 신뢰도 점수 파라미터 ─────────────────────────────
AI_CONFIDENCE_THRESHOLD = 60  # 최소 신뢰도 (0~100)
AI_CACHE_HOURS = 24           # AI 의견 캐시 24시간

# ── 캐싱 설정 ──────────────────────────────────────────
CACHE_PRICE_HOURS = 1          # 주가 캐시 1시간
CACHE_FUNDAMENTALS_DAYS = 7    # 펀더멘털 캐시 7일
CACHE_INDICATORS_HOURS = 2     # 기술지표 캐시 2시간

# ── 로깅 설정 ──────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG/INFO/WARNING/ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 10_000_000     # 10MB
LOG_BACKUP_COUNT = 5           # 최대 5개 파일 보관

# ── 외국인/기관 매매 추적 ───────────────────────────────
TRACK_INSTITUTIONAL = True     # 기관 매매 추적 여부
TRACK_FOREIGNERS = True        # 외국인 매매 추적 여부
FOREIGN_DAILY_THRESHOLD = 5_000_000_000  # 기준: 50억원 이상

# ── 배당주 전략 ─────────────────────────────────────────
DIVIDEND_YIELD_MIN = 0.03      # 최소 배당수익률 3%
DIVIDEND_HOLD_YEARS = 5        # 배당주 보유기간 5년

# ── 성능 최적화 ─────────────────────────────────────────
PARALLEL_REQUESTS = 5          # 동시 API 요청 수
TIMEOUT_SECONDS = 30           # API 타임아웃 30초
RETRY_ATTEMPTS = 3             # 재시도 횟수
