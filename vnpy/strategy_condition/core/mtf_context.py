"""Multi-Timeframe Context for Condition Engine"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
from vnpy.trader.constant import Interval
from .condition_tree import ConditionNode
from ..constant import NodeOp

@dataclass
class MultiTimeframeContext:
    symbol: str
    evaluation_time: Optional[datetime] = None
    bars_by_interval: Dict[Interval, list] = field(default_factory=dict)
    def set_bars(self, interval: Interval, bars: list) -> None:
        self.bars_by_interval[interval] = bars
    def get_bars(self, interval: Interval) -> list:
        return self.bars_by_interval.get(interval, [])
    def has_interval(self, interval: Interval) -> bool:
        return interval in self.bars_by_interval and len(self.bars_by_interval[interval]) > 0
    def get_available_intervals(self) -> list:
        return [i for i, bars in self.bars_by_interval.items() if bars]
    def __repr__(self) -> str:
        return f"MTFContext({self.symbol}, intervals={[i.value for i in self.get_available_intervals()]})"

@dataclass
class DataRequirement:
    strategy_execution_interval: Interval
    intervals: Set[Interval] = field(default_factory=set)
    def add_interval(self, interval: Interval) -> None:
        self.intervals.add(interval)
    @property
    def required_intervals(self) -> Set[Interval]:
        """兼容别名，widget.py 使用此属性"""
        return self.intervals
    @required_intervals.setter
    def required_intervals(self, value):
        """允许 mtf_auto_loader 设置（忽略，因为 intervals 已是源数据）"""
        pass  # intervals 已经是权威数据源，忽略外部赋值
    @property
    def execution_interval(self) -> Interval:
        """兼容别名"""
        return self.strategy_execution_interval
    @execution_interval.setter
    def execution_interval(self, value):
        """允许 mtf_auto_loader 设置"""
        self.strategy_execution_interval = value
    def __repr__(self) -> str:
        return f"DataReq(exec={self.strategy_execution_interval.value}, need={[i.value for i in self.intervals]})"

def analyze_data_requirements(condition_tree: ConditionNode, strategy_execution_interval: Interval) -> DataRequirement:
    req = DataRequirement(strategy_execution_interval=strategy_execution_interval)
    has_unspecified_condition = False  # 是否有条件未指定周期

    def _walk(node) -> None:
        nonlocal has_unspecified_condition
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if not isinstance(node, ConditionNode):
            return
        if node.op == NodeOp.LEAF:
            # 尝试从多个位置获取 data_interval
            interval = None
            if node.condition:
                # 优先从 data_interval 属性获取
                if hasattr(node.condition, 'data_interval') and node.condition.data_interval:
                    interval = node.condition.data_interval
                # 兼容旧版：从 params["_data_interval"] 获取
                elif "_data_interval" in node.condition.params:
                    interval_str = node.condition.params["_data_interval"]
                    if interval_str:
                        try:
                            interval = Interval(interval_str)
                        except:
                            pass

            if interval:
                req.add_interval(interval)
            else:
                # 没有明确指定周期的条件，使用策略执行周期
                has_unspecified_condition = True
                req.add_interval(strategy_execution_interval)
        else:
            for child in node.children:
                _walk(child)
    _walk(condition_tree)

    # 关键优化：如果所有条件都明确指定了同一个周期（且非执行周期），
    # 则将 strategy_execution_interval 更新为该周期，避免误判为多周期策略。
    # 例：所有条件都是5m，UI选了日线 → 实际应按5m单周期执行
    if not has_unspecified_condition and len(req.intervals) == 1:
        only_interval = next(iter(req.intervals))
        if only_interval != strategy_execution_interval:
            req.strategy_execution_interval = only_interval

    return req
