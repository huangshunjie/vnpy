"""
global_portfolio_intelligence/engine/objective_engine.py  (Phase 2)

ObjectiveEngine — 统一目标函数引擎。

职责：
  - 接收来自各子系统的状态输入（Portfolio / Risk / Alpha / Execution）
  - 计算统一目标函数值（Return - Risk - Cost - Turnover + Alpha + Execution）
  - 计算四个多目标评分（Sharpe / Drawdown / Capacity / Stability）
  - 更新 ObjectiveState 并广播事件
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from ..constant import OptimizationMode
from ..model.objective_model import (
    ObjectiveConfig, ObjectiveState, MultiObjectiveResult)
from ..utils.objective_utils import (
    compute_unified_objective,
    compute_sharpe_score,
    compute_drawdown_score,
    compute_capacity_score,
    compute_stability_score,
    compute_multi_objective_score,
    normalize,
)


class ObjectiveEngine:
    """统一目标函数引擎（Phase 2 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log    = log_fn or (lambda m: None)
        self._config = ObjectiveConfig()
        self._state  = ObjectiveState(config=self._config)
        self._history: list[ObjectiveState] = []

        # 内部缓存：来自子系统的原始数据
        self._returns:    list[float] = []
        self._nav:        list[float] = []
        self._used_cap:   float       = 0.0
        self._total_cap:  float       = 1.0

    def init(self)  -> None: self._log("[ObjectiveEngine] init()")
    def start(self) -> None: self._log("[ObjectiveEngine] start()")
    def stop(self)  -> None: self._log("[ObjectiveEngine] stop()")

    # ------------------------------------------------------------------ #
    #  配置
    # ------------------------------------------------------------------ #

    def set_config(self, config: ObjectiveConfig) -> None:
        self._config = config
        self._state.config = config
        self._log(f"[ObjectiveEngine] config updated: mode={config.mode.value}")

    def get_config(self) -> ObjectiveConfig:
        return self._config

    # ------------------------------------------------------------------ #
    #  数据更新（来自各子系统）
    # ------------------------------------------------------------------ #

    def update_returns(self, returns: list[float]) -> None:
        """更新收益率序列（来自 Portfolio Engine）。"""
        self._returns = list(returns)

    def update_nav(self, nav: list[float]) -> None:
        """更新净值序列（来自 Portfolio Engine）。"""
        self._nav = list(nav)

    def update_capital(self, used: float, total: float) -> None:
        """更新资金使用情况（来自 Capital Allocation）。"""
        self._used_cap  = used
        self._total_cap = max(total, 1e-9)

    # ------------------------------------------------------------------ #
    #  核心计算
    # ------------------------------------------------------------------ #

    def compute(
        self,
        inputs: dict,
    ) -> ObjectiveState:
        """
        计算统一目标函数。

        inputs 字典包含：
          expected_return      : float [0,1]  预期收益归一化分
          risk                 : float [0,1]  风险归一化分
          cost                 : float [0,1]  成本归一化分
          turnover             : float [0,1]  换手率归一化分
          alpha_quality        : float [0,1]  Alpha 质量分
          execution_efficiency : float [0,1]  执行效率分

          # 可选（用于多目标评分）
          returns    : list[float]   日收益率序列
          nav        : list[float]   净值序列
          used_cap   : float         已使用资金
          total_cap  : float         总资金
        """
        # 提取一阶输入
        exp_ret  = float(inputs.get("expected_return",      0.5))
        risk     = float(inputs.get("risk",                 0.3))
        cost     = float(inputs.get("cost",                 0.2))
        turnover = float(inputs.get("turnover",             0.2))
        alpha    = float(inputs.get("alpha_quality",        0.5))
        exec_eff = float(inputs.get("execution_efficiency", 0.7))

        # 更新时间序列缓存（如有）
        if "returns" in inputs:
            self._returns = list(inputs["returns"])
        if "nav" in inputs:
            self._nav = list(inputs["nav"])
        if "used_cap" in inputs:
            self._used_cap = float(inputs["used_cap"])
        if "total_cap" in inputs:
            self._total_cap = max(float(inputs["total_cap"]), 1e-9)

        # ── 统一目标函数 ─────────────────────────────────────────────
        result = compute_unified_objective(
            expected_return      = exp_ret,
            risk                 = risk,
            cost                 = cost,
            turnover             = turnover,
            alpha_quality        = alpha,
            execution_efficiency = exec_eff,
            weights              = self._config.as_weights(),
        )

        # ── 多目标评分 ───────────────────────────────────────────────
        sharpe_s    = compute_sharpe_score(self._returns)    if self._returns else 50.0
        drawdown_s  = compute_drawdown_score(self._nav)       if self._nav     else 50.0
        capacity_s  = compute_capacity_score(
            self._used_cap, self._total_cap)
        stability_s = compute_stability_score(self._returns)  if self._returns else 50.0

        multi = compute_multi_objective_score(
            sharpe_s, drawdown_s, capacity_s, stability_s,
            weights=self._config.as_multi_weights(),
        )

        multi_result = MultiObjectiveResult(
            composite       = multi["composite"],
            sharpe_score    = multi["sharpe_score"],
            drawdown_score  = multi["drawdown_score"],
            capacity_score  = multi["capacity_score"],
            stability_score = multi["stability_score"],
        )

        # ── 更新状态 ─────────────────────────────────────────────────
        self._state = ObjectiveState(
            expected_return      = exp_ret,
            risk                 = risk,
            cost                 = cost,
            turnover             = turnover,
            alpha_quality        = alpha,
            execution_efficiency = exec_eff,
            objective            = result["objective"],
            score                = result["score"],
            components           = result["components"],
            multi_objective      = multi_result,
            config               = self._config,
            updated_at           = datetime.now(),
            iteration            = self._state.iteration + 1,
        )

        self._history.append(self._state)

        self._log(
            f"[ObjectiveEngine] compute #{self._state.iteration}: "
            f"obj={self._state.objective:.4f} "
            f"score={self._state.score:.1f} "
            f"composite={multi_result.composite:.1f}"
        )
        return self._state

    # ------------------------------------------------------------------ #
    #  模式切换（自动调整权重）
    # ------------------------------------------------------------------ #

    def set_mode(self, mode: OptimizationMode) -> None:
        """
        切换优化模式，自动调整目标权重。

        SHARPE    → 强化 Return，弱化 Cost
        DRAWDOWN  → 强化 Risk，弱化 Turnover
        CAPACITY  → 均衡，强化 Execution
        STABILITY → 均衡，强化 Alpha
        BALANCED  → 默认权重
        """
        cfg = self._config
        cfg.mode = mode

        if mode == OptimizationMode.SHARPE:
            cfg.w_return, cfg.w_risk    = 0.40, 0.20
            cfg.w_cost,   cfg.w_turnover= 0.10, 0.10
            cfg.w_alpha,  cfg.w_execution=0.10, 0.10
        elif mode == OptimizationMode.DRAWDOWN:
            cfg.w_return, cfg.w_risk    = 0.20, 0.40
            cfg.w_cost,   cfg.w_turnover= 0.15, 0.05
            cfg.w_alpha,  cfg.w_execution=0.10, 0.10
        elif mode == OptimizationMode.CAPACITY:
            cfg.w_return, cfg.w_risk    = 0.25, 0.20
            cfg.w_cost,   cfg.w_turnover= 0.10, 0.10
            cfg.w_alpha,  cfg.w_execution=0.15, 0.20
        elif mode == OptimizationMode.STABILITY:
            cfg.w_return, cfg.w_risk    = 0.25, 0.20
            cfg.w_cost,   cfg.w_turnover= 0.10, 0.10
            cfg.w_alpha,  cfg.w_execution=0.20, 0.15
        else:  # BALANCED
            cfg.w_return, cfg.w_risk    = 0.30, 0.25
            cfg.w_cost,   cfg.w_turnover= 0.15, 0.10
            cfg.w_alpha,  cfg.w_execution=0.10, 0.10

        self._log(f"[ObjectiveEngine] mode set to {mode.value}")

    # ------------------------------------------------------------------ #
    #  查询
    # ------------------------------------------------------------------ #

    def get_state(self) -> ObjectiveState:
        return self._state

    def get_history(self, n: int = 50) -> list[ObjectiveState]:
        return self._history[-n:]

    def summary(self) -> dict:
        return {
            "phase":      2,
            "status":     "active",
            "mode":       self._config.mode.value,
            "iterations": self._state.iteration,
            "score":      self._state.score,
            "objective":  round(self._state.objective, 6),
            "composite":  self._state.multi_objective.composite,
        }
