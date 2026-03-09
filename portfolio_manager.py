# ============================================================
# portfolio_manager.py - 포트폴리오 추적 및 성과 분석
# ============================================================
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
from config import PORTFOLIO_CSV, PORTFOLIO_CASH_INIT
from data_collector import fetch_current_price

logger = logging.getLogger("StockAI.Portfolio")


# ── 포트폴리오 클래스 ──────────────────────────────────
class Portfolio:
    """매수/매도 거래 기록 및 포트폴리오 분석."""
    
    def __init__(self, initial_cash: float = PORTFOLIO_CASH_INIT):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings = {}  # {ticker: {"shares": n, "avg_price": p, "market": "KOSPI"}}
        self.transactions = []  # [{"date": ..., "ticker": ..., "action": "buy"|"sell", ...}]
        self._load_portfolio()
    
    def _load_portfolio(self) -> None:
        """CSV에서 포트폴리오 로드."""
        if os.path.exists(PORTFOLIO_CSV):
            try:
                df = pd.read_csv(PORTFOLIO_CSV, dtype={"ticker": str, "shares": float})
                for _, row in df.iterrows():
                    ticker = row["ticker"]
                    self.holdings[ticker] = {
                        "shares": float(row["shares"]),
                        "avg_price": float(row["avg_price"]),
                        "market": row.get("market", "KOSPI"),
                        "buy_value": float(row.get("buy_value", 0)),
                    }
                self.cash = float(df.get("_cash", [self.initial_cash]).iloc[0]) if "_cash" in df.columns else self.initial_cash
                logger.info(f"포트폴리오 로드 완료: {len(self.holdings)} 종목")
            except Exception as e:
                logger.warning(f"포트폴리오 로드 실패: {e}")
    
    def _save_portfolio(self) -> None:
        """포트폴리오를 CSV에 저장."""
        rows = []
        for ticker, info in self.holdings.items():
            if info["shares"] > 0:  # 0 이상 보유 종목만
                rows.append({
                    "ticker": ticker,
                    "shares": info["shares"],
                    "avg_price": info["avg_price"],
                    "market": info["market"],
                    "buy_value": info["buy_value"],
                })
        
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(PORTFOLIO_CSV, index=False, encoding="utf-8-sig")
            logger.info(f"포트폴리오 저장: {len(rows)} 종목")
    
    def buy(self, ticker: str, shares: float, price: float, market: str = "KOSPI") -> dict:
        """
        매수 처리.
        반환: {"status": "success"|"insufficient_cash", "cash_left": ...}
        """
        cost = shares * price
        commission = cost * 0.003  # 거래수수료 0.3%
        total_cost = cost + commission
        
        if total_cost > self.cash:
            logger.warning(f"자금부족: {ticker} 매수 불가")
            return {"status": "insufficient_cash", "required": total_cost, "available": self.cash}
        
        self.cash -= total_cost
        
        # 보유중인 경우: 평균 단가 업데이트
        if ticker in self.holdings:
            old_shares = self.holdings[ticker]["shares"]
            old_avg = self.holdings[ticker]["avg_price"]
            new_shares = old_shares + shares
            new_avg = (old_shares * old_avg + shares * price) / new_shares
            
            self.holdings[ticker]["shares"] = new_shares
            self.holdings[ticker]["avg_price"] = new_avg
            self.holdings[ticker]["buy_value"] = new_shares * new_avg
        else:
            self.holdings[ticker] = {
                "shares": shares,
                "avg_price": price,
                "market": market,
                "buy_value": shares * price,
            }
        
        # 거래 기록
        self.transactions.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ticker": ticker,
            "action": "buy",
            "shares": shares,
            "price": price,
            "commission": commission,
            "total": total_cost,
        })
        
        self._save_portfolio()
        logger.info(f"매수: {ticker} {shares}주 @ {price}원")
        
        return {"status": "success", "cash_left": round(self.cash, 0)}
    
    def sell(self, ticker: str, shares: float, price: float) -> dict:
        """
        매도 처리.
        반환: {"status": "success"|"insufficient_shares", "proceeds": ...}
        """
        if ticker not in self.holdings or self.holdings[ticker]["shares"] < shares:
            return {
                "status": "insufficient_shares",
                "available": self.holdings.get(ticker, {}).get("shares", 0)
            }
        
        proceeds = shares * price
        commission = proceeds * 0.003
        net_proceeds = proceeds - commission
        
        avg_cost = self.holdings[ticker]["avg_price"]
        gain = (price - avg_cost) * shares
        gain_pct = (gain / (avg_cost * shares)) * 100 if avg_cost > 0 else 0
        
        self.cash += net_proceeds
        self.holdings[ticker]["shares"] -= shares
        self.holdings[ticker]["buy_value"] = self.holdings[ticker]["shares"] * avg_cost
        
        # 0 주면 제거
        if self.holdings[ticker]["shares"] == 0:
            del self.holdings[ticker]
        
        # 거래 기록
        self.transactions.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ticker": ticker,
            "action": "sell",
            "shares": shares,
            "price": price,
            "commission": commission,
            "gain": round(gain, 0),
            "gain_pct": round(gain_pct, 2),
            "proceeds": net_proceeds,
        })
        
        self._save_portfolio()
        logger.info(f"매도: {ticker} {shares}주 @ {price}원 (수익률: {gain_pct:.1f}%)")
        
        return {
            "status": "success",
            "proceeds": round(net_proceeds, 0),
            "gain": round(gain, 0),
            "gain_pct": round(gain_pct, 2)
        }
    
    def get_current_value(self) -> dict:
        """
        현재 포트폴리오 평가액.
        반환: {"total_value": ..., "securities_value": ..., "cash": ..., "details": [...]}
        """
        securities_value = 0
        details = []
        
        for ticker, info in self.holdings.items():
            current_price = fetch_current_price(ticker, market=info["market"])
            if current_price is None:
                current_price = info["avg_price"]  # 수집 실패시 평균단가 사용
            
            market_value = info["shares"] * current_price
            cost_value = info["shares"] * info["avg_price"]
            gain = market_value - cost_value
            gain_pct = (gain / cost_value) * 100 if cost_value > 0 else 0
            
            securities_value += market_value
            details.append({
                "ticker": ticker,
                "shares": info["shares"],
                "avg_price": round(info["avg_price"], 0),
                "current_price": round(current_price, 0),
                "market_value": round(market_value, 0),
                "cost_value": round(cost_value, 0),
                "gain": round(gain, 0),
                "gain_pct": round(gain_pct, 2),
            })
        
        total_value = securities_value + self.cash
        
        return {
            "total_value": round(total_value, 0),
            "securities_value": round(securities_value, 0),
            "cash": round(self.cash, 0),
            "return_rate": round(((total_value - self.initial_cash) / self.initial_cash) * 100, 2),
            "details": details,
        }
    
    def get_allocation(self) -> dict:
        """자산 배분율."""
        current = self.get_current_value()
        total = current["total_value"]
        
        if total == 0:
            return {"cash": 100, "securities": 0, "by_sector": {}}
        
        return {
            "cash": round((current["cash"] / total) * 100, 2),
            "securities": round((current["securities_value"] / total) * 100, 2),
            "num_holdings": len(self.holdings),
        }
    
    def get_transaction_history(self, limit: int = 50) -> list[dict]:
        """거래 이력 조회."""
        return sorted(self.transactions, key=lambda x: x["date"], reverse=True)[:limit]
    
    def get_performance_stats(self) -> dict:
        """포트폴리오 성과통계."""
        if not self.transactions:
            return {"trades": 0, "win_rate": 0, "avg_gain": 0, "best_trade": None, "worst_trade": None}
        
        sell_trades = [t for t in self.transactions if t["action"] == "sell"]
        
        if not sell_trades:
            return {"trades": len(sell_trades), "win_rate": 0, "avg_gain": 0}
        
        gains = [t.get("gain_pct", 0) for t in sell_trades]
        winning_trades = len([g for g in gains if g > 0])
        
        return {
            "trades": len(sell_trades),
            "win_rate": round((winning_trades / len(sell_trades)) * 100, 1),
            "avg_gain": round(np.mean(gains), 2),
            "total_gain": round(sum([t.get("gain", 0) for t in sell_trades]), 0),
            "best_trade": round(max(gains), 2) if gains else 0,
            "worst_trade": round(min(gains), 2) if gains else 0,
        }


# ── 포트폴리오 헬퍼 함수 ───────────────────────────────

def create_sample_portfolio() -> Portfolio:
    """테스트용 샘플 포트폴리오 생성."""
    p = Portfolio()
    # 샘플 거래 추가 가능
    return p


def export_portfolio_report(portfolio: Portfolio, filename: str = "portfolio_report.csv") -> str:
    """포트폴리오 리포트 내보내기."""
    current = portfolio.get_current_value()
    stats = portfolio.get_performance_stats()
    
    summary = f"=== 포트폴리오 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===\n"
    summary += f"총자산: {current['total_value']:,}원\n"
    summary += f"증권: {current['securities_value']:,}원\n"
    summary += f"현금: {current['cash']:,}원\n"
    summary += f"수익률: {current['return_rate']:.2f}%\n"
    summary += f"\n거래 {stats['trades']}건 (승률: {stats['win_rate']:.1f}%)\n"
    
    df = pd.DataFrame(current["details"])
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    
    logger.info(f"포트폴리오 리포트 저장: {filename}")
    return summary
