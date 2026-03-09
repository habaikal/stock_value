# ============================================================
# app.py - Streamlit 멀티페이지 웹앱 (StockValuationAI Pro)
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings, time, logging
warnings.filterwarnings("ignore")

from stock_manager  import add_stock, remove_stock, get_watchlist, update_name
from data_collector import fetch_price_history, fetch_fundamentals, fetch_current_price
from data_collector import fetch_foreign_institutional_trades, fetch_korea_price_with_fdr
from wave_analyzer  import calculate_indicators, classify_wave, get_support_resistance
from valuation_engine import calculate_fair_value, build_scorecard
from ai_analyst     import analyze_with_gemini, quick_opinion
from portfolio_manager import Portfolio, export_portfolio_report
from backtest_engine import BacktestEngine
from logger_config import setup_logger

# 로거 설정
logger = setup_logger()

# ─────────────────────────────────────────────────────────────
# 페이지 설정 (멀티페이지 지원)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🥝 StockAI Pro - 적정주가 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# CSS 스타일
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* 폰트 적용 (Pretendard) - 아이콘이 깨지지 않도록 !important 제거 */
  @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
  
  html, body, p, div, h1, h2, h3, h4, h5, h6, span, a, label, button, input, select, textarea, li {
    font-family: 'Pretendard', sans-serif;
  }
  
  /* 다크 테마 공통 텍스트 강제 흰색 배치 */
  p, span, h1, h2, h3, h4, h5, h6, li, label, .stMarkdown {
    color: #f8fafc !important;
  }

  /* 입력 필드 등은 배경 대비 시인성을 위해 별도 지정 대비 */
  input, textarea, select {
    color: #1e293b !important;
    background-color: #f1f5f9 !important;
  }
  
  /* 메인 타이틀 다크 글래스모피즘 텍스트 */
  .stApp {
    background: linear-gradient(-45deg, #0f172a, #1e1b4b, #172554, #051833) !important;
    background-size: 400% 400% !important;
    animation: gradientBG 15s ease infinite !important;
  }
  @keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }

  /* 메인 타이틀 다크 글래스모피즘 텍스트 */
  .main-title {
    font-size: 2.8rem; 
    font-weight: 900;
    text-align: center; 
    margin-bottom: 0.3rem;
    background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
    -webkit-background-clip: text; 
    -webkit-text-fill-color: transparent;
    text-shadow: 2px 2px 8px rgba(0,0,0,0.3);
  }
  .sub-title {
    text-align: center; color: #94a3b8; font-size: 1.1rem; margin-bottom: 2.5rem;
    font-weight: 500;
  }

  /* 공통 다크 글래스모피즘 스타일 클래스 */
  .glass-card {
    background: rgba(30, 41, 59, 0.6) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4) !important;
    border-radius: 16px;
    padding: 1.2rem;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    color: #f8fafc;
  }
  .glass-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.6) !important;
  }

  /* 특정 컴포넌트 재정의 */
  .metric-card {
    background: rgba(30, 41, 59, 0.5) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px; padding: 1rem;
    border-left: 5px solid #3b82f6 !important; margin-bottom: 0.5rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    transition: all 0.3s;
  }
  .metric-card:hover {
    transform: scale(1.02);
  }

  .signal-box {
    font-size: 2rem; font-weight: 900; text-align: center;
    padding: 1.5rem; margin: 1.5rem 0;
    border-radius: 20px;
    background: rgba(30, 41, 59, 0.7);
    backdrop-filter: blur(15px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.1);
    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    transition: transform 0.3s;
    color: #f8fafc;
  }
  .signal-box:hover { transform: translateY(-3px); }

  .strong-buy  { color:#4ade80 !important; border-left: 8px solid #4ade80; }
  .buy         { color:#86efac !important; border-left: 8px solid #86efac; }
  .weak-buy    { color:#93c5fd !important; border-left: 8px solid #93c5fd; }
  .hold        { color:#fde047 !important; border-left: 8px solid #fde047; }
  .weak-sell   { color:#fdba74 !important; border-left: 8px solid #fdba74; }
  .sell        { color:#fca5a5 !important; border-left: 8px solid #fca5a5; }

  .section-header {
    font-size: 1.5rem; font-weight: 800; color: #93c5fd;
    padding-bottom: 0.3rem; margin: 2rem 0 1.2rem;
    border-bottom: 3px solid rgba(59, 130, 246, 0.3);
    display: inline-block;
  }

  .news-card {
    background: rgba(30, 41, 59, 0.6); 
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px; padding: 1rem;
    margin: 0.5rem 0; font-size: 0.9rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    transition: transform 0.2s;
    color: #cbd5e1;
  }
  .news-card:hover { transform: translateX(5px); }

  .factor-row {
    display: flex; align-items: center; gap: 1rem;
    padding: 0.8rem; border-radius: 10px; 
    background: rgba(30, 41, 59, 0.5);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 0.4rem;
  }

  /* 사이드바 글래스모피즘 */
  [data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.5) !important;
    backdrop-filter: blur(25px) !important;
    -webkit-backdrop-filter: blur(25px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  /* 기본 Expander(종목 추가 등) 다크 테마 반영 덮어쓰기 */
  .streamlit-expanderHeader {
    background: rgba(30, 41, 59, 0.5) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 8px !important;
    color: #f8fafc !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
  }
  .streamlit-expanderContent {
    background: transparent !important;
    border: none !important;
  }

  /* 탭 글래스 디자인 */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(15px);
    border-radius: 12px;
    padding: 0.2rem;
    display: flex;
    justify-content: space-around;
  }
  [data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 8px;
    margin: 0 2px;
    transition: all 0.3s;
    color: #94a3b8;
  }
  [data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(59, 130, 246, 0.8) !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    color: #ffffff !important;
  }

  /* 메트릭 박스들 투명화 */
  [data-testid="stMetricValue"] {
    color: #ffffff !important;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
  }
  [data-testid="stMetricLabel"] {
    color: #cbd5e1 !important;
  }
  div[data-testid="metric-container"] {
    background: rgba(30, 41, 59, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    transition: transform 0.2s;
  }
  div[data-testid="metric-container"]:hover {
    transform: translateY(-3px);
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────────
def fmt_price(v):
    if v is None: return "N/A"
    return f"₩{int(v):,}"

def fmt_pct(v):
    if v is None: return "N/A"
    return f"{v:+.1f}%"

def signal_class(sig: str) -> str:
    mapping = {
        "Strong Buy": "strong-buy", "Buy": "buy",
        "Weak Buy": "weak-buy",     "Hold": "hold",
        "Weak Sell": "weak-sell",   "Sell": "sell",
    }
    return mapping.get(sig, "hold")

@st.cache_data(ttl=300, show_spinner=False)
def load_analysis(ticker: str, market: str):
    """캐시 포함 전체 분석 실행 (5분 TTL)."""
    fund  = fetch_fundamentals(ticker, market)
    price = fetch_price_history(ticker, market, period="2y")
    if not price.empty:
        price = calculate_indicators(price)
        wave  = classify_wave(price)
        sr    = get_support_resistance(price)
    else:
        wave = {"wave_score": 55, "wave_label": "데이터부족", "wave_stage": "N/A", "detail": {}}
        sr   = {}
    val   = calculate_fair_value(fund, price, wave.get("wave_score", 55), market)
    score = build_scorecard(fund, wave, val)
    return fund, price, wave, sr, val, score


# ─────────────────────────────────────────────────────────────
# 사이드바: 종목 추가/관리
# ─────────────────────────────────────────────────────────────
def render_sidebar():
    st.sidebar.markdown("## 📋 관심 종목 관리")
    st.sidebar.markdown("---")

    # 종목 추가 입력 폼
    with st.sidebar.expander("➕ 종목 추가", expanded=True):
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            ticker_input = col1.text_input("티커 (예: 005930, AAPL)", placeholder="코드")
            name_input   = col2.text_input("종목명 (선택)", placeholder="이름")
            market_sel   = st.selectbox("시장", ["KOSPI", "KOSDAQ", "US"])
            memo_input   = st.text_input("메모 (선택)", placeholder="분석 메모")
            submitted    = st.form_submit_button("✅ 추가", use_container_width=True)

        if submitted and ticker_input:
            result = add_stock(
                ticker_input.strip(),
                name=name_input.strip(),
                market=market_sel,
                memo=memo_input.strip()
            )
            if result["status"] == "added":
                st.sidebar.success(f"✅ {ticker_input} 추가 완료!")
                st.rerun()
            else:
                st.sidebar.warning(f"⚠️ {ticker_input} 이미 존재합니다.")

    # 관심 종목 목록
    wl = get_watchlist()
    if wl.empty:
        st.sidebar.info("아직 종목이 없습니다.\n위에서 종목을 추가하세요!")
        return None

    st.sidebar.markdown("### 📌 관심 종목 목록")
    selected = st.sidebar.radio(
        label="분석할 종목 선택",
        options=wl["ticker"].tolist(),
        format_func=lambda t: f"{wl[wl['ticker']==t]['name'].values[0] or t}  ({t})",
        label_visibility="collapsed"
    )

    # 삭제 버튼
    with st.sidebar.expander("🗑 종목 삭제"):
        del_ticker = st.selectbox(
            "삭제할 종목", wl["ticker"].tolist(),
            format_func=lambda t: f"{wl[wl['ticker']==t]['name'].values[0] or t} ({t})"
        )
        if st.button("삭제 확인", type="secondary"):
            remove_stock(del_ticker)
            st.sidebar.success(f"🗑 {del_ticker} 삭제됨")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.caption("💡 데이터: yfinance | AI: Google Gemini")
    return selected, wl[wl["ticker"] == selected].iloc[0].to_dict()


# ─────────────────────────────────────────────────────────────
# 메인 화면 섹션들
# ─────────────────────────────────────────────────────────────

def render_header(fund, val, wave, ticker):
    name = fund.get("name", ticker)
    sector = fund.get("sector", "기타")
    cp   = fund.get("current_price")
    fv   = val.get("fair_value")
    sm   = val.get("safety_margin")
    sig  = val.get("signal", "Hold")
    sig_emoji = val.get("signal_emoji", "🟡")

    st.markdown(f'<p class="main-title">🥝 StockAI 적정주가 분석</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-title">30년 경력 전문가 방법론 × AI 분석 통합 시스템</p>', unsafe_allow_html=True)

    # 종목 헤더
    c1, c2, c3 = st.columns([3, 1, 1])
    c1.markdown(f"## 📈 {name}")
    c1.markdown(f"**티커:** `{ticker}` | **업종:** {sector} | **파동:** {wave.get('wave_label','N/A')}")
    c2.metric("현재가", fmt_price(cp))
    c3.metric("적정주가 (기본)", fmt_price(fv),
              delta=f"안전마진 {sm:+.1f}%" if sm is not None else None)
    
    # 추가 우량도 F-Score 표시
    f_score = val.get("f_score", 0)
    c4, c5 = st.columns([1, 1])
    c4.markdown(f"**Piotroski F-Score:** `{f_score}/9` (우량도)")
    if f_score >= 7: c4.success("우량(안전)")
    elif f_score <= 3: c4.error("재무 위험")
    else: c4.warning("보통")

    # 시그널 박스
    sig_css = signal_class(sig)
    st.markdown(f'<div class="signal-box {sig_css}">{sig_emoji} {sig}</div>', unsafe_allow_html=True)


def render_valuation_detail(val, fund):
    st.markdown('<p class="section-header">💰 적정주가 멀티팩터 분석</p>', unsafe_allow_html=True)

    # 팩터별 비교 차트
    factors = {
        "DCF 낙관\n(Monte Carlo)":  val.get("optimistic") if val.get("dcf_optimistic") is None else val.get("dcf_optimistic"),
        "DCF 기본\n(Monte Carlo)":  val.get("dcf_base"),
        "DCF 비관\n(Monte Carlo)":  val.get("dcf_bear"),
        "PER\n밸류":    val.get("per_value"),
        "PBR\n밸류":    val.get("pbr_value"),
        "자산\n가치":   val.get("asset_value"),
        "수익력\n가치": val.get("ep_value"),
        "최종\n적정가": val.get("fair_value"),
    }
    cp = val.get("current_price")

    valid = {k: v for k, v in factors.items() if v is not None}
    if valid:
        colors = ["#90caf9"] * (len(valid)-1) + ["#1a73e8"]
        fig = go.Figure(go.Bar(
            x=list(valid.keys()),
            y=list(valid.values()),
            marker_color=colors,
            text=[fmt_price(v) for v in valid.values()],
            textposition="outside"
        ))
        if cp:
            fig.add_hline(y=cp, line_dash="dash", line_color="red",
                          annotation_text=f"현재가 {fmt_price(cp)}", annotation_position="right")
        fig.update_layout(
            title="팩터별 적정주가 비교", height=380,
            yaxis_title="원(₩)", showlegend=False,
            margin=dict(t=50, b=30)
        )
        st.plotly_chart(fig, use_container_width=True)

    # 신뢰 구간 게이지
    c1, c2, c3 = st.columns(3)
    c1.metric("🐻 보수적 적정가", fmt_price(val.get("conservative")))
    c2.metric("🎯 기본 적정가",   fmt_price(val.get("fair_value")),
              delta=fmt_pct(val.get("safety_margin")))
    c3.metric("🚀 낙관적 적정가", fmt_price(val.get("optimistic")))

    # 주요 가정 정보
    with st.expander("⚙️ 계산 가정 상세"):
        col1, col2, col3 = st.columns(3)
        col1.info(f"**WACC:** {val.get('wacc', 'N/A')}%\n\n**기대성장률:** {val.get('base_growth', 'N/A')}%")
        col2.info(f"**한국시장 조정:** {(val.get('korea_adj') or 0)*100:+.1f}%")
        adj_d = val.get("korea_adj_detail", {})
        col3.info("\n".join([f"• {k}: {v*100:+.1f}%" for k, v in adj_d.items()]))
        st.caption("※ DCF 평가 모델이 5000회 이상 시뮬레이션 기반(Monte-Carlo) 확률 모형으로 업그레이드 되어 극한의 통계적 정밀도를 제공합니다.")

        # 증권사 컨센서스 비교
        tp = val.get("target_analyst")
        fv = val.get("fair_value")
        if tp and fv:
            diff = (tp - fv) / fv * 100
            st.success(f"📊 증권사 평균 목표가: {fmt_price(tp)} (본 모델 대비 {diff:+.1f}%)")


def render_fundamentals(fund):
    st.markdown('<p class="section-header">📊 펀더멘털 지표</p>', unsafe_allow_html=True)
    cols = st.columns(4)
    metrics = [
        ("PER", f"{fund.get('per', 'N/A')}배",  "주가수익비율"),
        ("PBR", f"{fund.get('pbr', 'N/A')}배",  "주가순자산비율"),
        ("ROE", f"{fund.get('roe', 'N/A')}%",   "자기자본이익률"),
        ("배당수익률", f"{fund.get('dividend_yield', 0):.1f}%", "시가배당률"),
    ]
    for i, (label, value, help_text) in enumerate(metrics):
        cols[i].metric(label, value, help=help_text)

    cols2 = st.columns(4)
    metrics2 = [
        ("52주 최고", fmt_price(fund.get("52w_high"))),
        ("52주 최저", fmt_price(fund.get("52w_low"))),
        ("시가총액",  f"{(fund.get('market_cap') or 0)/1e12:.2f}조"),
        ("베타",      f"{fund.get('beta', 'N/A')}"),
    ]
    for i, (label, value) in enumerate(metrics2):
        cols2[i].metric(label, value)


def render_wave_analysis(wave, price_df, sr):
    st.markdown('<p class="section-header">🌊 파동 분석 & 기술적 지표</p>', unsafe_allow_html=True)

    # 파동 정보
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"**파동 단계:** {wave.get('wave_stage', 'N/A')}")
        st.markdown(f"**파동 점수:** {wave.get('wave_score', 'N/A')}점")
        st.markdown(f"**파동 신호:** {wave.get('wave_label', 'N/A')}")
        st.markdown("---")
        d = wave.get("detail", {})
        if d:
            st.markdown(f"📌 MA20: {fmt_price(d.get('ma20'))}")
            st.markdown(f"📌 MA50: {fmt_price(d.get('ma50'))}")
            st.markdown(f"📌 RSI: {d.get('rsi', 'N/A')}")
            st.markdown(f"📌 52주 위치: {d.get('pos_52w', 'N/A')}%")
            st.markdown(f"📌 거래량 비율: {d.get('vol_ratio', 'N/A')}x")
        if sr:
            st.markdown("---")
            st.markdown(f"🔴 저항선: {fmt_price(sr.get('resistance'))}")
            st.markdown(f"🟢 지지선: {fmt_price(sr.get('support'))}")
            st.markdown(f"🔵 피봇: {fmt_price(sr.get('pivot'))}")

    with col2:
        if not price_df.empty and len(price_df) > 30:
            recent = price_df.tail(120)
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                row_heights=[0.6, 0.2, 0.2],
                subplot_titles=("주가 + 이동평균선", "RSI", "거래량")
            )
            # 캔들차트
            fig.add_trace(go.Candlestick(
                x=recent.index, open=recent["open"], high=recent["high"],
                low=recent["low"], close=recent["close"],
                name="주가", increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350"
            ), row=1, col=1)
            # 이동평균선
            for ma, color, name in [
                ("ma20",  "#ff9800", "MA20"),
                ("ma50",  "#2196f3", "MA50"),
                ("ma200", "#9c27b0", "MA200")
            ]:
                if ma in recent.columns:
                    fig.add_trace(go.Scatter(
                        x=recent.index, y=recent[ma],
                        line=dict(color=color, width=1.5),
                        name=name
                    ), row=1, col=1)
            # RSI
            if "rsi" in recent.columns:
                fig.add_trace(go.Scatter(
                    x=recent.index, y=recent["rsi"],
                    line=dict(color="#e91e63", width=1.5), name="RSI"
                ), row=2, col=1)
                fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
            # 거래량
            colors = ["#ef5350" if c < o else "#26a69a"
                      for c, o in zip(recent["close"], recent["open"])]
            fig.add_trace(go.Bar(
                x=recent.index, y=recent["volume"],
                marker_color=colors, name="거래량", showlegend=False
            ), row=3, col=1)

            fig.update_layout(
                height=500, showlegend=True,
                xaxis_rangeslider_visible=False,
                margin=dict(t=30, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("차트를 그릴 데이터가 부족합니다.")


def render_scorecard(score):
    st.markdown('<p class="section-header">🏆 종합 투자 스코어카드</p>', unsafe_allow_html=True)

    total = score.get("total", 0)
    # 게이지 차트
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=total,
        title={"text": "종합 투자 점수", "font": {"size": 20}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar":  {"color": "#1a73e8"},
            "steps": [
                {"range": [0,  40], "color": "#fce4ec"},
                {"range": [40, 60], "color": "#fffde7"},
                {"range": [60, 80], "color": "#e8f5e9"},
                {"range": [80,100], "color": "#c8e6c9"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75, "value": 70
            }
        }
    ))
    fig.update_layout(height=280, margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 세부 점수
    cols = st.columns(4)
    score_items = [
        ("💰 수익성",   score.get("profitability", 0), 25),
        ("📈 성장성",   score.get("growth",         0), 25),
        ("💎 밸류에이션", score.get("valuation",   0), 25),
        ("🛡 안전성",   score.get("safety",         0), 25),
    ]
    for i, (label, s, mx) in enumerate(score_items):
        pct = s / mx * 100
        cols[i].markdown(f"**{label}**")
        cols[i].progress(int(pct))
        cols[i].caption(f"{s:.1f} / {mx}점")


def render_ai_analysis(fund, val, wave, ticker, use_ai: bool):
    st.markdown('<p class="section-header">🤖 AI 애널리스트 의견 (Gemini Pro)</p>', unsafe_allow_html=True)

    if use_ai:
        with st.spinner("🔍 Gemini가 뉴스와 데이터를 분석 중..."):
            ai = analyze_with_gemini(
                fund.get("name", ticker), ticker,
                fund, val, wave
            )

        # 의견 + 신뢰도 표시
        opinion = ai.get("opinion", "Hold")
        credibility = ai.get("credibility_score", 50)
        css = signal_class(opinion)
        
        # 신뢰도 시각화
        credibility_bar = "🟢" * int(credibility / 10) + "⬜" * (10 - int(credibility / 10))
        st.markdown(f'<div class="signal-box {css}">🤖 AI 의견: {opinion}</div>',
                    unsafe_allow_html=True)
        
        st.write(f"**신뢰도 점수**: {credibility_bar} {credibility:.0f}%")
        
        # 신뢰도 경고 메시지
        if "warning" in ai:
            st.warning(ai["warning"])
        
        if credibility < 50:
            st.info("⚠️ 낮은 신뢰도. 정량 신호와 함께 검토하세요.")

        if ai.get("target_price"):
            st.metric("AI 목표주가", fmt_price(ai.get("target_price")))

        st.markdown(f"> 📝 {ai.get('summary', '')}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🟢 상승 근거**")
            for pt in ai.get("bull_points", []):
                st.markdown(f"- {pt}")
        with col2:
            st.markdown("**🔴 위험 요인**")
            for pt in ai.get("bear_points", []):
                st.markdown(f"- {pt}")

        cats = ai.get("catalysts", [])
        if cats:
            st.markdown("**⚡ 주요 촉매**")
            st.markdown(" | ".join([f"`{c}`" for c in cats]))

        col3, col4, col5 = st.columns(3)
        col3.metric("리스크 수준", ai.get("risk_level", "보통"))
        col4.metric("AI 신뢰도", f"{ai.get('confidence', 0)}%")
        col5.metric("추천 보유기간", ai.get("holding_period", "중기"))

        # 뉴스
        news = ai.get("news", [])
        if news:
            st.markdown("**📰 최근 관련 뉴스**")
            for n in news:
                st.markdown(
                    f'<div class="news-card glass-card">📌 <b>{n.get("title","")}</b><br>'
                    f'{n.get("body","")[:150]}... '
                    f'<a href="{n.get("url","#")}" target="_blank">더보기</a></div>',
                    unsafe_allow_html=True
                )
    else:
        # 규칙 기반 빠른 의견
        opinion = quick_opinion(
            val.get("signal", "Hold"),
            val.get("safety_margin")
        )
        st.info(f"🤖 **규칙 기반 의견:** {opinion}")
        st.caption("Gemini AI 분석을 사용하려면 사이드바에서 'AI 분석 사용'을 체크하고 .env에 GOOGLE_API_KEY를 입력하세요.")


def render_watchlist_table():
    st.markdown('<p class="section-header">📋 관심 종목 현황 (포트폴리오 뷰)</p>', unsafe_allow_html=True)
    wl = get_watchlist()
    if wl.empty:
        st.info("관심 종목을 추가하면 여기에 표시됩니다.")
        return

    rows = []
    progress_bar = st.progress(0, text="포트폴리오 데이터 로딩 중...")
    for i, row in wl.iterrows():
        ticker  = row["ticker"]
        market  = row.get("market", "KOSPI")
        try:
            fund = fetch_fundamentals(ticker, market)
            cp   = fund.get("current_price")
            per  = fund.get("per")
            pbr  = fund.get("pbr")
            roe  = fund.get("roe")
            name = fund.get("name") or row.get("name") or ticker
            update_name(ticker, name)

            price_df = fetch_price_history(ticker, market, period="6mo")
            if not price_df.empty:
                price_df = calculate_indicators(price_df)
                wave = classify_wave(price_df)
            else:
                wave = {"wave_score": 55, "wave_label": "N/A"}

            val = calculate_fair_value(fund, price_df, wave.get("wave_score", 55), market)
            rows.append({
                "시장": market,
                "종목명": name, "티커": ticker,
                "현재가": fmt_price(cp),
                "적정가": fmt_price(val.get("fair_value")),
                "안전마진": fmt_pct(val.get("safety_margin")),
                "시그널": val.get("signal", "N/A"),
                "파동": wave.get("wave_stage", "N/A"),
                "F-Score": f"{val.get('f_score', 'N/A')}/9",
                "PER": f"{per}배" if per else "N/A",
                "PBR": f"{pbr}배" if pbr else "N/A",
                "ROE": f"{roe}%" if roe else "N/A",
            })
        except Exception as e:
            rows.append({"종목명": ticker, "티커": ticker,
                         "현재가": "오류", "시그널": str(e)[:30]})
        progress_bar.progress((i+1)/len(wl))

    progress_bar.empty()
    if rows:
        df_display = pd.DataFrame(rows)
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
# 메인 진입점
# ─────────────────────────────────────────────────────────────
def main():
    result = render_sidebar()

    if result is None:
        st.markdown('<p class="main-title">🥝 StockAI 적정주가 분석</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-title">30년 경력 전문가 방법론 × AI 분석 통합 시스템</p>', unsafe_allow_html=True)
        st.info("👈 사이드바에서 종목을 추가하고 분석을 시작하세요!")
        st.markdown("""
        ### 🚀 사용법
        1. **왼쪽 사이드바**에서 종목 티커(예: `005930`)를 입력하여 추가
        2. 관심 종목 클릭 → 자동으로 실시간 분석 실행
        3. AI 분석을 원하면 `.env`에 `GOOGLE_API_KEY=your_key` 입력 후 체크박스 활성화
        
        ### 📊 30년 경력 글로벌 기준 분석 방법론 (Ultimate Version)
        | 팩터 | 가중치 | 방법 |
        |------|--------|------|
        | 확률론적 DCF | 35% | 몬테카를로(Monte Carlo) 시뮬레이션 확률 모형 적용 |
        | 상대가치 | 25% | 글로벌 기준 회귀 PBR/PER 분석 + F-Score(피오트로스키) 결합 |
        | 시장 팩터 | 0% | 한국 디스카운트 보정 및 미국주식 프리미엄 동적 인식 |
        | 자산/수익 | 30% | ROE조정 청산가치 + 영구채 모델 |
        | 파동/모멘텀 | 10% | 4단계 파동 분석 기반 엘리어트 파동 점수 부여 |
        """)
        return

    selected_ticker, selected_row = result
    market = selected_row.get("market", "KOSPI")

    # AI 사용 여부 (사이드바)
    st.sidebar.markdown("---")
    use_ai = st.sidebar.checkbox(
        "🤖 AI 분석 사용 (Gemini)",
        value=bool(getattr(__import__('config'), 'GOOGLE_API_KEY', False)),
        help="GOOGLE_API_KEY 필요. .env 파일에 설정하세요."
    )

    # 탭 구성 (포트폴리오, 백테스팅 추가)
    tab_main, tab_wave, tab_score, tab_ai, tab_portfolio, tab_backtest = st.tabs([
        "💰 적정주가 분석",
        "🌊 파동·기술 분석",
        "🏆 스코어카드",
        "🤖 AI 애널리스트",
        "📈 포트폴리오",
        "📊 백테스팅"
    ])

    # 데이터 로딩 (캐시)
    with st.spinner(f"📡 {selected_ticker} 데이터 수집 중..."):
        try:
            fund, price_df, wave, sr, val, score = load_analysis(selected_ticker, market)
            # 종목명 업데이트
            update_name(selected_ticker, fund.get("name", ""))
        except Exception as e:
            st.error(f"❌ 데이터 수집 오류: {e}")
            return

    with tab_main:
        render_header(fund, val, wave, selected_ticker)
        st.divider()
        render_fundamentals(fund)
        st.divider()
        render_valuation_detail(val, fund)

    with tab_wave:
        render_wave_analysis(wave, price_df, sr)

    with tab_score:
        render_scorecard(score)

    with tab_ai:
        render_ai_analysis(fund, val, wave, selected_ticker, use_ai)

    with tab_portfolio:
        render_portfolio_management(selected_ticker, fund.get("current_price"))

    with tab_backtest:
        render_backtest_analysis(selected_ticker)


# ──────────────────────────────────────────────────────────────
# 포트폴리오 관리 렌더링
# ──────────────────────────────────────────────────────────────
def render_portfolio_management(ticker: str, current_price: float | None) -> None:
    """포트폴리오 관리 UI."""
    st.markdown("### 📈 포트폴리오 관리")
    
    portfolio = Portfolio()
    current_value = portfolio.get_current_value()
    allocation = portfolio.get_allocation()
    stats = portfolio.get_performance_stats()
    
    # 자산 요약
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총자산", f"₩{current_value['total_value']:,.0f}", 
                  f"{current_value['return_rate']:.2f}%", delta_color="normal")
    with col2:
        st.metric("증권가액", f"₩{current_value['securities_value']:,.0f}")
    with col3:
        st.metric("현금", f"₩{current_value['cash']:,.0f}")
    with col4:
        st.metric("보유종목", allocation.get("num_holdings", 0))
    
    # 거래 UI
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💳 매수")
        ticker_input = st.text_input("종목코드", value=ticker, key="buy_ticker")
        shares = st.number_input("수량 (주)", min_value=1, step=1, key="buy_shares")
        price = st.number_input("매수가 (원)", min_value=1, step=100, 
                               value=int(current_price) if current_price else 10000,
                               key="buy_price")
        
        if st.button("🟢 매수 실행"):
            result = portfolio.buy(ticker_input, shares, price)
            if result["status"] == "success":
                st.success(f"✅ {ticker_input} {shares}주 매수 완료\n남은 자금: ₩{result['cash_left']:,.0f}")
                st.rerun()
            else:
                st.error(f"❌ {result['status']}: 필요 {result['required']:,.0f}원, 보유 {result['available']:,.0f}원")
    
    with col2:
        st.subheader("📤 매도")
        ticker_sell = st.text_input("종목코드", key="sell_ticker")
        shares_sell = st.number_input("수량 (주)", min_value=1, step=1, key="sell_shares")
        price_sell = st.number_input("매도가 (원)", min_value=1, step=100, value=10000, key="sell_price")
        
        if st.button("🔴 매도 실행"):
            result = portfolio.sell(ticker_sell, shares_sell, price_sell)
            if result["status"] == "success":
                st.success(f"✅ {ticker_sell} {shares_sell}주 매도 완료\n순수익: ₩{result['proceeds']:,.0f} "
                          f"(수익률: {result['gain_pct']:.2f}%)")
                st.rerun()
            else:
                st.error(f"❌ {result['status']}: 보유 {result['available']:.0f}주")
    
    # 보유 종목 현황
    st.divider()
    st.subheader("📊 보유 종목")
    if current_value["details"]:
        df_holdings = pd.DataFrame(current_value["details"])
        st.dataframe(df_holdings, use_container_width=True)
    else:
        st.info("보유 종목 없음")
    
    # 성과통계
    st.divider()
    st.subheader("🎯 성과통계")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 거래", stats.get("trades", 0))
    with col2:
        st.metric("승률", f"{stats.get('win_rate', 0):.1f}%")
    with col3:
        st.metric("평균손익", f"₩{stats.get('avg_gain', 0):,.0f}")
    with col4:
        st.metric("최대수익", f"₩{stats.get('total_gain', 0):,.0f}")
    
    # 거래 이력
    if st.checkbox("거래 이력 보기"):
        history = portfolio.get_transaction_history()
        if history:
            df_history = pd.DataFrame(history)
            st.dataframe(df_history, use_container_width=True)


# ──────────────────────────────────────────────────────────────
# 백테스팅 렌더링
# ──────────────────────────────────────────────────────────────
def render_backtest_analysis(ticker: str) -> None:
    """백테스팅 분석 UI."""
    st.markdown("### 📊 신호 백테스팅")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작일", value=pd.to_datetime("2023-01-01").date())
    with col2:
        end_date = st.date_input("종료일", value=pd.to_datetime("2026-03-10").date())
    
    if st.button("▶️ 백테스트 실행", key="backtest_run"):
        with st.spinner(f"🔄 {ticker} 백테스팅 중..."):
            engine = BacktestEngine(
                ticker,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            results = engine.run()
            
            if results and "error" not in results:
                # 성과 메트릭스
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("수익률", f"{results['total_return']:.2f}%")
                with col2:
                    st.metric("CAGR", f"{results['cagr']:.2f}%")
                with col3:
                    st.metric("최대낙폭", f"{results['mdd']:.2f}%")
                with col4:
                    st.metric("Sharpe 지수", f"{results['sharpe_ratio']:.2f}")
                with col5:
                    st.metric("거래수", results["num_trades"])
                
                st.divider()
                
                # 일일 포트폴리오 가치 차트
                df_daily = pd.DataFrame(results["daily_values"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_daily["date"],
                    y=df_daily["portfolio_value"],
                    mode="lines",
                    name="포트폴리오 가치",
                    line=dict(color="#3b82f6", width=2)
                ))
                fig.update_layout(
                    title=f"{ticker} 백테스팅 성과",
                    xaxis_title="날짜",
                    yaxis_title="자산가치 (원)",
                    hovermode="x unified",
                    template="plotly_dark"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 거래 기록
                if results["trades"]:
                    st.divider()
                    st.subheader("📋 거래 기록")
                    df_trades = pd.DataFrame(results["trades"])
                    st.dataframe(df_trades, use_container_width=True)
                
                # 결과 저장
                if st.button("💾 결과 저장"):
                    engine.save_results(results)
                    st.success("✅ 백테스팅 결과 저장됨")
            else:
                st.error("❌ 백테스팅 실패")


# ──────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # 임시 GOOGLE_API_KEY 참조
    from config import GOOGLE_API_KEY
    main()
