#!/usr/bin/env python3
# ============================================================
# setup_and_run.sh → 이 파일은 README용. 실제 실행은 아래 참조
# run_check.py  - 환경 점검 및 초기 설정 스크립트
# ============================================================
import subprocess, sys, os

def check_env():
    print("=" * 60)
    print("🥝 StockValuationAI 환경 점검")
    print("=" * 60)

    # Python 버전
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 9
    print(f"{'✅' if ok else '❌'} Python {v.major}.{v.minor}.{v.micro}  (필요: 3.9+)")

    # 필수 패키지
    packages = [
        "streamlit", "pandas", "numpy", "yfinance",
        "plotly", "google.generativeai", "duckduckgo_search",
    ]
    for pkg in packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"✅ {pkg}")
        except ImportError:
            print(f"❌ {pkg} → pip install {pkg}")

    # .env 파일
    if os.path.exists(".env"):
        with open(".env") as f:
            content = f.read()
        if "GOOGLE_API_KEY" in content and "your_api_key" not in content:
            print("✅ .env: GOOGLE_API_KEY 설정됨")
        else:
            print("⚠️  .env: GOOGLE_API_KEY 미설정 (AI 분석 비활성)")
    else:
        print("⚠️  .env 파일 없음 (AI 분석 비활성)")

    # watchlist.csv
    if os.path.exists("watchlist.csv"):
        import pandas as pd
        df = pd.read_csv("watchlist.csv")
        print(f"✅ watchlist.csv: {len(df)}개 종목 등록됨")
    else:
        print("📋 watchlist.csv: 아직 없음 (앱 실행 후 종목 추가 시 자동 생성)")

    print("=" * 60)
    print("▶ 앱 실행: streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    check_env()
