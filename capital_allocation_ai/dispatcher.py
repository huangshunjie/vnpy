"""
capital_allocation_ai/engine.py

CapitalAllocationEngine — 顶层资本分配调度引擎（Phase 1 Stub）。

职责：
  - VeighNa BaseEngine 接口实现（init / start / stop）
  - 协调 5 个子引擎（Phase 2+ 逐步接入）
  - 广播 Capital Allocation 事件
  - 不执行任何交易逻辑

❌ 不修改 Portfolio / Execution / Risk
✔  仅读取 Alpha Factory / Portfolio / Risk 数据
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME
from .event import (
    EVENT_CAPITAL_UPDATE,
    EVENT_ALLOCATION_UPDATED,
    EVENT_ALPHA_RANK_UPDATED,
    EVENT_REBALANCE_TRIGGER,
    EVENT_RISK_BUDGET_UPDATED,
)
from .engine.scoring_engine    import AlphaCapitalScoringEngine
from .engine.allocation_engine import CapitalAllocationEngine as _AllocationEngine
from .engine.risk_budget_engine import RiskBudgetEngine
from .engine.routing_engine     import StrategyCapitalRouter
from .engine.rebalance_engine   import RebalancingEngine
from .datasource.alpha_loader     import AlphaLoader
from .datasource.portfolio_loader import PortfolioLoader
from .datasource.risk_loader      import RiskLoader


class CapitalAllocationEngine(BaseEngine):
    """
    Capital Allocation Intelligence System — 顶层引擎（Phase 1）。

    Phase 1: 骨架，所有方法均为 stub，Engine 可正常 init/start/stop。
    Phase 2: 接入 AlphaCapitalScoringEngine。
    Phase 3: 接入 CapitalAllocationEngine（子引擎）。
    Phase 4: 接入 RiskBudgetEngine。
    Phase 5: 接入 RebalancingEngine。
    """

    engine_name = APP_NAME

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self._started_at: datetime | None = None
        self._log_records: list[str] = []

        # ── 子引擎（Phase 1: stub 实例）─────────────────────────────
        self.alpha_loader     = AlphaLoader(use_simulated=True)
        self.scoring_engine   = AlphaCapitalScoringEngine(
            alpha_loader = self.alpha_loader,
            log_fn       = self._log,
        )
        self.allocation_engine = _AllocationEngine(log_fn=self._log)
        self.risk_loader        = RiskLoader()
        self.risk_budget_engine = RiskBudgetEngine(
            risk_loader = self.risk_loader,
            log_fn      = self._log,
        )
        self.routing_engine    = StrategyCapitalRouter(log_fn=self._log)
        self.rebalance_engine  = RebalancingEngine(log_fn=self._log)

        # ── 数据源（Phase 1: stub 实例）──────────────────────────────
        self.portfolio_loader = PortfolioLoader()

        self._log(f"[{APP_NAME}] Engine created (Phase 1 stub)")

    # ------------------------------------------------------------------ #
    #  BaseEngine 接口
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        """初始化引擎（Phase 1: no-op）。"""
        self._log(f"[{APP_NAME}] init()")

    def start(self) -> None:
        """启动引擎（Phase 1: 记录启动时间）。"""
        self._started_at = datetime.now()
        self._log(f"[{APP_NAME}] start()  at={str(self._started_at)[:19]}")
        self.dispatch_event(EVENT_CAPITAL_UPDATE, {"status": "started"})

    def stop(self) -> None:
        """停止引擎（Phase 1: no-op）。"""
        self._log(f"[{APP_NAME}] stop()")

    def close(self) -> None:
        """关闭引擎（VeighNa 生命周期接口）。"""
        self.stop()

    # ------------------------------------------------------------------ #
    #  核心接口（Phase 1 stub）
    # ------------------------------------------------------------------ #

    def calculate_allocation(
        self,
        alpha_ids:  list | None = None,
        max_ratio:  float = 0.30,
        min_ratio:  float = 0.005,
    ):
        """
        全链路资金分配（Phase 3）：
          1. batch_score_alphas → capital_score
          2. AllocationEngine.calculate → CapitalAllocation 列表
          3. StrategyCapitalRouter.route → 策略级路由
          4. 广播 EVENT_ALLOCATION_UPDATED

        Returns
        -------
        AllocationSnapshot
        """
        results = self.scoring_engine.batch_score(alpha_ids)
        scores  = {s.alpha_id: s.capital_score for s in results}

        total_capital = self.portfolio_loader.get_total_capital()
        snapshot = self.allocation_engine.calculate(
            scores        = scores,
            total_capital = total_capital,
            max_ratio     = max_ratio,
            min_ratio     = min_ratio,
        )

        routed = self.routing_engine.route(snapshot.allocations)

        self._log(
            f"[{APP_NAME}] calculate_allocation"
            f"  n={len(results)}"
            f"  capital={total_capital:,.0f}"
            f"  signals={len(snapshot.signals)}"
            f"  routed_strategies={len(routed)}"
        )
        self.dispatch_event(
            EVENT_ALLOCATION_UPDATED,
            {
                "snapshot_id":   snapshot.snapshot_id,
                "n_active":      snapshot.n_active,
                "total_capital": total_capital,
                "n_signals":     len(snapshot.signals),
            },
        )
        return snapshot

    def get_allocation_snapshot(self):
        """返回最新资金分配快照（Phase 3）。"""
        return self.allocation_engine.get_latest_snapshot()

    def get_allocation_signals(self, limit: int = 100) -> list:
        """返回最新资金流动信号列表（Phase 3）。"""
        return self.allocation_engine.get_signals(limit=limit)

    def get_routed_capitals(self) -> dict:
        """返回最新策略级路由资金分配（Phase 3）。"""
        snap = self.allocation_engine.get_latest_snapshot()
        if snap is None:
            return {}
        return self.routing_engine.route(snap.allocations)

    def get_alpha_ranking(self, top_n: int = 50) -> list:
        """返回 Alpha 资本评分排名（Phase 2 实现）。"""
        ranking = self.scoring_engine.get_ranking(top_n=top_n)
        self.dispatch_event(
            EVENT_ALPHA_RANK_UPDATED,
            {"count": len(ranking)}
        )
        return ranking

    # ------------------------------------------------------------------ #
    #  Alpha 资本评分接口（Phase 2）
    # ------------------------------------------------------------------ #

    def score_alpha(self, alpha_id: str):
        """对单个 Alpha 进行资本评分（Phase 2）。"""
        return self.scoring_engine.score(alpha_id)

    def batch_score_alphas(
        self,
        alpha_ids: list[str] | None = None,
    ) -> list:
        """批量资本评分（Phase 2）。"""
        results = self.scoring_engine.batch_score(alpha_ids)
        self.dispatch_event(
            EVENT_ALPHA_RANK_UPDATED,
            {"count": len(results)}
        )
        return results

    def get_capital_ratios(self) -> dict:
        """返回各 Alpha 资本分配比例（Phase 2）。"""
        return self.scoring_engine.get_normalized_ratios()

    def get_scoring_summary(self) -> dict:
        """返回评分引擎摘要（Phase 2）。"""
        return self.scoring_engine.summary()

    # ------------------------------------------------------------------ #
    #  风险预算接口（Phase 4）
    # ------------------------------------------------------------------ #

    def evaluate_risk(
        self,
        alpha_ids: list | None = None,
        ratios:    dict | None = None,
    ):
        """
        全链路风险预算评估（Phase 4）：
          1. 确定 alpha_ids / ratios（来自最新分配快照 or 参数）
          2. RiskBudgetEngine.evaluate → RiskSnapshot
          3. 广播 EVENT_RISK_BUDGET_UPDATED

        Returns
        -------
        RiskSnapshot
        """
        if alpha_ids is None or ratios is None:
            snap_alloc = self.allocation_engine.get_latest_snapshot()
            if snap_alloc is None:
                self._log(f"[{APP_NAME}] evaluate_risk: no allocation snapshot, run calculate_allocation first")
                return None
            alpha_ids = list(snap_alloc.allocations.keys())
            ratios    = {k: v.ratio for k, v in snap_alloc.allocations.items()}

        snap = self.risk_budget_engine.evaluate(alpha_ids, ratios)
        self.dispatch_event(
            EVENT_RISK_BUDGET_UPDATED,
            {
                "snapshot_id": snap.snapshot_id,
                "n_breached":  snap.n_breached,
                "n_signals":   len(snap.adjust_signals),
                "port_var":    snap.portfolio_var,
            },
        )
        return snap

    def get_risk_adjusted_ratios(self) -> dict:
        """返回经风险约束后的资金分配比例（Phase 4）。"""
        snap_alloc = self.allocation_engine.get_latest_snapshot()
        snap_risk  = self.risk_budget_engine.get_latest_snapshot()
        if snap_alloc is None:
            return {}
        ratios = {k: v.ratio for k, v in snap_alloc.allocations.items()}
        if snap_risk is None:
            return ratios
        return self.risk_budget_engine.apply_risk_constraints(ratios, snap_risk)

    def get_risk_snapshot(self):
        """返回最新风险快照（Phase 4）。"""
        return self.risk_budget_engine.get_latest_snapshot()

    def get_risk_signals(self, limit: int = 100) -> list:
        """返回最新风险调整信号（Phase 4）。"""
        return self.risk_budget_engine.get_signals(limit=limit)

    def get_breached_alphas(self) -> list:
        """返回当前有风险违规的 Alpha 列表（Phase 4）。"""
        return self.risk_budget_engine.get_breached_alphas()

    def update_risk_budget(self, **kwargs) -> dict:
        """更新风险预算上限（Phase 4）。"""
        self.risk_budget_engine.update_limits(**kwargs)
        self._log(f"[{APP_NAME}] update_risk_budget  {kwargs}")
        return self.risk_budget_engine.get_limits()

    # ------------------------------------------------------------------ #
    #  再平衡接口（Phase 5）
    # ------------------------------------------------------------------ #

    def trigger_rebalance(
        self,
        trigger_type: str  = "manual",
        reason:       str  = "",
        force:        bool = False,
    ):
        """
        全链路再平衡触发（Phase 5）：
          1. 从 AllocationEngine 获取 current/target 比例
          2. 从 RiskBudgetEngine 获取最新风险快照
          3. 从 ScoringEngine 获取最新评分
          4. RebalancingEngine.trigger → RebalancePlan
          5. 广播 EVENT_REBALANCE_TRIGGER

        Returns
        -------
        RebalancePlan | None
        """
        snap_alloc = self.allocation_engine.get_latest_snapshot()
        if snap_alloc is None:
            self._log(f"[{APP_NAME}] trigger_rebalance: no allocation snapshot")
            return None

        current_ratios = {
            k: v.ratio for k, v in snap_alloc.allocations.items()
        }
        # 目标比例 = 风险约束后比例
        target_ratios = self.get_risk_adjusted_ratios()
        if not target_ratios:
            target_ratios = current_ratios

        total_capital = snap_alloc.total_capital
        risk_snap     = self.risk_budget_engine.get_latest_snapshot()
        curr_scores   = self.scoring_engine.get_normalized_ratios()

        plan = self.rebalance_engine.trigger(
            current_ratios = current_ratios,
            target_ratios  = target_ratios,
            total_capital  = total_capital,
            trigger_type   = trigger_type,
            reason         = reason,
            risk_snap      = risk_snap,
            curr_scores    = curr_scores,
            force          = force,
        )

        self.dispatch_event(
            EVENT_REBALANCE_TRIGGER,
            {
                "plan_id":     plan.plan_id if plan else None,
                "trigger":     trigger_type,
                "n_trades":    plan.n_trades     if plan else 0,
                "turnover":    plan.total_turnover if plan else 0.0,
                "cost":        plan.estimated_cost if plan else 0.0,
            },
        )
        return plan

    def auto_rebalance(self):
        """自动检测所有触发条件并执行再平衡（Phase 5）。"""
        snap_alloc = self.allocation_engine.get_latest_snapshot()
        if snap_alloc is None:
            return None

        current = {k: v.ratio for k, v in snap_alloc.allocations.items()}
        target  = self.get_risk_adjusted_ratios() or current
        risk_snap   = self.risk_budget_engine.get_latest_snapshot()
        curr_scores = self.scoring_engine.get_normalized_ratios()

        plan = self.rebalance_engine.auto_trigger(
            current_ratios = current,
            target_ratios  = target,
            total_capital  = snap_alloc.total_capital,
            risk_snap      = risk_snap,
            curr_scores    = curr_scores,
        )
        if plan:
            self.dispatch_event(
                EVENT_REBALANCE_TRIGGER,
                {"plan_id": plan.plan_id, "trigger": plan.trigger.value,
                 "n_trades": plan.n_trades},
            )
        return plan

    def get_rebalance_plan(self):
        """返回最新再平衡计划（Phase 5）。"""
        return self.rebalance_engine.get_latest_plan()

    def get_rebalance_history(self, limit: int = 50) -> list:
        """返回再平衡历史记录（Phase 5）。"""
        return self.rebalance_engine.get_history_dicts(limit=limit)

    def approve_rebalance(self, plan_id: str) -> bool:
        """批准再平衡计划（Phase 5）。"""
        return self.rebalance_engine.approve_plan(plan_id)

    def cancel_rebalance(self, plan_id: str, reason: str = "") -> bool:
        """取消再平衡计划（Phase 5）。"""
        return self.rebalance_engine.cancel_plan(plan_id, reason)


    # ------------------------------------------------------------------ #
    #  事件广播
    # ------------------------------------------------------------------ #

    def dispatch_event(
        self,
        event_type: str,
        data:       dict | None = None,
    ) -> None:
        """广播 Capital Allocation 事件到 EventEngine。"""
        event = Event(event_type, data or {})
        self.event_engine.put(event)

    # ------------------------------------------------------------------ #
    #  摘要
    # ------------------------------------------------------------------ #

    def get_summary(self) -> dict:
        uptime = 0.0
        if self._started_at:
            uptime = (datetime.now() - self._started_at).total_seconds()
        return {
            "app":       APP_NAME,
            "phase":     5,
            "uptime":    round(uptime, 1),
            "scoring":   self.scoring_engine.summary(),
            "allocation": self.allocation_engine.summary(),
            "risk_budget": self.risk_budget_engine.summary(),
            "routing":   self.routing_engine.summary(),
            "rebalance": self.rebalance_engine.summary(),
            "alpha_loader": self.alpha_loader.summary(),
            "risk_loader":  self.risk_loader.summary(),
        }

    # ------------------------------------------------------------------ #
    #  内部日志
    # ------------------------------------------------------------------ #

    def _log(self, msg: str) -> None:
        ts = str(datetime.now())[:19]
        record = f"{ts}  {msg}"
        self._log_records.append(record)
        try:
            self.write_log(msg)
        except Exception:
            pass

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]
