"""
global_portfolio_intelligence/engine/flow_engine.py  (Phase 4)

FlowEngine — 资金流控制器。

职责：
  - 管理策略/Alpha 资金预算（CapitalBudget）
  - 四种分配模式：equal / performance / regime_based / risk_parity
  - 资金流调度记录（FlowRecord）
  - 动态资金再分配（基于绩效分 + 市场状态）
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import AllocationMode
from ..model.performance_model import CapitalBudget, FlowRecord, CapitalFlowState
from ..utils.optimization_utils import normalize_weights, risk_parity_weights


class FlowEngine:
    """资金流控制器（Phase 4 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log      = log_fn or (lambda m: None)
        self._mode     = AllocationMode.PERFORMANCE
        self._total    = 0.0
        self._strategy_budgets: dict[str, CapitalBudget] = {}
        self._alpha_budgets:    dict[str, CapitalBudget] = {}
        self._flow_records: list[FlowRecord] = []
        self._state = CapitalFlowState()

    def init(self)  -> None: self._log("[FlowEngine] init()")
    def start(self) -> None: self._log("[FlowEngine] start()")
    def stop(self)  -> None: self._log("[FlowEngine] stop()")

    def set_mode(self, mode: AllocationMode) -> None:
        self._mode = mode
        self._log(f"[FlowEngine] mode -> {mode.value}")

    def set_total_capital(self, total: float) -> None:
        self._total = max(total, 0.0)
        self._log(f"[FlowEngine] total_capital={self._total:.2f}")

    # ── entity registration ──────────────────────────────────────────
    def register_strategy(self, entity_id: str,
                           performance_score: float = 50.0,
                           risk_budget: float = 0.15) -> None:
        self._strategy_budgets[entity_id] = CapitalBudget(
            entity_id=entity_id, entity_type="strategy",
            performance_score=performance_score, risk_budget=risk_budget)
        self._log(f"[FlowEngine] strategy registered: {entity_id}")

    def register_alpha(self, entity_id: str,
                        performance_score: float = 50.0) -> None:
        self._alpha_budgets[entity_id] = CapitalBudget(
            entity_id=entity_id, entity_type="alpha",
            performance_score=performance_score)
        self._log(f"[FlowEngine] alpha registered: {entity_id}")

    def update_performance(self, entity_id: str, score: float) -> None:
        for d in [self._strategy_budgets, self._alpha_budgets]:
            if entity_id in d:
                d[entity_id].performance_score = max(0.0, min(score, 100.0))

    def update_regime_weights(self, weights: dict[str, float]) -> None:
        for eid, w in weights.items():
            for d in [self._strategy_budgets, self._alpha_budgets]:
                if eid in d:
                    d[eid].regime_weight = max(0.0, w)

    def set_active(self, entity_id: str, active: bool) -> None:
        for d in [self._strategy_budgets, self._alpha_budgets]:
            if entity_id in d:
                d[eid].is_active = active

    # ── core allocation ──────────────────────────────────────────────
    def allocate(self, mode: AllocationMode | None = None) -> CapitalFlowState:
        """
        执行一次全局资金分配。

        Returns updated CapitalFlowState.
        """
        m = mode if mode is not None else self._mode
        s_budgets = [b for b in self._strategy_budgets.values() if b.is_active]
        a_budgets = [b for b in self._alpha_budgets.values()   if b.is_active]

        if not s_budgets and not a_budgets:
            self._log("[FlowEngine] allocate: no active entities")
            return self._state

        # 计算分配权重
        s_weights = self._compute_weights(s_budgets, m)
        a_weights = self._compute_weights(a_budgets, m)

        # 策略分配占 80%，Alpha 分配占 20%
        s_cap = self._total * 0.80
        a_cap = self._total * 0.20

        flow_id_base = f"FLW_{uuid.uuid4().hex[:6].upper()}"
        deployed = 0.0

        for i, b in enumerate(s_budgets):
            w = s_weights[i] if i < len(s_weights) else 0.0
            amt = round(s_cap * w, 2)
            b.allocated_capital = amt
            b.allocation_ratio  = round(amt / max(self._total, 1e-9), 6)
            deployed += amt
            self._flow_records.append(FlowRecord(
                flow_id=f"{flow_id_base}_S{i}", flow_type="allocation",
                entity_id=b.entity_id, entity_type="strategy",
                amount=amt, ratio=b.allocation_ratio, mode=m,
                reason=f"{m.value} allocation"))

        for i, b in enumerate(a_budgets):
            w = a_weights[i] if i < len(a_weights) else 0.0
            amt = round(a_cap * w, 2)
            b.allocated_capital = amt
            b.allocation_ratio  = round(amt / max(self._total, 1e-9), 6)
            deployed += amt
            self._flow_records.append(FlowRecord(
                flow_id=f"{flow_id_base}_A{i}", flow_type="allocation",
                entity_id=b.entity_id, entity_type="alpha",
                amount=amt, ratio=b.allocation_ratio, mode=m,
                reason=f"{m.value} allocation"))

        idle = max(self._total - deployed, 0.0)
        deploy_ratio = round(deployed / max(self._total, 1e-9), 6)

        # 集中度评分（HHI）
        all_ratios = [b.allocation_ratio for b in s_budgets + a_budgets]
        conc = self._concentration_score(all_ratios)

        # 资金效率评分（部署率接近 85% 为最优）
        eff = max(0.0, 1.0 - abs(deploy_ratio - 0.85) / 0.85) * 100

        self._state = CapitalFlowState(
            total_capital       = self._total,
            deployed_capital    = round(deployed, 2),
            idle_capital        = round(idle, 2),
            deployment_ratio    = deploy_ratio,
            strategy_budgets    = list(s_budgets),
            alpha_budgets       = list(a_budgets),
            n_active_strategies = len(s_budgets),
            n_active_alphas     = len(a_budgets),
            concentration_score = conc,
            efficiency_score    = round(eff, 2),
            mode                = m,
            updated_at          = datetime.now(),
            flow_count          = len(self._flow_records),
        )

        self._log(
            f"[FlowEngine] allocate: mode={m.value} "
            f"deployed={deployed:.2f}/{self._total:.2f} "
            f"ratio={deploy_ratio:.2%} conc={conc:.1f} eff={eff:.1f}")
        return self._state

    # ── dynamic reallocation ─────────────────────────────────────────
    def rebalance_by_performance(
        self,
        performance_updates: dict[str, float],
    ) -> CapitalFlowState:
        """根据最新绩效评分动态再分配资金。"""
        for eid, score in performance_updates.items():
            self.update_performance(eid, score)
        return self.allocate(AllocationMode.PERFORMANCE)

    def rebalance_by_regime(
        self,
        regime_weights: dict[str, float],
    ) -> CapitalFlowState:
        """根据市场状态（Regime）调节系数动态再分配。"""
        self.update_regime_weights(regime_weights)
        return self.allocate(AllocationMode.REGIME_BASED)

    # ── query ────────────────────────────────────────────────────────
    def get_state(self) -> CapitalFlowState:
        return self._state

    def get_flow_records(self, n: int = 50) -> list[FlowRecord]:
        return self._flow_records[-n:]

    def get_strategy_budget(self, entity_id: str) -> CapitalBudget | None:
        return self._strategy_budgets.get(entity_id)

    def summary(self) -> dict:
        return {
            "phase":        4,
            "status":       "active",
            "mode":         self._mode.value,
            "total_capital":round(self._total, 2),
            "deployed":     round(self._state.deployed_capital, 2),
            "deploy_ratio": round(self._state.deployment_ratio, 4),
            "n_strategies": len(self._strategy_budgets),
            "n_alphas":     len(self._alpha_budgets),
            "flow_count":   len(self._flow_records),
            "concentration":round(self._state.concentration_score, 2),
            "efficiency":   round(self._state.efficiency_score, 2),
        }

    # ── internal ─────────────────────────────────────────────────────
    def _compute_weights(
        self,
        budgets: list[CapitalBudget],
        mode: AllocationMode,
    ) -> list[float]:
        if not budgets:
            return []
        n = len(budgets)

        if mode == AllocationMode.EQUAL:
            return [1.0 / n] * n

        elif mode == AllocationMode.PERFORMANCE:
            scores = [b.performance_score for b in budgets]
            return normalize_weights(scores)

        elif mode == AllocationMode.REGIME_BASED:
            scores = [b.performance_score * b.regime_weight for b in budgets]
            return normalize_weights([max(s, 0.0) for s in scores])

        else:  # RISK_PARITY
            vols = [b.risk_budget if b.risk_budget > 0 else 0.15
                    for b in budgets]
            return risk_parity_weights(vols)

    @staticmethod
    def _concentration_score(ratios: list[float]) -> float:
        if not ratios: return 100.0
        n = len(ratios)
        total = sum(ratios)
        if total <= 0: return 100.0
        norm = [r / total for r in ratios]
        hhi  = sum(w ** 2 for w in norm)
        hhi_min = 1.0 / n
        score = max(0.0, (1.0 - hhi) / max(1.0 - hhi_min, 1e-9)) * 100
        return round(score, 2)
