"""
Condition Insight 数据模型

定义条件智能分析的统一数据结构，支持JSON序列化。
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class ConditionRole(Enum):
    """条件在策略中的角色"""
    TREND_FILTER = "趋势过滤"
    ENTRY_TRIGGER = "入场触发"
    CONFIRMATION = "信号确认"
    RISK_FILTER = "风险过滤"
    EXIT_SIGNAL = "退出信号"


@dataclass
class ParamInsight:
    """单个参数的智能说明"""
    name: str                       # 参数键名 (如 "min_ratio")
    label: str                      # 中文显示名 (如 "量比下限")
    description: str                # 含义说明
    default: Any                    # 默认值
    range_min: Optional[float] = None   # 推荐范围下限
    range_max: Optional[float] = None   # 推荐范围上限
    # 按策略类型推荐
    recommend_short: str = ""       # 短线推荐
    recommend_trend: str = ""       # 趋势推荐
    recommend_swing: str = ""       # 波段推荐

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ParamInsight":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ConditionInsight:
    """
    条件智能分析卡片数据

    每个 ConditionIndicator 对应一个 ConditionInsight 实例。
    """
    # ── 基本信息 ──
    name: str                           # 显示名称
    category: str                       # 所属分类 (Trend/Volume/...)
    roles: List[ConditionRole] = field(default_factory=list)
    description: str = ""               # 功能描述

    # ── 计算逻辑 ──
    formula: str = ""                   # 公式说明
    trigger: str = ""                   # 触发条件文本

    # ── 参数说明 ──
    parameters: List[ParamInsight] = field(default_factory=list)

    # ── 使用场景 ──
    scenarios_good: List[str] = field(default_factory=list)  # 适合场景
    scenarios_bad: List[str] = field(default_factory=list)   # 不适合场景

    # ── 组合建议 ──
    combinations: List[str] = field(default_factory=list)    # 推荐搭配条件名
    combo_model: str = ""               # 组合形成的策略模型名称

    # ── 风险提示 ──
    risks: List[str] = field(default_factory=list)

    # ── 量化经验 ──
    experience: str = ""

    # ── 预留统计字段 ──
    statistics: Dict[str, Optional[float]] = field(default_factory=lambda: {
        "win_rate": None,
        "ic": None,
        "rank_ic": None,
        "average_return": None,
        "max_drawdown": None,
    })

    def to_dict(self) -> dict:
        """序列化为JSON兼容字典"""
        d = asdict(self)
        d["roles"] = [r.value for r in self.roles]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ConditionInsight":
        """从字典反序列化"""
        d = d.copy()
        d["roles"] = [ConditionRole(v) for v in d.get("roles", [])]
        d["parameters"] = [
            ParamInsight.from_dict(p) if isinstance(p, dict) else p
            for p in d.get("parameters", [])
        ]
        valid_keys = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in d.items() if k in valid_keys})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> "ConditionInsight":
        return cls.from_dict(json.loads(s))