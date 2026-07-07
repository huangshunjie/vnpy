"""
quant_research/registry/strategy_registry.py

StrategyRegistry — Phase 5 完整实现。
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from ..model.strategy_model import StrategyRecord, StrategyVersion
from ..constant import StrategyStatus


class StrategyRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, StrategyRecord] = {}
        self._ver_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: StrategyRecord) -> StrategyRecord:
        self._records[record.strategy_id] = record
        return record

    def get(self, strategy_id: str) -> Optional[StrategyRecord]:
        return self._records.get(strategy_id)

    def list(self) -> List[StrategyRecord]:
        return list(self._records.values())

    def update(self, record: StrategyRecord) -> None:
        self._records[record.strategy_id] = record

    def delete(self, strategy_id: str) -> None:
        self._records.pop(strategy_id, None)

    def clear(self) -> None:
        self._records.clear()
        self._ver_counter.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        status:        Optional[StrategyStatus] = None,
        strategy_type: Optional[str]            = None,
        tag:           Optional[str]            = None,
        author:        Optional[str]            = None,
    ) -> List[StrategyRecord]:
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if strategy_type is not None:
            result = [r for r in result
                      if strategy_type.lower() in r.strategy_type.lower()]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        if author is not None:
            result = [r for r in result
                      if author.lower() in r.author.lower()]
        return result

    def search(self, keyword: str) -> List[StrategyRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.name.lower()
            or kw in r.description.lower()
            or kw in r.strategy_type.lower()
            or kw in r.author.lower()
            or kw in r.universe.lower()
            or any(kw in t.lower() for t in r.tags)
        ]

    # ------------------------------------------------------------------
    # 绩效更新
    # ------------------------------------------------------------------

    def update_performance(
        self,
        strategy_id:   str,
        annual_return: float = 0.0,
        max_drawdown:  float = 0.0,
        sharpe:        float = 0.0,
        sortino:       float = 0.0,
        calmar:        float = 0.0,
        win_rate:      float = 0.0,
        turnover:      float = 0.0,
        profit_factor: float = 0.0,
    ) -> None:
        record = self._records.get(strategy_id)
        if record:
            record.annual_return  = annual_return
            record.max_drawdown   = max_drawdown
            record.sharpe         = sharpe
            record.sortino        = sortino
            record.calmar         = calmar
            record.win_rate       = win_rate
            record.turnover       = turnover
            record.profit_factor  = profit_factor
            record.updated_at     = datetime.now()

    # ------------------------------------------------------------------
    # 状态流转
    # ------------------------------------------------------------------

    def publish(self, strategy_id: str) -> None:
        record = self._records.get(strategy_id)
        if record:
            record.status       = StrategyStatus.LIVE
            record.published_at = datetime.now()
            record.updated_at   = datetime.now()

    def retire(self, strategy_id: str) -> None:
        record = self._records.get(strategy_id)
        if record:
            record.status     = StrategyStatus.RETIRED
            record.retired_at = datetime.now()
            record.updated_at = datetime.now()

    def set_testing(self, strategy_id: str) -> None:
        record = self._records.get(strategy_id)
        if record:
            record.status     = StrategyStatus.TESTING
            record.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # 版本历史
    # ------------------------------------------------------------------

    def add_version(
        self,
        strategy_id: str,
        note:        str = "",
        created_by:  str = "",
    ) -> Optional[StrategyVersion]:
        record = self._records.get(strategy_id)
        if record is None:
            return None
        count = self._ver_counter.get(strategy_id, 0) + 1
        self._ver_counter[strategy_id] = count
        ver = StrategyVersion(
            version_id  = f"VER-{strategy_id}-{count:03d}",
            strategy_id = strategy_id,
            version     = record.version,
            note        = note,
            params      = dict(record.params),
            created_at  = datetime.now(),
            created_by  = created_by,
        )
        record.versions.append(ver)
        record.updated_at = datetime.now()
        return ver

    def get_versions(self, strategy_id: str) -> List[StrategyVersion]:
        record = self._records.get(strategy_id)
        return list(record.versions) if record else []

    # ------------------------------------------------------------------
    # 关联资源
    # ------------------------------------------------------------------

    def link_feature(self, strategy_id: str, feature_id: str) -> None:
        record = self._records.get(strategy_id)
        if record and feature_id not in record.feature_ids:
            record.feature_ids.append(feature_id)
            record.updated_at = datetime.now()

    def unlink_feature(self, strategy_id: str, feature_id: str) -> None:
        record = self._records.get(strategy_id)
        if record and feature_id in record.feature_ids:
            record.feature_ids.remove(feature_id)
            record.updated_at = datetime.now()

    def link_backtest(self, strategy_id: str, backtest_id: str) -> None:
        record = self._records.get(strategy_id)
        if record and backtest_id not in record.backtest_ids:
            record.backtest_ids.append(backtest_id)
            record.updated_at = datetime.now()

    def unlink_backtest(self, strategy_id: str, backtest_id: str) -> None:
        record = self._records.get(strategy_id)
        if record and backtest_id in record.backtest_ids:
            record.backtest_ids.remove(backtest_id)
            record.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # 排行榜
    # ------------------------------------------------------------------

    def top_by_sharpe(self, n: int = 10) -> List[StrategyRecord]:
        active = [r for r in self._records.values()
                  if r.status != StrategyStatus.RETIRED]
        return sorted(active, key=lambda r: r.sharpe, reverse=True)[:n]

    def top_by_return(self, n: int = 10) -> List[StrategyRecord]:
        active = [r for r in self._records.values()
                  if r.status != StrategyStatus.RETIRED]
        return sorted(active, key=lambda r: r.annual_return, reverse=True)[:n]
