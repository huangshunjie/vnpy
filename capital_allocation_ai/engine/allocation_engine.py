"""
capital_allocation_ai/engine/allocation_engine.py  (Phase 3)

CapitalAllocationEngine — 资金分配引擎（完整实现）。

分配逻辑：
  1. 从 ScoringEngine 拉取 capital_score
  2. normalize_scores → 原始比例
  3. apply_capital_constraints → 约束后比例（max_ratio / min_ratio）
  4. 与上期比较 → 计算 flow_direction / delta
  5. 生成 CapitalFlowSignal 列表
  6. 生成 AllocationSnapshot

公式：
  Capital_i = Score_i / Sum(All Scores)

❌ 不执行任何交易逻辑
✔  只计算分配比例，发出资金流动信号
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable

from ..constant import AllocationStatus, CapitalFlowDirection
from ..model.allocation_model import (
    CapitalAllocation,
    CapitalFlowSignal,
    AllocationSnapshot,
)
from ..utils.capital_utils import (
    normalize_scores,
    apply_capital_constraints,
    compute_flow_direction,
    compute_concentration,
    compute_effective_n,
    compute_allocation_delta,
    compute_total_turnover,
    build_allocation_summary,
)


class CapitalAllocationEngine:
    """
    资金分配引擎（Phase 3）。

    使用方式：
        engine = CapitalAllocationEngine()
        snapshot = engine.calculate(
            scores        = {"A": 0.6, "B": 0.3, "C": 0.1},
            total_capital = 10_000_000,
        )
    """

    def __init__(
        self,
        log_fn:      Callable | None = None,
        max_ratio:   float = 0.30,
        min_ratio:   float = 0.005,
        flow_threshold: float = 0.005,
    ) -> None:
        self._log           = log_fn or (lambda msg: None)
        self._max_ratio     = max_ratio
        self._min_ratio     = min_ratio
        self._flow_threshold = flow_threshold

        self._allocations:  dict[str, CapitalAllocation] = {}
        self._prev_ratios:  dict[str, float]             = {}
        self._snapshots:    list[AllocationSnapshot]     = []
        self._signals:      list[CapitalFlowSignal]      = []
        self._calc_count    = 0

    # ------------------------------------------------------------------ #
    #  核心计算
    # ------------------------------------------------------------------ #

    def calculate(
        self,
        scores:        dict[str, float],
        total_capital: float,
        max_ratio:     float | None = None,
        min_ratio:     float | None = None,
    ) -> AllocationSnapshot:
        """
        计算资金分配方案。

        Parameters
        ----------
        scores        : {alpha_id: capital_score}
        total_capital : 总可分配资金
        max_ratio     : 单 Alpha 最大比例（覆盖默认值）
        min_ratio     : 单 Alpha 最小比例（覆盖默认值）

        Returns
        -------
        AllocationSnapshot  本次分配快照
        """
        max_r = max_ratio if max_ratio is not None else self._max_ratio
        min_r = min_ratio if min_ratio is not None else self._min_ratio

        # Step 1: 归一化评分 → 原始比例
        raw_ratios = normalize_scores(scores, min_clip=0.0)

        # Step 2: 施加上下限约束
        constrained = apply_capital_constraints(
            raw_ratios, max_ratio=max_r, min_ratio=min_r
        )

        # Step 3: 计算流向 & delta
        delta_map    = compute_allocation_delta(self._prev_ratios, constrained)
        turnover     = compute_total_turnover(self._prev_ratios, constrained)
        concentration = compute_concentration(constrained)
        effective_n   = compute_effective_n(constrained)

        # Step 4: 构建 CapitalAllocation 列表
        allocations: dict[str, CapitalAllocation] = {}
        signals:     list[CapitalFlowSignal]      = []

        for alpha_id, ratio in constrained.items():
            prev_r     = self._prev_ratios.get(alpha_id, 0.0)
            delta_r    = delta_map.get(alpha_id, 0.0)
            direction  = compute_flow_direction(prev_r, ratio, self._flow_threshold)
            alloc_amt  = round(ratio * total_capital, 2)
            prev_amt   = round(prev_r * total_capital, 2)

            alloc = CapitalAllocation(
                alpha_id       = alpha_id,
                total_capital  = total_capital,
                allocated      = alloc_amt,
                ratio          = ratio,
                prev_allocated = prev_amt,
                prev_ratio     = prev_r,
                delta_ratio    = round(delta_r, 8),
                flow_direction = CapitalFlowDirection(direction),
                capital_score  = scores.get(alpha_id, 0.0),
                status         = AllocationStatus.ACTIVE if ratio > 1e-8
                                 else AllocationStatus.SUSPENDED,
            )
            allocations[alpha_id] = alloc

            # 生成资金流动信号（仅有实质变化时）
            if direction != "hold":
                signal = CapitalFlowSignal(
                    signal_id    = f"SIG_{uuid.uuid4().hex[:8].upper()}",
                    alpha_id     = alpha_id,
                    direction    = CapitalFlowDirection(direction),
                    target_ratio  = ratio,
                    target_amount = alloc_amt,
                    delta_amount  = round((ratio - prev_r) * total_capital, 2),
                    urgency       = "high" if abs(delta_r) > 0.05 else "normal",
                    reason        = (
                        f"score={scores.get(alpha_id, 0):.4f}  "
                        f"ratio {prev_r:.4f} → {ratio:.4f}"
                    ),
                )
                signals.append(signal)

        # Step 5: 构建 snapshot
        snap_id  = f"SNAP_{uuid.uuid4().hex[:8].upper()}"
        snapshot = AllocationSnapshot(
            snapshot_id   = snap_id,
            total_capital = total_capital,
            allocations   = allocations,
            signals       = signals,
            concentration = concentration,
            effective_n   = effective_n,
            turnover      = turnover,
        )

        # Step 6: 持久化
        self._allocations = allocations
        self._prev_ratios = {k: v.ratio for k, v in allocations.items()}
        self._snapshots.append(snapshot)
        self._signals.extend(signals)
        self._calc_count += 1

        self._log(
            f"[AllocationEngine] calculate #{self._calc_count}"
            f"  n={len(allocations)}"
            f"  capital={total_capital:,.0f}"
            f"  HHI={concentration:.4f}"
            f"  eff_N={effective_n:.1f}"
            f"  turnover={turnover:.4f}"
            f"  signals={len(signals)}"
        )
        return snapshot

    # ------------------------------------------------------------------ #
    #  动态资金流动（高分增配，低分减配）
    # ------------------------------------------------------------------ #

    def adjust_by_score_change(
        self,
        new_scores:    dict[str, float],
        total_capital: float,
        boost_factor:  float = 1.2,
        cut_factor:    float = 0.8,
        threshold:     float = 0.05,
    ) -> AllocationSnapshot:
        """
        基于评分变化动态调整资金（Phase 3 高级功能）。

        规则：
          若某 Alpha 的评分比上次上升 >= threshold → 乘以 boost_factor
          若某 Alpha 的评分比上次下降 >= threshold → 乘以 cut_factor
          否则保持不变

        Parameters
        ----------
        new_scores    : 最新评分
        total_capital : 总资金
        boost_factor  : 加仓倍率（默认 1.2 = 增加 20%）
        cut_factor    : 减仓倍率（默认 0.8 = 减少 20%）
        threshold     : 评分变化触发阈值

        Returns
        -------
        AllocationSnapshot  调整后的分配快照
        """
        prev_scores = {
            k: v.capital_score for k, v in self._allocations.items()
        }
        adjusted: dict[str, float] = {}
        for alpha_id, score in new_scores.items():
            prev_sc = prev_scores.get(alpha_id, score)
            delta   = score - prev_sc
            if delta >= threshold:
                adjusted[alpha_id] = score * boost_factor
            elif delta <= -threshold:
                adjusted[alpha_id] = max(score * cut_factor, 0.0)
            else:
                adjusted[alpha_id] = score

        return self.calculate(adjusted, total_capital)

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_allocations(self) -> dict[str, CapitalAllocation]:
        return dict(self._allocations)

    def get_ratios(self) -> dict[str, float]:
        return {k: v.ratio for k, v in self._allocations.items()}

    def get_latest_snapshot(self) -> AllocationSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def get_snapshots(self, limit: int = 20) -> list[AllocationSnapshot]:
        return self._snapshots[-limit:]

    def get_signals(self, limit: int = 100) -> list[CapitalFlowSignal]:
        return self._signals[-limit:]

    def get_thresholds(self) -> dict:
        return {
            "max_ratio":      self._max_ratio,
            "min_ratio":      self._min_ratio,
            "flow_threshold": self._flow_threshold,
        }

    def update_thresholds(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, f"_{k}"):
                setattr(self, f"_{k}", v)
                self._log(f"[AllocationEngine] threshold updated: {k}={v}")

    def summary(self) -> dict:
        if not self._allocations:
            return {"allocated": 0, "total_capital": 0.0, "phase": 3}
        snap = self.get_latest_snapshot()
        return {
            "allocated":      len(self._allocations),
            "active":         sum(1 for a in self._allocations.values()
                                  if a.ratio > 1e-8),
            "total_capital":  snap.total_capital if snap else 0.0,
            "concentration":  snap.concentration if snap else 0.0,
            "effective_n":    snap.effective_n   if snap else 0.0,
            "turnover":       snap.turnover       if snap else 0.0,
            "n_signals":      len(self._signals),
            "calc_count":     self._calc_count,
            "phase":          3,
        }
