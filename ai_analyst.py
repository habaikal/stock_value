# ============================================================
# ai_analyst.py - Gemini Pro 기반 AI 뉴스 분석 & 투자 의견 (신뢰도 개선)
# ============================================================
import google.generativeai as genai
from duckduckgo_search import DDGS
from config import GOOGLE_API_KEY, AI_CONFIDENCE_THRESHOLD, AI_CACHE_HOURS
import json, re, os
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger("StockAI.AIAnalyst")

# ── AI 의견 캐시 ───────────────────────────────────────
CACHE_DIR = "ai_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def _configure_gemini():
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel("gemini-1.5-flash")


def search_news(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo로 최신 뉴스 검색."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title":   r.get("title", ""),
                    "body":    r.get("body", ""),
                    "url":     r.get("url", ""),
                    "date":    r.get("date", ""),
                })
        return results
    except Exception as e:
        print(f"[뉴스 검색 오류] {e}")
        return []


def analyze_with_gemini(stock_name: str, ticker: str,
                        fund: dict, val_result: dict,
                        wave_result: dict) -> dict:
    """
    Gemini에게 종목 종합 분석 요청 (신뢰도 개선).
    반환: {opinion, summary, bull_points, bear_points, risk_level, confidence, credibility_score}
    """
    if not GOOGLE_API_KEY:
        return {
            "opinion": "API 키 없음",
            "summary": "GOOGLE_API_KEY를 .env에 설정하면 AI 분석이 활성화됩니다.",
            "bull_points": [], "bear_points": [],
            "risk_level": "알수없음", "confidence": 0,
            "credibility_score": 0,
        }

    # 캐시 확인
    cache_key = hashlib.md5(f"{ticker}_{datetime.now().date()}".encode()).hexdigest()
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if (datetime.now() - datetime.fromisoformat(cached.get("timestamp", ""))).seconds < AI_CACHE_HOURS * 3600:
                    logger.info(f"캐시에서 AI 의견 로드: {ticker}")
                    return cached["result"]
        except Exception as e:
            logger.warning(f"캐시 로드 실패: {e}")

    # 뉴스 수집
    news_list = search_news(f"{stock_name} 주가 실적 전망 2025", max_results=5)
    news_text = "\n".join([
        f"[{n['date']}] {n['title']}: {n['body'][:200]}" for n in news_list
    ]) or "최근 뉴스 없음"

    # 밸류에이션 요약
    fv = val_result.get("fair_value", "N/A")
    cp = val_result.get("current_price", "N/A")
    sm = val_result.get("safety_margin", "N/A")
    signal = val_result.get("signal", "N/A")
    wave_label = wave_result.get("wave_label", "N/A")

    prompt = f"""
당신은 30년 경력의 한국 주식 시장 전문 애널리스트입니다.
아래 데이터를 종합적으로 분석하여 투자 의견을 제시하세요.

## 분석 대상
- 종목명: {stock_name} ({ticker})
- 현재가: {cp:,}원 (있는 경우)
- 적정주가: {fv:,}원 (있는 경우)
- 안전마진: {sm}%
- 퀀트 시그널: {signal}
- 파동 단계: {wave_label}

## 펀더멘털
- PER: {fund.get('per', 'N/A')}배
- PBR: {fund.get('pbr', 'N/A')}배
- ROE: {fund.get('roe', 'N/A')}%
- 배당수익률: {fund.get('dividend_yield', 0):.1f}%
- 업종: {fund.get('sector', '미분류')}

## DCF 시나리오
- 낙관: {val_result.get('dcf_bull', 'N/A')}원
- 기본: {val_result.get('dcf_base', 'N/A')}원
- 비관: {val_result.get('dcf_bear', 'N/A')}원

## 최근 뉴스
{news_text}

## 출력 형식 (JSON만 출력, 다른 텍스트 없이)
{{
  "opinion": "Strong Buy | Buy | Weak Buy | Hold | Weak Sell | Sell 중 하나",
  "target_price": 숫자(원),
  "summary": "3문장 이내 핵심 요약",
  "bull_points": ["상승 근거 1", "상승 근거 2", "상승 근거 3"],
  "bear_points": ["하락 위험 1", "하락 위험 2"],
  "catalysts": ["단기 촉매 1", "중기 촉매 2"],
  "risk_level": "낮음 | 보통 | 높음",
  "confidence": 0~100 (분석 신뢰도),
  "holding_period": "단기(1개월) | 중기(3~6개월) | 장기(1년+)"
}}
"""

    try:
        model = _configure_gemini()
        response = model.generate_content(prompt)
        text = response.text.strip()

        # JSON 파싱
        json_match = re.search(r'\{[\s\S]+\}', text)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(text)

        result["news"] = news_list[:3]
        
        # 신뢰도 점수 계산 및 검증
        result["credibility_score"] = _calculate_credibility(result, val_result, fund)
        result["timestamp"] = datetime.now().isoformat()
        
        # 낮은 신뢰도 경고
        if result["credibility_score"] < AI_CONFIDENCE_THRESHOLD:
            result["warning"] = f"⚠️ 신뢰도 {result['credibility_score']:.0f}% - 데이터 확인 후 투자 결정 권장"
        
        # 캐시 저장
        _save_cache(cache_file, result)
        
        return result

    except json.JSONDecodeError:
        fallback = {
            "opinion": signal,
            "summary": f"AI 분석 중 파싱 오류. 퀀트 시그널: {signal}",
            "bull_points": [], "bear_points": [],
            "risk_level": "보통", "confidence": 40,
            "credibility_score": 35,
            "news": news_list[:3],
            "warning": "⚠️ AI 응답 파싱 실패. 정량 신호 참조"
        }
        return fallback
    except Exception as e:
        fallback = {
            "opinion": signal,
            "summary": f"AI 분석 오류: {str(e)[:100]}",
            "bull_points": [], "bear_points": [],
            "risk_level": "보통", "confidence": 0,
            "credibility_score": 30,
            "news": news_list[:3],
            "warning": "⚠️ AI 분석 실패. 정량 신호 참조"
        }
        logger.error(f"AI 분석 실패: {e}")
        return fallback


def _calculate_credibility(ai_opinion: dict, val_result: dict, fund: dict) -> float:
    """
    AI 의견의 신뢰도 점수 계산 (0~100).
    신호 일관성, 데이터 품질, 펀더멘털 정렬도를 점수화.
    """
    score = 100
    
    # 1. 신뢰도 자체 점수 (AI가 제시한)
    ai_confidence = ai_opinion.get("confidence", 50)
    if ai_confidence < 50:
        score -= 20
    
    # 2. 데이터 완성도 점수
    data_quality = 0
    checks = [
        val_result.get("fair_value") is not None,
        fund.get("per") is not None,
        fund.get("roe") is not None,
        len(ai_opinion.get("bull_points", [])) > 0,
    ]
    data_quality = sum(checks) / len(checks) * 30
    score += data_quality - 30  # -30 ~ 0
    
    # 3. 의견 일관성 확인
    opinion = ai_opinion.get("opinion", "")
    sm = val_result.get("safety_margin")
    
    # 안전마진과 의견의 일관성 검증
    if sm is not None:
        opinion_matches = False
        if sm > 20 and opinion in ["Strong Buy", "Buy"]:
            opinion_matches = True
        elif 15 <= sm <= 20 and opinion in ["Buy", "Weak Buy"]:
            opinion_matches = True
        elif -10 <= sm < 15 and opinion in ["Weak Buy", "Hold"]:
            opinion_matches = True
        elif -30 <= sm < -10 and opinion in ["Hold", "Weak Sell"]:
            opinion_matches = True
        elif sm < -30 and opinion in ["Weak Sell", "Sell"]:
            opinion_matches = True
        
        if not opinion_matches:
            score -= 15  # 일관성 없으면 -15
    
    # 4. PER 현실성 검증
    per = fund.get("per")
    if per is not None:
        if per < 0 or per > 100 and ai_opinion.get("opinion") == "Strong Buy":
            score -= 10  # 비정상적인 PER과 강한 의견 = 신뢰도 감소
    
    return max(0, min(100, score))


def _save_cache(cache_file: str, result: dict) -> None:
    """AI 의견을 파일로 캐시."""
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "result": result}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {e}")


def quick_opinion(signal: str, safety_margin: float) -> str:
    """API 키 없을 때 규칙 기반 빠른 의견."""
    if safety_margin is None:
        return "데이터 부족으로 판단 불가"
    if safety_margin >= 30:
        return f"✅ 현재가 대비 {safety_margin:.1f}% 저평가. 중장기 매수 적합."
    elif safety_margin >= 15:
        return f"🔵 {safety_margin:.1f}% 저평가. 분할 매수 고려."
    elif safety_margin >= -5:
        return f"🟡 적정가 수준. 추가 모니터링 권장."
    elif safety_margin >= -20:
        return f"🟠 {abs(safety_margin):.1f}% 고평가. 신규 매수 자제."
    else:
        return f"🔴 {abs(safety_margin):.1f}% 과평가. 매도 또는 비중 축소 검토."
