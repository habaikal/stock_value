# 🥝 StockValuationAI - 한국 주식 적정주가 분석 웹앱

30년 경력 전문가 방법론 × StockAI × Gemini AI 통합 시스템

## 🚀 빠른 시작

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. API 키 설정 (.env.example → .env 복사 후 편집)
cp .env.example .env

# 3. 환경 점검
python run_check.py

# 4. 앱 실행
streamlit run app.py
```

## 📁 파일 구조

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit 메인 웹앱 |
| `config.py` | 전역 설정 및 밸류에이션 파라미터 |
| `stock_manager.py` | 관심종목 CSV 저장·조회·삭제 |
| `data_collector.py` | yfinance 실시간 데이터 수집 |
| `wave_analyzer.py` | 파동 분석 + 기술적 지표 |
| `valuation_engine.py` | 5-Factor 적정주가 계산 엔진 |
| `ai_analyst.py` | Gemini AI 뉴스 분석 |
| `run_check.py` | 환경 점검 스크립트 |

## 📊 분석 방법론

### 5-Factor 적정주가 모델
- **DCF (35%)**: Bull/Base/Bear 3시나리오 확률 가중 DCF
- **상대가치 (25%)**: PER/PBR/PSR 회귀분석 기반
- **자산가치 (15%)**: ROE 조정 청산가치
- **수익력 가치 (15%)**: 영구채 모델
- **파동 모멘텀 (10%)**: 4단계 파동 분류 조정

### 파동 분류 (StockAI 방법론)
- 🚀 2단계 중기 (90점): 정배열 + 거래량 급증 + RSI 55~75
- 📈 2단계 초기 (80점): 골든크로스 + 거래량 증가
- 🔄 전환 구간 (70점): 이평선 수렴 + 바닥 탈출
- 📊 일반 상승 (60점): MA20 > MA50

### 투자 판단 기준
| 시그널 | 조건 |
|--------|------|
| 🟢🟢 Strong Buy | 현재가 < 적정가 × 70% |
| 🟢 Buy | 현재가 < 적정가 × 85% |
| 🔵 Weak Buy | 현재가 < 적정가 × 95% |
| 🟡 Hold | 적정가의 85~110% 사이 |
| 🟠 Weak Sell | 현재가 > 적정가 × 110% |
| 🔴 Sell | 현재가 > 적정가 × 120% |
