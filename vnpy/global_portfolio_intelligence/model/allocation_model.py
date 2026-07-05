"""
global_portfolio_intelligence/model/allocation_model.py  (Phase 3)

跨模块优化状态模型。

CrossModuleState  — 单次跨模块优化结果
OptimizationResult— 完整优化迭代记录
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import OptimizationMode


@dataclass
class CrossModuleState:
    """
    跨模块优化结果快照。

    涵盖五个优化维度：
      alpha_weights       Alpha 因子权重
      strategy_allocs     策略资金分配比例
      portfolio_weights   组合持仓权重
      capital_dist        资金分配分布
      exec_intensity      执行力度向量
    """
    # 优化维度
    alpha_weights:      list[float] = field(default_factory=list)
    strategy_allocs:    list[float] = field(default_factory=list)
    portfolio_weights:  list[float] = field(default_factory=list)
    capital_dist:       list[float] = field(default_factory=list)
    exec_intensity:     list[float] = field(default_factory=list)

    # 标识信息
    alpha_ids:          list[str]   = field(default_factory=list)
    strategy_ids:       list[str]   = field(default_factory=list)
    asset_ids:          list[str]   = field(default_factory=list)

    # 评分
    composite_score:    float = 0.0
    alpha_score:        float = 0.0
    strategy_score:     float = 0.0
    portfolio_score:    float = 0.0
    execution_score:    float = 0.0
    capital_score:      float = 0.0

    # 优化过程
    mode:               OptimizationMode = OptimizationMode.BALANCED
    iterations:         int              = 0
    converged:          bool             = False
    obj_history:        list[float]      = field(default_factory=list)

    updated_at:         datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "composite_score":   round(self.composite_score,  2),
            "alpha_score":       round(self.alpha_score,      2),
            "strategy_score":    round(self.strategy_score,   2),
            "portfolio_score":   round(self.portfolio_score,  2),
            "execution_score":   round(self.execution_score,  2),
            "capital_score":     round(self.capital_score,    2),
            "mode":              self.mode.value,
            "iterations":        self.iterations,
            "converged":         self.converged,
            "alpha_weights":     [round(w, 6) for w in self.alpha_weights],
            "strategy_allocs":   [round(w, 6) for w in self.strategy_allocs],
            "portfolio_weights": [round(w, 6) for w in self.portfolio_weights],
            "capital_dist":      [round(w, 6) for w in self.capital_dist],
            "exec_intensity":    [round(v, 6) for v in self.exec_intensity],
            "updated_at":        str(self.updated_at)[:19],
        }


@dataclass
class OptimizationResult:
    """完整优化迭代记录（供 UI 和历史查询使用）。"""
    run_id:         str              = ""
    mode:           OptimizationMode = OptimizationMode.BALANCED
    state:          CrossModuleState = field(default_factory=CrossModuleState)
    initial_score:  float            = 0.0
    final_score:    float            = 0.0
    improvement:    float            = 0.0
    n_iterations:   int              = 0
    converged:      bool             = False
    started_at:     datetime         = field(default_factory=datetime.now)
    completed_at:   datetime         = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "run_id":        self.run_id,
            "mode":          self.mode.value,
            "initial_score": round(self.initial_score, 2),
            "final_score":   round(self.final_score,   2),
            "improvement":   round(self.improvement,   2),
            "n_iterations":  self.n_iterations,
            "converged":     self.converged,
            "started_at":    str(self.started_at)[:19],
            "completed_at":  str(self.completed_at)[:19],
            "state":         self.state.to_dict(),
        }
