"""
capital_allocation_ai/engine/risk_budget_engine.py  (Phase 4)

RiskBudgetEngine — 风险预算引擎（完整实现）。

职责：
  - 为每个 Alpha 分配风险预算（Vol / DD / Beta）
  - 检测风险违规（breach）
  - 生成 RiskAdjustSignal（减仓 / 暂停信号）
  - 提供风险约束后的调整比例

预算上限（默认）：
  Volatility  ≤ 0.30（年化）
  Drawdown    ≤ 0.20
  Beta        ≤ 0.80

❌ 不执行任何交易逻辑
✔  只检测 & 生成信号
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable

from ..constant import RiskBudgetType, AllocationStatus
from ..model.risk_budget_model import (
    RiskBudget,
    RiskBreach,
    RiskAdjustSignal,
    RiskSnapshot,
)
from ..datasource.risk_loader import RiskLoader


_DEFAULT_LIMITS = {
    RiskBudgetType.VOLATILITY: 0.30,
    RiskBudgetType.DRAWDOWN:   0.20,
    RiskBudgetType.EXPOSURE:   0.80,
}

_CRITICAL_MULT = 1.5   # 超限 50% 以上视为 critical


class RiskBudgetEngine:
    """
    风险预算引擎（Phase 4）。

    使用方式：
        engine = RiskBudgetEngine(risk_loader=RiskLoader())
        snap = engine.evaluate(
            alpha_ids = ["A", "B", "C"],
            ratios    = {"A": 0.4, "B": 0.35, "C": 0.25},
        )
        signals = snap.adjust_signals
    """

    def __init__(
        self,
        risk_loader:   RiskLoader | None   = None,
        log_fn:        Callable | None     = None,
        vol_limit:     float = 0.30,
        dd_limit:      float = 0.20,
        beta_limit:    float = 0.80,
        port_var_limit: float = 0.03,   # 组合日度 VaR 上限
        port_dd_limit:  float = 0.15,   # 组合整体回撤上限
        reduce_factor: float = 0.50,    # 违规时建议仓位缩减比例
    ) -> None:
        self._loader    = risk_loader or RiskLoader()
        self._log       = log_fn or (lambda msg: None)

        self._limits = {
            RiskBudgetType.VOLATILITY: vol_limit,
            RiskBudgetType.DRAWDOWN:   dd_limit,
            RiskBudgetType.EXPOSURE:   beta_limit,
        }
        self._port_var_limit  = port_var_limit
        self._port_dd_limit   = port_dd_limit
        self._reduce_factor   = reduce_factor

        self._budgets:   dict[str, list[RiskBudget]] = {}
        self._breaches:  list[RiskBreach]            = []
        self._signals:   list[RiskAdjustSignal]      = []
        self._snapshots: list[RiskSnapshot]           = []
        self._eval_count = 0

    # ------------------------------------------------------------------ #
    #  核心评估
    # ------------------------------------------------------------------ #

    def evaluate(
        self,
        alpha_ids: list[str],
        ratios:    dict[str, float],
    ) -> RiskSnapshot:
        """
        对所有 Alpha 进行风险预算评估。

        流程：
          1. 加载各 Alpha 风险指标
          2. 与预算上限比较 → 生成 RiskBudget 列表
          3. 检测违规 → 生成 RiskBreach
          4. 对违规 Alpha 生成 RiskAdjustSignal（建议减仓）
          5. 计算组合级风险（VaR / DD / Beta）
          6. 生成 RiskSnapshot

        Parameters
        ----------
        alpha_ids : Alpha ID 列表
        ratios    : 当前资金分配比例 {alpha_id: ratio}

        Returns
        -------
        RiskSnapshot
        """
        snap_breaches:  list[RiskBreach]        = []
        snap_signals:   list[RiskAdjustSignal]  = []
        snap_budgets:   dict[str, list[RiskBudget]] = {}

        risk_metrics = self._loader.get_all_risk_metrics(alpha_ids)

        for alpha_id in alpha_ids:
            metrics = risk_metrics.get(alpha_id, {})
            weight  = ratios.get(alpha_id, 0.0)

            alpha_budgets: list[RiskBudget] = []

            # ── 检测三个维度 ─────────────────────────────────────────
            checks = [
                (RiskBudgetType.VOLATILITY, metrics.get("vol",      0.0)),
                (RiskBudgetType.DRAWDOWN,   metrics.get("drawdown", 0.0)),
                (RiskBudgetType.EXPOSURE,   abs(metrics.get("beta", 0.0))),
            ]

            for budget_type, current_val in checks:
                limit       = self._limits[budget_type]
                utilization = (current_val / limit) if limit > 1e-12 else 0.0
                is_breached = current_val > limit

                budget = RiskBudget(
                    alpha_id      = alpha_id,
                    budget_type   = budget_type,
                    budget_limit  = limit,
                    current_value = round(current_val, 6),
                    utilization   = round(utilization, 6),
                    weight        = weight,
                    is_breached   = is_breached,
                    status        = (AllocationStatus.SUSPENDED if is_breached
                                     else AllocationStatus.ACTIVE),
                )
                alpha_budgets.append(budget)

                if is_breached:
                    excess    = current_val - limit
                    severity  = (
                        "critical"
                        if current_val > limit * _CRITICAL_MULT
                        else "warn"
                    )
                    breach = RiskBreach(
                        breach_id   = f"BRE_{uuid.uuid4().hex[:8].upper()}",
                        alpha_id    = alpha_id,
                        budget_type = budget_type,
                        limit       = limit,
                        actual      = round(current_val, 6),
                        excess      = round(excess, 6),
                        severity    = severity,
                        action_taken = "signal_emitted",
                    )
                    snap_breaches.append(breach)
                    self._breaches.append(breach)

                    # 生成减仓信号
                    suggested = weight * self._reduce_factor
                    if severity == "critical":
                        suggested = 0.0   # critical → 建议暂停
                    delta = suggested - weight

                    signal = RiskAdjustSignal(
                        signal_id       = f"RSK_{uuid.uuid4().hex[:8].upper()}",
                        alpha_id        = alpha_id,
                        breach          = breach,
                        suggested_ratio = round(suggested, 6),
                        current_ratio   = round(weight,    6),
                        delta_ratio     = round(delta,     6),
                        urgency         = severity,
                        reason          = (
                            f"{budget_type.value}={current_val:.4f}"
                            f" > limit={limit:.4f}"
                            f"  excess={excess:.4f}"
                        ),
                    )
                    snap_signals.append(signal)
                    self._signals.append(signal)

            snap_budgets[alpha_id] = alpha_budgets

        # ── 组合级指标 ───────────────────────────────────────────────
        port_var  = self._loader.get_portfolio_var(alpha_ids, ratios)
        port_dd   = self._loader.get_portfolio_drawdown(alpha_ids, ratios)
        port_beta = self._loader.get_portfolio_beta(alpha_ids, ratios)

        # 组合级违规
        if port_var > self._port_var_limit:
            self._log(
                f"[RiskBudgetEngine] PORTFOLIO VaR BREACH"
                f"  var={port_var:.4f} > limit={self._port_var_limit:.4f}"
            )
        if port_dd > self._port_dd_limit:
            self._log(
                f"[RiskBudgetEngine] PORTFOLIO DD BREACH"
                f"  dd={port_dd:.4f} > limit={self._port_dd_limit:.4f}"
            )

        snap = RiskSnapshot(
            snapshot_id    = f"RSNAP_{uuid.uuid4().hex[:8].upper()}",
            budgets        = snap_budgets,
            breaches       = snap_breaches,
            adjust_signals = snap_signals,
            portfolio_var  = port_var,
            portfolio_dd   = port_dd,
            portfolio_beta = port_beta,
            n_breached     = len({b.alpha_id for b in snap_breaches}),
        )

        self._budgets  = snap_budgets
        self._snapshots.append(snap)
        self._eval_count += 1

        self._log(
            f"[RiskBudgetEngine] evaluate #{self._eval_count}"
            f"  n={len(alpha_ids)}"
            f"  breached={snap.n_breached}"
            f"  signals={len(snap_signals)}"
            f"  port_var={port_var:.4f}"
            f"  port_dd={port_dd:.4f}"
            f"  port_beta={port_beta:.4f}"
        )
        return snap

    # ------------------------------------------------------------------ #
    #  约束调整
    # ------------------------------------------------------------------ #

    def apply_risk_constraints(
        self,
        ratios: dict[str, float],
        snap:   RiskSnapshot | None = None,
    ) -> dict[str, float]:
        """
        将风险超限 Alpha 的比例按 RiskAdjustSignal 减配，
        并重新归一化剩余 Alpha。

        Parameters
        ----------
        ratios : 当前分配比例
        snap   : 风险快照（None 则使用最新快照）

        Returns
        -------
        dict  {alpha_id: adjusted_ratio}  风险约束后的比例
        """
        if snap is None:
            snap = self.get_latest_snapshot()
        if snap is None:
            return dict(ratios)

        adjusted = dict(ratios)

        # 对每个信号应用减仓
        for signal in snap.adjust_signals:
            aid = signal.alpha_id
            if aid in adjusted:
                adjusted[aid] = signal.suggested_ratio

        # 重归一化
        total = sum(adjusted.values())
        if total < 1e-12:
            return dict(ratios)
        return {k: round(v / total, 8) for k, v in adjusted.items()}

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def check_breach(self, alpha_id: str) -> bool:
        """检查指定 Alpha 是否有风险预算违规。"""
        budgets = self._budgets.get(alpha_id, [])
        return any(b.is_breached for b in budgets)

    def get_breached_alphas(self) -> list[str]:
        """返回当前有违规的 Alpha ID 列表。"""
        snap = self.get_latest_snapshot()
        if snap is None:
            return []
        return list({b.alpha_id for b in snap.breaches})

    def get_budgets(
        self,
        alpha_id: str | None = None,
    ) -> dict | list:
        if alpha_id:
            return self._budgets.get(alpha_id, [])
        return dict(self._budgets)

    def get_latest_snapshot(self) -> RiskSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def get_snapshots(self, limit: int = 10) -> list[RiskSnapshot]:
        return self._snapshots[-limit:]

    def get_signals(self, limit: int = 100) -> list[RiskAdjustSignal]:
        return self._signals[-limit:]

    def get_breach_history(self, limit: int = 100) -> list[RiskBreach]:
        return self._breaches[-limit:]

    def update_limits(self, **kwargs) -> None:
        """动态更新风险预算上限。"""
        mapping = {
            "vol_limit":  RiskBudgetType.VOLATILITY,
            "dd_limit":   RiskBudgetType.DRAWDOWN,
            "beta_limit": RiskBudgetType.EXPOSURE,
        }
        for kw, bt in mapping.items():
            if kw in kwargs:
                self._limits[bt] = kwargs[kw]
                self._log(f"[RiskBudgetEngine] limit updated: {bt.value}={kwargs[kw]}")
        if "port_var_limit" in kwargs:
            self._port_var_limit = kwargs["port_var_limit"]
        if "port_dd_limit" in kwargs:
            self._port_dd_limit = kwargs["port_dd_limit"]

    def get_limits(self) -> dict:
        return {
            "vol_limit":      self._limits[RiskBudgetType.VOLATILITY],
            "dd_limit":       self._limits[RiskBudgetType.DRAWDOWN],
            "beta_limit":     self._limits[RiskBudgetType.EXPOSURE],
            "port_var_limit": self._port_var_limit,
            "port_dd_limit":  self._port_dd_limit,
            "reduce_factor":  self._reduce_factor,
        }

    def summary(self) -> dict:
        snap = self.get_latest_snapshot()
        return {
            "eval_count":   self._eval_count,
            "n_alphas":     len(self._budgets),
            "n_breached":   snap.n_breached   if snap else 0,
            "portfolio_var": snap.portfolio_var if snap else 0.0,
            "portfolio_dd":  snap.portfolio_dd  if snap else 0.0,
            "total_signals": len(self._signals),
            "phase":         4,
        }
