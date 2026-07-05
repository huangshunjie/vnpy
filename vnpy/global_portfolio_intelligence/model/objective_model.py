"""
global_portfolio_intelligence/model/objective_model.py  (Phase 2)

ObjectiveState   — 统一目标函数当前状态快照
ObjectiveConfig  — 目标函数权重配置
MultiObjectiveResult — 多目标评分结果
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import OptimizationMode


@dataclass
class ObjectiveConfig:
    """统一目标函数权重配置。"""
    mode:       OptimizationMode = OptimizationMode.BALANCED

    # 一阶目标权重（合计应为 1.0）
    w_return:     float = 0.30
    w_risk:       float = 0.25
    w_cost:       float = 0.15
    w_turnover:   float = 0.10
    w_alpha:      float = 0.10
    w_execution:  float = 0.10

    # 多目标权重
    w_sharpe:     float = 0.40
    w_drawdown:   float = 0.30
    w_capacity:   float = 0.15
    w_stability:  float = 0.15

    def as_weights(self) -> dict[str, float]:
        return {
            "return":    self.w_return,
            "risk":      self.w_risk,
            "cost":      self.w_cost,
            "turnover":  self.w_turnover,
            "alpha":     self.w_alpha,
            "execution": self.w_execution,
        }

    def as_multi_weights(self) -> dict[str, float]:
        return {
            "sharpe":    self.w_sharpe,
            "drawdown":  self.w_drawdown,
            "capacity":  self.w_capacity,
            "stability": self.w_stability,
        }

    def to_dict(self) -> dict:
        return {
            "mode":        self.mode.value,
            "w_return":    self.w_return,
            "w_risk":      self.w_risk,
            "w_cost":      self.w_cost,
            "w_turnover":  self.w_turnover,
            "w_alpha":     self.w_alpha,
            "w_execution": self.w_execution,
        }


@dataclass
class MultiObjectiveResult:
    """多目标评分结果。"""
    composite:       float = 0.0
    sharpe_score:    float = 0.0
    drawdown_score:  float = 0.0
    capacity_score:  float = 0.0
    stability_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "composite":       round(self.composite,       2),
            "sharpe_score":    round(self.sharpe_score,    2),
            "drawdown_score":  round(self.drawdown_score,  2),
            "capacity_score":  round(self.capacity_score,  2),
            "stability_score": round(self.stability_score, 2),
        }


@dataclass
class ObjectiveState:
    """
    统一目标函数当前状态快照。
    由 ObjectiveEngine 每次计算后更新，广播 EVENT_OBJECTIVE_UPDATED。
    """
    # 输入分量（归一化 [0,1]）
    expected_return:       float = 0.0
    risk:                  float = 0.0
    cost:                  float = 0.0
    turnover:              float = 0.0
    alpha_quality:         float = 0.0
    execution_efficiency:  float = 0.0

    # 一阶目标函数结果
    objective:             float = 0.0
    score:                 float = 0.0      # [0, 100]
    components:            dict  = field(default_factory=dict)

    # 多目标评分
    multi_objective:       MultiObjectiveResult = field(
        default_factory=MultiObjectiveResult)

    # 配置
    config:                ObjectiveConfig = field(
        default_factory=ObjectiveConfig)

    updated_at:            datetime = field(default_factory=datetime.now)
    iteration:             int      = 0     # 累计计算次数

    def to_dict(self) -> dict:
        return {
            "expected_return":      round(self.expected_return,      4),
            "risk":                 round(self.risk,                 4),
            "cost":                 round(self.cost,                 4),
            "turnover":             round(self.turnover,             4),
            "alpha_quality":        round(self.alpha_quality,        4),
            "execution_efficiency": round(self.execution_efficiency, 4),
            "objective":            round(self.objective,            6),
            "score":                round(self.score,                2),
            "components":           {k: round(v, 6)
                                     for k, v in self.components.items()},
            "multi_objective":      self.multi_objective.to_dict(),
            "config":               self.config.to_dict(),
            "updated_at":           str(self.updated_at)[:19],
            "iteration":            self.iteration,
        }
