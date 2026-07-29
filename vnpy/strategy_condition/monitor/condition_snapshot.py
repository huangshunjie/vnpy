"""
strategy_condition/monitor/condition_snapshot.py
条件监控数据模型：ConditionDetail / ConditionSnapshot / StateChangeEvent

设计原则：
  - 纯数据容器，不包含任何计算逻辑
  - 支持序列化（to_dict / from_dict）以便持久化和回放
  - 每根K线对应一个 ConditionSnapshot，记录所有条件的完整评估状态
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ConditionDetail:
    """
    单个叶节点条件在某根K线上的评估详情。

    Attributes:
        condition_name: 条件显示名称 (e.g. "MA5斜率向上")
        indicator: ConditionIndicator.value (e.g. "MA_SLOPE")
        passed: 该条件是否通过
        score: 评分 [0, 1]
        current_value: 当前指标计算值 (e.g. 11.02)
        threshold_desc: 阈值描述文字 (e.g. "斜率 > 0.0")
        params: 条件参数副本
    """
    condition_name: str
    indicator: str
    passed: bool
    score: float = 0.0
    current_value: Optional[float] = None
    threshold_desc: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_name": self.condition_name,
            "indicator": self.indicator,
            "passed": self.passed,
            "score": round(self.score, 4),
            "current_value": round(self.current_value, 4) if self.current_value is not None else None,
            "threshold_desc": self.threshold_desc,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConditionDetail":
        return cls(
            condition_name=d["condition_name"],
            indicator=d["indicator"],
            passed=d["passed"],
            score=d.get("score", 0.0),
            current_value=d.get("current_value"),
            threshold_desc=d.get("threshold_desc", ""),
            params=d.get("params", {}),
        )


@dataclass
class ConditionSnapshot:
    """
    一根K线上所有条件的完整评估快照。

    Attributes:
        dt: K线时间
        symbol: 股票代码
        price: 收盘价
        bar_index: 在bars序列中的索引位置

        buy_details: 买入条件逐条评估详情
        sell_details: 卖出条件逐条评估详情

        buy_passed_count: 买入条件通过数量
        buy_total_count: 买入条件总数量
        buy_result: 最终买入条件树是否通过
        buy_score: 买入综合评分

        sell_passed_count: 卖出条件通过数量
        sell_total_count: 卖出条件总数量
        sell_result: 最终卖出条件树是否通过
        sell_score: 卖出综合评分

        signal_type: "BUY" / "SELL" / None
    """
    dt: datetime
    symbol: str
    price: float
    bar_index: int = 0

    buy_details: List[ConditionDetail] = field(default_factory=list)
    sell_details: List[ConditionDetail] = field(default_factory=list)

    buy_passed_count: int = 0
    buy_total_count: int = 0
    buy_result: bool = False
    buy_score: float = 0.0

    sell_passed_count: int = 0
    sell_total_count: int = 0
    sell_result: bool = False
    sell_score: float = 0.0

    signal_type: Optional[str] = None  # "BUY" / "SELL" / None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dt": str(self.dt)[:19],
            "symbol": self.symbol,
            "price": round(self.price, 4),
            "bar_index": self.bar_index,
            "buy_details": [d.to_dict() for d in self.buy_details],
            "sell_details": [d.to_dict() for d in self.sell_details],
            "buy_passed_count": self.buy_passed_count,
            "buy_total_count": self.buy_total_count,
            "buy_result": self.buy_result,
            "buy_score": round(self.buy_score, 4),
            "sell_passed_count": self.sell_passed_count,
            "sell_total_count": self.sell_total_count,
            "sell_result": self.sell_result,
            "sell_score": round(self.sell_score, 4),
            "signal_type": self.signal_type,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConditionSnapshot":
        return cls(
            dt=datetime.strptime(d["dt"][:19], "%Y-%m-%d %H:%M:%S") if isinstance(d["dt"], str) else d["dt"],
            symbol=d["symbol"],
            price=d["price"],
            bar_index=d.get("bar_index", 0),
            buy_details=[ConditionDetail.from_dict(x) for x in d.get("buy_details", [])],
            sell_details=[ConditionDetail.from_dict(x) for x in d.get("sell_details", [])],
            buy_passed_count=d.get("buy_passed_count", 0),
            buy_total_count=d.get("buy_total_count", 0),
            buy_result=d.get("buy_result", False),
            buy_score=d.get("buy_score", 0.0),
            sell_passed_count=d.get("sell_passed_count", 0),
            sell_total_count=d.get("sell_total_count", 0),
            sell_result=d.get("sell_result", False),
            sell_score=d.get("sell_score", 0.0),
            signal_type=d.get("signal_type"),
        )

    @property
    def buy_summary(self) -> str:
        """买入条件摘要文字"""
        return f"{self.buy_passed_count}/{self.buy_total_count}"

    @property
    def sell_summary(self) -> str:
        """卖出条件摘要文字"""
        return f"{self.sell_passed_count}/{self.sell_total_count}"

    @property
    def has_signal(self) -> bool:
        """是否有买入或卖出信号"""
        return self.signal_type is not None


@dataclass
class StateChangeEvent:
    """
    条件状态变化事件：某个条件从 True→False 或 False→True。

    Attributes:
        dt: 变化发生的K线时间
        bar_index: 变化发生的K线索引
        condition_name: 条件显示名称
        indicator: ConditionIndicator.value
        old_state: 变化前状态
        new_state: 变化后状态
        side: "buy" / "sell"
    """
    dt: datetime
    bar_index: int
    condition_name: str
    indicator: str
    old_state: bool
    new_state: bool
    side: str = "buy"  # "buy" or "sell"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dt": str(self.dt)[:19],
            "bar_index": self.bar_index,
            "condition_name": self.condition_name,
            "indicator": self.indicator,
            "old_state": self.old_state,
            "new_state": self.new_state,
            "side": self.side,
        }

    @property
    def direction(self) -> str:
        """变化方向：'activated' (False→True) 或 'deactivated' (True→False)"""
        return "activated" if self.new_state else "deactivated"

    @property
    def description(self) -> str:
        """人类可读的变化描述"""
        arrow = "❌→✅" if self.new_state else "✅→❌"
        return f"{self.condition_name} {arrow}"