"""
strategy_condition/core/strategy.py

Strategy 数据模型：买入条件树 + 卖出条件树 + 元信息 + JSON 序列化。

设计原则：
- Strategy 是纯数据对象，不持有任何引擎引用
- 评估由 condition_engine 负责，strategy 只描述"规则是什么"
- 完整支持 JSON 序列化/反序列化，支持版本管理
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .condition_tree import ConditionNode
from ..constant import NodeOp


@dataclass
class StrategyMeta:
    """策略元信息"""
    name:        str
    version:     str        = "1.0.0"
    description: str        = ""
    author:      str        = ""
    created_at:  str        = field(default_factory=lambda: str(datetime.now())[:19])
    updated_at:  str        = field(default_factory=lambda: str(datetime.now())[:19])
    tags:        List[str]  = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":        self.name,
            "version":     self.version,
            "description": self.description,
            "author":      self.author,
            "created_at":  self.created_at,
            "updated_at":  self.updated_at,
            "tags":        self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StrategyMeta":
        return cls(
            name=        d.get("name", "未命名策略"),
            version=     d.get("version", "1.0.0"),
            description= d.get("description", ""),
            author=      d.get("author", ""),
            created_at=  d.get("created_at", ""),
            updated_at=  d.get("updated_at", ""),
            tags=        d.get("tags", []),
        )


@dataclass
class StrategyParams:
    """策略运行参数（选股/回测共用）"""
    max_hold_days:   int   = 60       # 最大持仓天数（兜底）
    stop_loss_pct:   float = 8.0      # 止损触发（%）
    take_profit_pct: float = 15.0     # 止盈触发（%）
    trail_drawdown:  float = 10.0     # 追踪止盈回撤（%）
    min_bars:        int   = 60       # 最少K线数（过滤新股）
    commission_rate: float = 0.0003   # 手续费率
    stamp_duty_rate: float = 0.001    # 印花税率
    slippage_rate:   float = 0.0002   # 滑点

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_hold_days":   self.max_hold_days,
            "stop_loss_pct":   self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "trail_drawdown":  self.trail_drawdown,
            "min_bars":        self.min_bars,
            "commission_rate": self.commission_rate,
            "stamp_duty_rate": self.stamp_duty_rate,
            "slippage_rate":   self.slippage_rate,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StrategyParams":
        return cls(
            max_hold_days=   d.get("max_hold_days",   60),
            stop_loss_pct=   d.get("stop_loss_pct",   8.0),
            take_profit_pct= d.get("take_profit_pct", 15.0),
            trail_drawdown=  d.get("trail_drawdown",  10.0),
            min_bars=        d.get("min_bars",        60),
            commission_rate= d.get("commission_rate", 0.0003),
            stamp_duty_rate= d.get("stamp_duty_rate", 0.001),
            slippage_rate=   d.get("slippage_rate",   0.0002),
        )


@dataclass
class Strategy:
    """
    量化策略定义。
    包含买入条件树、卖出条件树、元信息和运行参数。
    """
    meta:      StrategyMeta
    buy_tree:  ConditionNode
    sell_tree: ConditionNode
    params:    StrategyParams   = field(default_factory=StrategyParams)
    strategy_id: str            = field(default_factory=lambda: uuid.uuid4().hex[:10])

    # ── 快捷属性 ──────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def buy_condition_count(self) -> int:
        return self.buy_tree.count_leaves()

    @property
    def sell_condition_count(self) -> int:
        return self.sell_tree.count_leaves()

    # ── JSON 序列化 ───────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "meta":        self.meta.to_dict(),
            "buy_tree":    self.buy_tree.to_dict(),
            "sell_tree":   self.sell_tree.to_dict(),
            "params":      self.params.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Strategy":
        return cls(
            strategy_id= d.get("strategy_id", uuid.uuid4().hex[:10]),
            meta=        StrategyMeta.from_dict(d["meta"]),
            buy_tree=    ConditionNode.from_dict(d["buy_tree"]),
            sell_tree=   ConditionNode.from_dict(d["sell_tree"]),
            params=      StrategyParams.from_dict(d.get("params", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Strategy":
        return cls.from_dict(json.loads(json_str))

    # ── 更新元信息时间戳 ──────────────────────────────────────────────

    def touch(self) -> None:
        self.meta.updated_at = str(datetime.now())[:19]

    # ── 显示 ──────────────────────────────────────────────────────────

    def summary(self) -> str:
        lines = [
            f"策略：{self.meta.name}  v{self.meta.version}",
            f"  买入条件（{self.buy_condition_count} 个）:",
            self.buy_tree.pretty(indent=2),
            f"  卖出条件（{self.sell_condition_count} 个）:",
            self.sell_tree.pretty(indent=2),
            f"  止损: {self.params.stop_loss_pct}%  "
            f"止盈: {self.params.take_profit_pct}%  "
            f"追踪: {self.params.trail_drawdown}%  "
            f"最大持仓: {self.params.max_hold_days}天",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (f"Strategy(name={self.meta.name!r}, "
                f"buy={self.buy_condition_count}, "
                f"sell={self.sell_condition_count})")


# ── 工厂函数：从空模板快速创建策略 ────────────────────────────────────

def empty_strategy(name: str = "新策略") -> Strategy:
    """创建空策略模板（AND 买入树 + OR 卖出树）"""
    return Strategy(
        meta=      StrategyMeta(name=name),
        buy_tree=  ConditionNode(op=NodeOp.AND, label="买入条件"),
        sell_tree= ConditionNode(op=NodeOp.OR,  label="卖出条件"),
        params=    StrategyParams(),
    )
