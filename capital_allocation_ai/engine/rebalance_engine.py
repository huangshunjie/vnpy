"""
capital_allocation_ai/engine/rebalance_engine.py  (Phase 5)

RebalancingEngine — 再平衡引擎（完整实现）。

触发类型：
  scheduled   定时触发（默认 7 天）
  risk        风险超限触发（VaR / DD / 违规 Alpha 数）
  score       评分变化触发（多个 Alpha 评分大幅变化）
  manual      手动触发

执行流程：
  1. 检测触发条件
  2. 获取当前比例 vs 目标比例
  3. compute_rebalance_trades → 交易清单
  4. estimate_rebalance_cost → 成本评估
  5. 生成 RebalancePlan（含分批计划）
  6. 记录 RebalanceRecord

❌ 不执行任何实际交易
✔  只生成再平衡计划，下游消费
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable

from ..constant import RebalanceTrigger
from ..model.rebalance_model import (
    RebalanceTrade,
    RebalancePlan,
    RebalanceRecord,
)
from ..utils.rebalance_utils import (
    should_rebalance,
    check_scheduled_trigger,
    check_risk_trigger,
    check_score_trigger,
    compute_deviation,
    compute_drift_score,
    compute_rebalance_trades,
    compute_incremental_trades,
    estimate_rebalance_cost,
    is_cost_effective,
)


class RebalancingEngine:
    """
    再平衡引擎（Phase 5）。

    使用方式：
        engine = RebalancingEngine()
        plan = engine.trigger(
            current_ratios = {"A": 0.35, "B": 0.35, "C": 0.30},
            target_ratios  = {"A": 0.40, "B": 0.30, "C": 0.30},
            total_capital  = 10_000_000,
            trigger_type   = "manual",
        )
    """

    def __init__(
        self,
        log_fn:              Callable | None = None,
        dev_threshold:       float = 0.05,     # 偏差触发阈值
        interval_days:       int   = 7,        # 定时再平衡间隔
        var_threshold:       float = 0.025,    # 风险触发 VaR 上限
        dd_threshold:        float = 0.12,     # 风险触发 DD 上限
        n_breach_limit:      int   = 3,        # 风险触发违规 Alpha 上限
        score_change_thresh: float = 0.10,     # 评分变化触发阈值
        n_changed_limit:     int   = 3,        # 评分变化触发 Alpha 数
        max_single_trade:    float = 500_000,  # 单笔最大交易金额
        min_trade_amount:    float = 1_000.0,  # 最小有效交易金额
        commission:          float = 0.0003,
        slippage:            float = 0.0002,
        market_impact:       float = 0.0001,
    ) -> None:
        self._log                = log_fn or (lambda msg: None)
        self._dev_threshold      = dev_threshold
        self._interval_days      = interval_days
        self._var_threshold      = var_threshold
        self._dd_threshold       = dd_threshold
        self._n_breach_limit     = n_breach_limit
        self._score_change_thresh = score_change_thresh
        self._n_changed_limit    = n_changed_limit
        self._max_single_trade   = max_single_trade
        self._min_trade_amount   = min_trade_amount
        self._commission         = commission
        self._slippage           = slippage
        self._market_impact      = market_impact

        self._last_rebalance_at: datetime | None = None
        self._prev_scores:       dict[str, float] = {}
        self._history:           list[RebalanceRecord] = []
        self._plans:             list[RebalancePlan]   = []
        self._rebalance_count    = 0

    # ------------------------------------------------------------------ #
    #  触发检测
    # ------------------------------------------------------------------ #

    def check_trigger_conditions(
        self,
        current_ratios: dict[str, float],
        target_ratios:  dict[str, float],
        risk_snap=None,
        curr_scores:    dict[str, float] | None = None,
        reference_time: datetime | None = None,
    ) -> tuple[str | None, str]:
        """
        自动检测是否满足任一触发条件。

        优先级：risk > score > scheduled > deviation

        Returns
        -------
        (trigger_type | None, reason)
        """
        # 1. 风险触发（最高优先级）
        triggered, reason = check_risk_trigger(
            risk_snap,
            var_threshold  = self._var_threshold,
            dd_threshold   = self._dd_threshold,
            n_breach_limit = self._n_breach_limit,
        )
        if triggered:
            return "risk", reason

        # 2. 评分变化触发
        if curr_scores:
            triggered, reason = check_score_trigger(
                self._prev_scores,
                curr_scores,
                change_threshold = self._score_change_thresh,
                n_changed_limit  = self._n_changed_limit,
            )
            if triggered:
                return "score", reason

        # 3. 定时触发
        if check_scheduled_trigger(
            self._last_rebalance_at,
            interval_days  = self._interval_days,
            reference_time = reference_time,
        ):
            return "scheduled", f"Scheduled interval {self._interval_days}d"

        # 4. 偏差触发
        if should_rebalance(
            current_ratios, target_ratios,
            threshold = self._dev_threshold,
        ):
            drift = compute_drift_score(current_ratios, target_ratios)
            return "scheduled", f"Drift score={drift:.4f} > threshold={self._dev_threshold}"

        return None, ""

    # ------------------------------------------------------------------ #
    #  核心触发
    # ------------------------------------------------------------------ #

    def trigger(
        self,
        current_ratios: dict[str, float],
        target_ratios:  dict[str, float],
        total_capital:  float,
        trigger_type:   str   = "manual",
        reason:         str   = "",
        risk_snap=None,
        curr_scores:    dict[str, float] | None = None,
        force:          bool  = False,
    ) -> RebalancePlan | None:
        """
        触发再平衡，生成 RebalancePlan。

        Parameters
        ----------
        current_ratios : 当前资金分配比例
        target_ratios  : 目标资金分配比例（来自 AllocationEngine）
        total_capital  : 总资金
        trigger_type   : "manual" | "scheduled" | "risk" | "score"
        reason         : 触发原因说明
        risk_snap      : 最新风险快照（用于风险触发判断）
        curr_scores    : 最新评分（用于评分变化触发）
        force          : 强制触发，跳过偏差检查

        Returns
        -------
        RebalancePlan | None  （None = 无需再平衡）
        """
        # 自动触发检测（非手动 / 非强制）
        if trigger_type == "auto":
            detected, auto_reason = self.check_trigger_conditions(
                current_ratios, target_ratios, risk_snap, curr_scores
            )
            if detected is None:
                self._log("[RebalanceEngine] No trigger condition met — skip")
                return None
            trigger_type = detected
            reason       = auto_reason or reason

        # 偏差检查（手动 / 非强制时仍检查是否有实质变化）
        drift = compute_drift_score(current_ratios, target_ratios)
        if not force and drift < 1e-6:
            self._log("[RebalanceEngine] Drift ~0, nothing to rebalance")
            return None

        try:
            trigger_enum = RebalanceTrigger(trigger_type)
        except ValueError:
            trigger_enum = RebalanceTrigger.MANUAL

        # 计算交易清单
        raw_trades = compute_rebalance_trades(
            current_ratios, target_ratios,
            total_capital  = total_capital,
            min_trade      = self._min_trade_amount,
        )
        dev = compute_deviation(current_ratios, target_ratios)

        trade_objs: list[RebalanceTrade] = []
        for aid, delta_amt in raw_trades.items():
            trade_objs.append(RebalanceTrade(
                alpha_id     = aid,
                delta_ratio  = round(dev.get(aid, 0.0), 8),
                delta_amount = delta_amt,
                prev_ratio   = current_ratios.get(aid, 0.0),
                target_ratio = target_ratios.get(aid, 0.0),
            ))

        # 成本估算
        cost = estimate_rebalance_cost(
            raw_trades,
            commission    = self._commission,
            slippage      = self._slippage,
            market_impact = self._market_impact,
        )

        # 分批计划
        batches = compute_incremental_trades(
            raw_trades, max_single=self._max_single_trade
        )

        # 成本有效性（用净值 0.1% 作为预期收益代理）
        expected_gain = total_capital * 0.001
        cost_ok       = is_cost_effective(cost, expected_gain, min_gain_ratio=2.0)

        plan_id = f"PLAN_{uuid.uuid4().hex[:8].upper()}"
        plan = RebalancePlan(
            plan_id        = plan_id,
            trigger        = trigger_enum,
            trigger_reason = reason or f"trigger={trigger_type}",
            trades         = trade_objs,
            prev_ratios    = dict(current_ratios),
            target_ratios  = dict(target_ratios),
            total_capital  = total_capital,
            cost_estimate  = cost,
            drift_score    = drift,
            is_cost_effective = cost_ok,
            batches        = batches,
        )

        record = RebalanceRecord(
            record_id = f"REC_{uuid.uuid4().hex[:8].upper()}",
            plan      = plan,
            status    = "planned",
        )
        self._history.append(record)
        self._plans.append(plan)
        self._last_rebalance_at = datetime.now()
        self._rebalance_count  += 1

        if curr_scores:
            self._prev_scores = dict(curr_scores)

        self._log(
            f"[RebalanceEngine] trigger #{self._rebalance_count}"
            f"  type={trigger_type}"
            f"  n_trades={plan.n_trades}"
            f"  turnover={plan.total_turnover:,.0f}"
            f"  cost={plan.estimated_cost:,.0f}"
            f"  drift={drift:.4f}"
            f"  batches={len(batches)}"
            f"  cost_ok={cost_ok}"
        )
        return plan

    def auto_trigger(
        self,
        current_ratios: dict[str, float],
        target_ratios:  dict[str, float],
        total_capital:  float,
        risk_snap=None,
        curr_scores:    dict[str, float] | None = None,
    ) -> RebalancePlan | None:
        """自动检测触发条件并执行再平衡。"""
        return self.trigger(
            current_ratios = current_ratios,
            target_ratios  = target_ratios,
            total_capital  = total_capital,
            trigger_type   = "auto",
            risk_snap      = risk_snap,
            curr_scores    = curr_scores,
        )

    # ------------------------------------------------------------------ #
    #  记录管理
    # ------------------------------------------------------------------ #

    def approve_plan(self, plan_id: str) -> bool:
        """批准再平衡计划。"""
        for rec in reversed(self._history):
            if rec.plan.plan_id == plan_id:
                rec.approve()
                self._log(f"[RebalanceEngine] plan approved: {plan_id}")
                return True
        return False

    def cancel_plan(self, plan_id: str, reason: str = "") -> bool:
        """取消再平衡计划。"""
        for rec in reversed(self._history):
            if rec.plan.plan_id == plan_id:
                rec.cancel(reason)
                self._log(f"[RebalanceEngine] plan cancelled: {plan_id}  reason={reason}")
                return True
        return False

    # ------------------------------------------------------------------ #
    #  查询
    # ------------------------------------------------------------------ #

    def get_latest_plan(self) -> RebalancePlan | None:
        return self._plans[-1] if self._plans else None

    def get_plans(self, limit: int = 20) -> list[RebalancePlan]:
        return self._plans[-limit:]

    def get_history(self, limit: int = 50) -> list[RebalanceRecord]:
        return self._history[-limit:]

    def get_history_dicts(self, limit: int = 50) -> list[dict]:
        return [r.to_dict() for r in self._history[-limit:]]

    def get_params(self) -> dict:
        return {
            "dev_threshold":       self._dev_threshold,
            "interval_days":       self._interval_days,
            "var_threshold":       self._var_threshold,
            "dd_threshold":        self._dd_threshold,
            "n_breach_limit":      self._n_breach_limit,
            "score_change_thresh": self._score_change_thresh,
            "n_changed_limit":     self._n_changed_limit,
            "max_single_trade":    self._max_single_trade,
            "commission":          self._commission,
        }

    def update_params(self, **kwargs) -> None:
        for k, v in kwargs.items():
            attr = f"_{k}"
            if hasattr(self, attr):
                setattr(self, attr, v)
                self._log(f"[RebalanceEngine] param updated: {k}={v}")

    def summary(self) -> dict:
        plan = self.get_latest_plan()
        return {
            "rebalances":    self._rebalance_count,
            "last_at":       str(self._last_rebalance_at)[:19]
                             if self._last_rebalance_at else None,
            "latest_trades": plan.n_trades     if plan else 0,
            "latest_cost":   plan.estimated_cost if plan else 0.0,
            "latest_drift":  plan.drift_score  if plan else 0.0,
            "phase":         5,
        }
