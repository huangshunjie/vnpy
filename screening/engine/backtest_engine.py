"""
screening/engine/backtest_engine.py
Backtest Engine — Phase 7
"""
from __future__ import annotations
import math, uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class BacktestConfig:
    start_date:     str   = "2021-01-01"
    end_date:       str   = ""
    capital:        float = 1_000_000.0
    top_n:          int   = 20
    rebalance_days: int   = 20
    commission:     float = 0.0003
    slippage:       float = 0.001
    risk_free_rate: float = 0.02
    annual_days:    int   = 252

    def to_dict(self) -> dict:
        return {"start_date": self.start_date, "end_date": self.end_date or "today",
                "capital": self.capital, "top_n": self.top_n,
                "rebalance_days": self.rebalance_days,
                "commission": self.commission, "slippage": self.slippage}

    @classmethod
    def default(cls) -> "BacktestConfig":
        return cls()


@dataclass
class DailyRecord:
    date:     str
    nav:      float
    pnl:      float
    turnover: float = 0.0


@dataclass
class BacktestResult:
    run_id:           str
    config:           BacktestConfig
    daily_records:    List[DailyRecord] = field(default_factory=list)
    total_return:     float = 0.0
    annual_return:    float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio:     float = 0.0
    calmar_ratio:     float = 0.0
    win_rate:         float = 0.0
    total_days:       int   = 0
    generated_at:     datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {"run_id": self.run_id,
                "total_return":     round(self.total_return, 4),
                "annual_return":    round(self.annual_return, 4),
                "max_drawdown_pct": round(self.max_drawdown_pct, 4),
                "sharpe_ratio":     round(self.sharpe_ratio, 4),
                "calmar_ratio":     round(self.calmar_ratio, 4),
                "win_rate":         round(self.win_rate, 4),
                "total_days":       self.total_days,
                "generated_at":     str(self.generated_at)[:19]}


def _date_range(start: str, end: str) -> List[date]:
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end) if end else date.today()
    result, cur = [], d0
    while cur <= d1:
        result.append(cur); cur += timedelta(days=1)
    return result


def _compute_metrics(nav_series: List[float], annual_days: int = 252,
                     risk_free: float = 0.02) -> dict:
    n = len(nav_series)
    if n < 2:
        return {"total_return": 0.0, "annual_return": 0.0,
                "max_drawdown_pct": 0.0, "sharpe_ratio": 0.0,
                "calmar_ratio": 0.0, "win_rate": 0.0}
    total_return = nav_series[-1] / nav_series[0] - 1.0
    years = n / annual_days
    annual_return = (1 + total_return) ** (1 / max(years, 1e-9)) - 1.0
    peak, max_dd_pct = nav_series[0], 0.0
    for nav in nav_series:
        if nav > peak: peak = nav
        dd = (peak - nav) / peak if peak > 0 else 0.0
        if dd > max_dd_pct: max_dd_pct = dd
    daily_rets = [nav_series[i] / nav_series[i-1] - 1.0 for i in range(1, n)]
    win_rate = sum(1 for r in daily_rets if r > 0) / len(daily_rets) if daily_rets else 0.0
    if daily_rets:
        mu = sum(daily_rets) / len(daily_rets)
        std = math.sqrt(sum((r - mu)**2 for r in daily_rets) / len(daily_rets)) or 1e-9
        sharpe = (mu - risk_free / annual_days) / std * math.sqrt(annual_days)
    else:
        sharpe = 0.0
    calmar = annual_return / max_dd_pct if max_dd_pct > 1e-9 else 0.0
    return {"total_return": total_return, "annual_return": annual_return,
            "max_drawdown_pct": max_dd_pct, "sharpe_ratio": sharpe,
            "calmar_ratio": calmar, "win_rate": win_rate}


class BacktestEngine:
    """选股组合回测引擎（Phase 7）。"""

    def __init__(self, log_fn=None, main_engine=None):
        self._log = log_fn or print
        self._main_engine = main_engine
        self._config = BacktestConfig.default()
        self._last_result = None

    def set_config(self, config): self._config = config
    def get_config(self): return self._config
    def set_main_engine(self, me): self._main_engine = me
    def get_last_result(self): return self._last_result

    def run_backtest(self, symbols, scores=None):
        if not symbols:
            self._log("[BacktestEngine] 股票池为空"); return None
        import uuid as _uuid
        self._log(f"[BacktestEngine] 开始回测：{len(symbols)} 只，Top {self._config.top_n}")
        t0 = datetime.now()
        run_id = str(_uuid.uuid4())[:8]
        ranked = sorted(symbols, key=lambda s: (scores or {}).get(s, 0.0), reverse=True)
        portfolio = ranked[:self._config.top_n]
        returns_map = self._load_returns(portfolio)
        if not returns_map:
            self._log("[BacktestEngine] 无真实数据，使用模拟收益率")
            returns_map = self._simulate_returns(portfolio)
        daily_records, nav_series = self._build_nav_curve(returns_map)
        if not nav_series:
            return None
        metrics = _compute_metrics(nav_series, self._config.annual_days, self._config.risk_free_rate)
        elapsed = (datetime.now() - t0).total_seconds()
        self._last_result = BacktestResult(
            run_id=run_id, config=self._config, daily_records=daily_records,
            total_return=metrics["total_return"], annual_return=metrics["annual_return"],
            max_drawdown_pct=metrics["max_drawdown_pct"], sharpe_ratio=metrics["sharpe_ratio"],
            calmar_ratio=metrics["calmar_ratio"], win_rate=metrics["win_rate"],
            total_days=len(daily_records))
        self._log(
            f"[BacktestEngine] 完成 {elapsed:.2f}s | 收益 {metrics['total_return']:.2%} | "
            f"年化 {metrics['annual_return']:.2%} | MaxDD {metrics['max_drawdown_pct']:.2%} | "
            f"Sharpe {metrics['sharpe_ratio']:.2f}")
        return self._last_result

    def _load_returns(self, symbols):
        if self._main_engine is None: return {}
        result = {}
        try:
            from vnpy.trader.constant import Exchange, Interval
            from datetime import datetime as dt
            start = dt.fromisoformat(self._config.start_date)
            end = dt.fromisoformat(self._config.end_date) if self._config.end_date else dt.now()
            db = self._main_engine.get_database()
            if db is None: return {}
            for sym in symbols:
                parts = sym.split(".")
                if len(parts) != 2: continue
                code, exch_str = parts
                try:
                    exchange = Exchange(exch_str)
                    bars = db.load_bar_data(symbol=code, exchange=exchange,
                        interval=Interval.DAILY, start=start, end=end)
                    if len(bars) < 5: continue
                    rets = []
                    for i in range(1, len(bars)):
                        p0, p1 = bars[i-1].close_price, bars[i].close_price
                        if p0 > 0:
                            rets.append((str(bars[i].datetime.date()), (p1 - p0) / p0))
                    if rets: result[sym] = rets
                except Exception: pass
        except Exception: pass
        return result

    def _simulate_returns(self, symbols):
        import hashlib, random
        start = date.fromisoformat(self._config.start_date)
        end_str = self._config.end_date
        end = date.fromisoformat(end_str) if end_str else date.today()
        all_dates = [d for d in _date_range(str(start), str(end)) if d.weekday() < 5]
        result = {}
        for sym in symbols:
            h = int(hashlib.md5(sym.encode()).hexdigest(), 16)
            rng = random.Random(h % (2**32))
            alpha = (h % 200 - 100) / 100000.0
            result[sym] = [(str(d), rng.gauss(0.0003 + alpha, 0.015)) for d in all_dates]
        return result

    def _build_nav_curve(self, returns_map):
        if not returns_map: return [], []
        date_sets = [set(d for d, _ in v) for v in returns_map.values()]
        common = sorted(date_sets[0].intersection(*date_sets[1:]) if len(date_sets) > 1 else date_sets[0])
        if not common:
            union = set()
            for v in returns_map.values(): union.update(d for d, _ in v)
            common = sorted(union)
        ret_by_date = {d: {} for d in common}
        for sym, rets in returns_map.items():
            for d, r in rets:
                if d in ret_by_date: ret_by_date[d][sym] = r
        nav, nav_series = 1.0, [1.0]
        records = [DailyRecord(date=common[0], nav=1.0, pnl=0.0)]
        rb, comm, slip = self._config.rebalance_days, self._config.commission, self._config.slippage
        for idx, d in enumerate(common[1:], 1):
            day_rets = ret_by_date.get(d, {})
            if not day_rets:
                records.append(DailyRecord(date=d, nav=nav, pnl=0.0)); nav_series.append(nav); continue
            avg_ret = sum(day_rets.values()) / len(day_rets)
            cost = (comm + slip) * 2 if idx % rb == 0 else 0.0
            pnl = nav * (avg_ret - cost)
            nav += pnl; nav_series.append(nav)
            records.append(DailyRecord(date=d, nav=nav, pnl=pnl,
                turnover=1.0 if idx % rb == 0 else 0.0))
        return records, nav_series

    def summary(self):
        if self._last_result: return self._last_result.to_dict()
        return {"status": "no_backtest"}
