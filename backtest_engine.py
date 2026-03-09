# ============================================================
# backtest_engine.py - 신호 정확도 검증 및 백테스팅
# ============================================================
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from config import (
    BACKTEST_START_DATE, BACKTEST_END_DATE, BACKTEST_INITIAL_CAPITAL,
    BACKTEST_COMMISSION, BACKTEST_SLIPPAGE, BACKTEST_CSV
)
from data_collector import fetch_price_history
from wave_analyzer import calculate_indicators, classify_wave
from valuation_engine import calculate_fair_value

logger = logging.getLogger("StockAI.Backtest")


class BacktestEngine:
    """Signal 기반 간단한 백테스팅."""
    
    def __init__(self, ticker: str, start_date: str = BACKTEST_START_DATE,
                 end_date: str = BACKTEST_END_DATE,
                 initial_capital: int = BACKTEST_INITIAL_CAPITAL):
        self.ticker = ticker
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.shares = 0
        self.trades = []
        self.daily_values = []
        
        self.df = None
        self.signals = []
    
    def _load_data(self) -> bool:
        """백테스트 기간의 가격 데이터 로드."""
        try:
            # 충분한 히스토리 로드 (지표 계산용)
            early_start = self.start_date - timedelta(days=200)
            df = fetch_price_history(
                self.ticker,
                market="KOSPI",
                period="5y"  # 충분한 기간
            )
            
            if df.empty:
                logger.error(f"{self.ticker} 데이터 수집 실패")
                return False
            
            # 기간 필터링
            self.df = df[
                (df.index >= early_start) & (df.index <= self.end_date)
            ].copy()
            
            if self.df.empty:
                logger.error(f"{self.ticker} {self.start_date}~{self.end_date} 데이터 없음")
                return False
            
            # 기술적 지표 계산
            self.df = calculate_indicators(self.df)
            logger.info(f"데이터 로드: {self.ticker} {len(self.df)} 행")
            return True
            
        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            return False
    
    def _generate_signals(self) -> None:
        """각 날짜별 Signal 생성."""
        signals = []
        
        for i in range(200, len(self.df)):  # 충분한 히스토리 후부터
            date = self.df.index[i]
            if date < self.start_date:
                continue
            
            row = self.df.iloc[i]
            
            # 간단한 시그널: MA20 > MA50 (상승) → BUY, MA20 < MA50 (하강) → SELL
            ma20 = row.get("ma20")
            ma50 = row.get("ma50")
            rsi = row.get("rsi", 50)
            close = row.get("close")
            
            signal = "HOLD"
            reason = ""
            
            if pd.notna(ma20) and pd.notna(ma50):
                if ma20 > ma50 and rsi < 70:
                    signal = "BUY"
                    reason = "골든크로스 + RSI 과매수 전"
                elif ma20 < ma50 and rsi > 30:
                    signal = "SELL"
                    reason = "데드크로스 + RSI 과매도 전"
            
            signals.append({
                "date": date.strftime("%Y-%m-%d"),
                "close": round(close, 0),
                "ma20": round(ma20, 0) if pd.notna(ma20) else None,
                "ma50": round(ma50, 0) if pd.notna(ma50) else None,
                "rsi": round(rsi, 1),
                "signal": signal,
                "reason": reason,
            })
        
        self.signals = signals
    
    def _execute_trades(self) -> None:
        """시그널 기반 매매 실행."""
        for signal_data in self.signals:
            date = signal_data["date"]
            close = signal_data["close"]
            signal = signal_data["signal"]
            
            # 슬리피지 적용
            slipped_price = close * (1 + BACKTEST_SLIPPAGE)
            
            if signal == "BUY" and self.shares == 0:
                # 전체 자금으로 매수
                shares_to_buy = self.cash / slipped_price
                cost = shares_to_buy * slipped_price
                commission = cost * BACKTEST_COMMISSION
                
                self.shares = shares_to_buy
                self.cash -= (cost + commission)
                
                self.trades.append({
                    "date": date,
                    "action": "BUY",
                    "shares": round(shares_to_buy, 0),
                    "price": round(slipped_price, 0),
                    "commission": round(commission, 0),
                })
                
                logger.info(f"{date} BUY: {self.ticker} {shares_to_buy:.0f}주 @ {slipped_price:.0f}원")
            
            elif signal == "SELL" and self.shares > 0:
                # 전체 매도
                proceeds = self.shares * slipped_price
                commission = proceeds * BACKTEST_COMMISSION
                
                self.cash += (proceeds - commission)
                
                self.trades.append({
                    "date": date,
                    "action": "SELL",
                    "shares": round(self.shares, 0),
                    "price": round(slipped_price, 0),
                    "commission": round(commission, 0),
                    "proceeds": round(proceeds - commission, 0),
                })
                
                logger.info(f"{date} SELL: {self.ticker} {self.shares:.0f}주 @ {slipped_price:.0f}원")
                self.shares = 0
            
            # 일일 포트폴리오 가치 기록
            portfolio_value = self.cash + (self.shares * close)
            self.daily_values.append({
                "date": date,
                "portfolio_value": round(portfolio_value, 0),
                "shares": round(self.shares, 0),
                "cash": round(self.cash, 0),
            })
    
    def run(self) -> dict:
        """백테스트 실행."""
        if not self._load_data():
            return None
        
        self._generate_signals()
        self._execute_trades()
        
        return self.get_results()
    
    def get_results(self) -> dict:
        """백테스트 결과 반환."""
        if not self.daily_values:
            return {"error": "No trades executed"}
        
        daily_df = pd.DataFrame(self.daily_values)
        final_value = daily_df["portfolio_value"].iloc[-1]
        
        returns = (final_value - self.initial_capital) / self.initial_capital * 100
        
        # CAGR 계산 (복합연율수익률)
        days_elapsed = (pd.to_datetime(daily_df["date"].iloc[-1]) - 
                       pd.to_datetime(daily_df["date"].iloc[0])).days
        years = days_elapsed / 365.25
        cagr = ((final_value / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # 최대낙폭 (MDD: Maximum Drawdown)
        cummax = daily_df["portfolio_value"].cummax()
        drawdown = (daily_df["portfolio_value"] - cummax) / cummax * 100
        mdd = drawdown.min()
        
        # Sharpe Ratio (간단히 계산)
        daily_returns = daily_df["portfolio_value"].pct_change().dropna() * 100
        sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0
        
        # 거래 통계
        sell_trades = [t for t in self.trades if t["action"] == "SELL"]
        win_trades = 0
        total_gain = 0
        
        for trade in sell_trades:
            # 해당 매도 전의 매수 찾기
            for prev_trade in self.trades:
                if prev_trade["action"] == "BUY" and prev_trade["date"] < trade["date"]:
                    buy_cost = prev_trade["price"] * prev_trade["shares"]
                    sell_proceeds = trade["price"] * trade["shares"]
                    gain = sell_proceeds - buy_cost
                    
                    if gain > 0:
                        win_trades += 1
                    total_gain += gain
        
        win_rate = (win_trades / len(sell_trades) * 100) if sell_trades else 0
        
        results = {
            "ticker": self.ticker,
            "period": f"{self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}",
            "initial_capital": self.initial_capital,
            "final_value": round(final_value, 0),
            "total_return": round(returns, 2),
            "cagr": round(cagr, 2),
            "mdd": round(mdd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "num_trades": len(self.trades),
            "num_buy": len([t for t in self.trades if t["action"] == "BUY"]),
            "num_sell": len([t for t in self.trades if t["action"] == "SELL"]),
            "win_rate": round(win_rate, 1),
            "avg_gain_per_trade": round(total_gain / len(self.trades), 0) if self.trades else 0,
            "trades": self.trades,
            "daily_values": self.daily_values,
        }
        
        return results
    
    def save_results(self, results: dict, filename: str = BACKTEST_CSV) -> str:
        """결과를 CSV에 저장."""
        if not results or "error" in results:
            return None
        
        df = pd.DataFrame([{
            "ticker": results["ticker"],
            "period": results["period"],
            "initial": results["initial_capital"],
            "final": results["final_value"],
            "return": results["total_return"],
            "cagr": results["cagr"],
            "mdd": results["mdd"],
            "sharpe": results["sharpe_ratio"],
            "trades": results["num_trades"],
            "win_rate": results["win_rate"],
        }])
        
        # 기존 파일이 있으면 append
        existing = pd.DataFrame()
        try:
            existing = pd.read_csv(filename)
        except:
            pass
        
        df = pd.concat([existing, df], ignore_index=True)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        
        logger.info(f"백테스트 결과 저장: {filename}")
        return filename


def compare_backtests(tickers: list[str]) -> pd.DataFrame:
    """여러 종목 백테스트 비교."""
    results = []
    
    for ticker in tickers:
        engine = BacktestEngine(ticker)
        result = engine.run()
        
        if result and "error" not in result:
            results.append(result)
    
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame([{
        "ticker": r["ticker"],
        "return": r["total_return"],
        "cagr": r["cagr"],
        "mdd": r["mdd"],
        "sharpe": r["sharpe_ratio"],
        "trades": r["num_trades"],
        "win_rate": r["win_rate"],
    } for r in results])
    
    return df.sort_values("cagr", ascending=False)
