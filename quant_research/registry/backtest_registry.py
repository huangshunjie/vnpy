"""
quant_research/registry/backtest_registry.py

BacktestRegistry — Phase 7 完整实现。
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..model.backtest_model import BacktestRecord, DailyEquity
from ..constant import BacktestStatus


class BacktestRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, BacktestRecord] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: BacktestRecord) -> BacktestRecord:
        self._records[record.backtest_id] = record
        return record

    def get(self, backtest_id: str) -> Optional[BacktestRecord]:
        return self._records.get(backtest_id)

    def list(self) -> List[BacktestRecord]:
        return list(self._records.values())

    def update(self, record: BacktestRecord) -> None:
        self._records[record.backtest_id] = record

    def delete(self, backtest_id: str) -> None:
        self._records.pop(backtest_id, None)

    def clear(self) -> None:
        self._records.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        status:      Optional[BacktestStatus] = None,
        strategy_id: Optional[str]            = None,
        tag:         Optional[str]            = None,
    ) -> List[BacktestRecord]:
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if strategy_id is not None:
            result = [r for r in result if r.strategy_id == strategy_id]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        return result

    def search(self, keyword: str) -> List[BacktestRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.name.lower()
            or kw in r.description.lower()
            or kw in r.strategy_id.lower()
            or kw in r.strategy_name.lower()
            or kw in r.universe.lower()
            or any(kw in t.lower() for t in r.tags)
        ]

    # ------------------------------------------------------------------
    # 状态流转
    # ------------------------------------------------------------------

    def submit(self, backtest_id: str) -> None:
        r = self._records.get(backtest_id)
        if r:
            r.status       = BacktestStatus.RUNNING
            r.submitted_at = datetime.now()
            r.updated_at   = datetime.now()

    def complete(
        self,
        backtest_id:    str,
        annual_return:  float = 0.0,
        max_drawdown:   float = 0.0,
        sharpe:         float = 0.0,
        sortino:        float = 0.0,
        calmar:         float = 0.0,
        win_rate:       float = 0.0,
        turnover:       float = 0.0,
        profit_factor:  float = 0.0,
        total_return:   float = 0.0,
        alpha:          float = 0.0,
        beta:           float = 0.0,
        information_ratio: float = 0.0,
        total_trades:   int   = 0,
        avg_holding_days: float = 0.0,
        max_position_conc: float = 0.0,
        equity_curve:   Optional[List[DailyEquity]] = None,
        monthly_returns: Optional[Dict[str, float]] = None,
    ) -> None:
        r = self._records.get(backtest_id)
        if r is None:
            return
        r.status           = BacktestStatus.COMPLETED
        r.annual_return    = annual_return
        r.max_drawdown     = max_drawdown
        r.sharpe           = sharpe
        r.sortino          = sortino
        r.calmar           = calmar
        r.win_rate         = win_rate
        r.turnover         = turnover
        r.profit_factor    = profit_factor
        r.total_return     = total_return
        r.alpha            = alpha
        r.beta             = beta
        r.information_ratio = information_ratio
        r.total_trades     = total_trades
        r.avg_holding_days = avg_holding_days
        r.max_position_conc = max_position_conc
        r.equity_curve     = equity_curve or []
        r.monthly_returns  = monthly_returns or {}
        r.completed_at     = datetime.now()
        r.updated_at       = datetime.now()

    def fail(self, backtest_id: str, error_msg: str = "") -> None:
        r = self._records.get(backtest_id)
        if r:
            r.status     = BacktestStatus.FAILED
            r.error_msg  = error_msg
            r.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # 关联资源
    # ------------------------------------------------------------------

    def link_model(self, backtest_id: str, model_id: str) -> None:
        r = self._records.get(backtest_id)
        if r and model_id not in r.model_ids:
            r.model_ids.append(model_id)
            r.updated_at = datetime.now()

    def unlink_model(self, backtest_id: str, model_id: str) -> None:
        r = self._records.get(backtest_id)
        if r and model_id in r.model_ids:
            r.model_ids.remove(model_id)
            r.updated_at = datetime.now()

    def link_feature(self, backtest_id: str, feature_id: str) -> None:
        r = self._records.get(backtest_id)
        if r and feature_id not in r.feature_ids:
            r.feature_ids.append(feature_id)
            r.updated_at = datetime.now()

    def link_dataset(self, backtest_id: str, dataset_id: str) -> None:
        r = self._records.get(backtest_id)
        if r and dataset_id not in r.dataset_ids:
            r.dataset_ids.append(dataset_id)
            r.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # 对比 / 排行
    # ------------------------------------------------------------------

    def compare(self, backtest_ids: List[str]) -> List[BacktestRecord]:
        return [
            self._records[bid]
            for bid in backtest_ids
            if bid in self._records
        ]

    def top_by_sharpe(self, n: int = 10) -> List[BacktestRecord]:
        completed = [r for r in self._records.values()
                     if r.status == BacktestStatus.COMPLETED]
        return sorted(completed, key=lambda r: r.sharpe, reverse=True)[:n]

    def top_by_return(self, n: int = 10) -> List[BacktestRecord]:
        completed = [r for r in self._records.values()
                     if r.status == BacktestStatus.COMPLETED]
        return sorted(completed, key=lambda r: r.annual_return, reverse=True)[:n]
