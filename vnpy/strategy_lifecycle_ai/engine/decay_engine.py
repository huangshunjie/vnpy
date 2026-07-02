"""
strategy_lifecycle_ai/engine/decay_engine.py  (Phase 3)

DecayEngine — 策略衰减检测引擎（完整实现）。

实现：
  - detect()        完整衰减检测流水线
  - get_state()     获取当前衰减状态
  - get_decaying()  获取所有衰减中的策略
  - get_critical()  获取危急衰减策略
  - 维护 DecayHistory

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import DecayLevel, StrategyPhase
from ..model.decay_model import DecayState, DecayHistory
from ..utils.decay_utils import (
    compute_sharpe_slope,
    compute_dd_expansion,
    compute_ic_decay_proxy,
    compute_performance_slope,
    compute_decay_score,
    classify_decay_level,
    compute_decay_persistence,
    compute_regime_sensitivity,
)


class DecayEngine:
    """策略衰减检测引擎（Phase 3 完整实现）。"""

    def __init__(
        self,
        log_fn:            Callable | None = None,
        sharpe_window:     int   = 10,
        dd_window:         int   = 10,
        ic_window:         int   = 20,
        perf_window:       int   = 20,
        history_max:       int   = 500,
        critical_threshold: float = 0.75,
        severe_threshold:   float = 0.55,
    ) -> None:
        self._log              = log_fn or (lambda m: None)
        self._sharpe_window    = sharpe_window
        self._dd_window        = dd_window
        self._ic_window        = ic_window
        self._perf_window      = perf_window
        self._history_max      = history_max
        self._critical_thr     = critical_threshold
        self._severe_thr       = severe_threshold

        self._states:    dict[str, DecayState]   = {}
        self._histories: dict[str, DecayHistory] = {}

    # ------------------------------------------------------------------ #
    #  核心接口
    # ------------------------------------------------------------------ #

    def detect(
        self,
        strategy_id:    str,
        sharpe_series:  list[float],
        dd_series:      list[float],
        returns:        list[float],
        pnl_series:     list[float],
        regime_context: dict | None = None,
    ) -> DecayState:
        """
        完整衰减检测流水线。

        Parameters
        ----------
        strategy_id   : 策略 ID
        sharpe_series : 历史 Sharpe 序列（由 PerformanceEngine 提供）
        dd_series     : 历史最大回撤序列
        returns       : 日收益率序列
        pnl_series    : 净值序列
        regime_context: 市场状态上下文（可选，含 regime_weight_modifier 等）

        Returns
        -------
        DecayState
        """
        # ── 四个衰减指标 ──────────────────────────────────────────────
        sharpe_slope = compute_sharpe_slope(sharpe_series, self._sharpe_window)
        dd_expansion = compute_dd_expansion(dd_series,     self._dd_window)
        ic_decay     = compute_ic_decay_proxy(returns,     self._ic_window)
        perf_slope   = compute_performance_slope(pnl_series, self._perf_window)

        # ── 市场状态修正 ──────────────────────────────────────────────
        # 若市场处于高波动/熊市（regime_modifier < 0.85），适度放宽衰减判定
        regime_modifier = 1.0
        if regime_context:
            regime_modifier = float(regime_context.get(
                "regime_weight_modifier", 1.0))

        # 综合评分（市场恶化时降低 ic_decay 权重，避免误判）
        if regime_modifier < 0.85:
            weights = {
                "sharpe_slope": 0.40,
                "dd_expansion": 0.35,
                "ic_decay":     0.10,
                "perf_slope":   0.15,
            }
        else:
            weights = None  # 默认权重

        decay_score = compute_decay_score(
            sharpe_slope, dd_expansion, ic_decay, perf_slope, weights)

        # ── 等级分类 ──────────────────────────────────────────────────
        decay_level = classify_decay_level(
            decay_score, sharpe_slope, dd_expansion)

        # ── 持续天数 ──────────────────────────────────────────────────
        if strategy_id not in self._histories:
            self._histories[strategy_id] = DecayHistory(
                strategy_id, self._history_max)
        history = self._histories[strategy_id]
        decay_days = compute_decay_persistence(history.get_level_history())
        if decay_level != DecayLevel.NONE:
            decay_days += 1

        # ── 等级变化检测 ──────────────────────────────────────────────
        prev_state  = self._states.get(strategy_id)
        prev_level  = prev_state.decay_level if prev_state else DecayLevel.NONE
        level_changed = (decay_level != prev_level)

        # ── 市场状态敏感度（可选，数据量不足时跳过）──────────────────
        regime_sensitivity = 0.0
        if regime_context:
            bull_rets = regime_context.get("bull_returns", [])
            bear_rets = regime_context.get("bear_returns", [])
            if bull_rets and bear_rets:
                regime_sensitivity = compute_regime_sensitivity(
                    bull_rets, bear_rets)

        state = DecayState(
            strategy_id        = strategy_id,
            decay_level        = decay_level,
            decay_score        = decay_score,
            sharpe_slope       = sharpe_slope,
            dd_expansion       = dd_expansion,
            ic_decay_proxy     = ic_decay,
            perf_slope         = perf_slope,
            decay_days         = decay_days,
            regime_sensitivity = regime_sensitivity,
            detected_at        = datetime.now(),
            prev_level         = prev_level,
            level_changed      = level_changed,
        )

        self._states[strategy_id] = state
        history.append(state)

        if decay_level != DecayLevel.NONE:
            self._log(
                f"[DecayEngine] {strategy_id}"
                f"  level={decay_level.value}"
                f"  score={decay_score:.3f}"
                f"  days={decay_days}"
                f"  sh_slope={sharpe_slope:.4f}"
                f"  dd_exp={dd_expansion:.4f}"
                f"  changed={level_changed}"
            )

        return state

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_state(self, strategy_id: str) -> DecayState:
        if strategy_id not in self._states:
            self._states[strategy_id] = DecayState(strategy_id=strategy_id)
        return self._states[strategy_id]

    def get_all(self) -> list[DecayState]:
        return list(self._states.values())

    def get_decaying(self) -> list[DecayState]:
        """获取所有处于衰减状态（非 NONE）的策略。"""
        return [s for s in self._states.values()
                if s.decay_level != DecayLevel.NONE]

    def get_critical(self) -> list[DecayState]:
        """获取危急衰减策略（CRITICAL 等级）。"""
        return [s for s in self._states.values()
                if s.decay_level == DecayLevel.CRITICAL]

    def get_severe_or_above(self) -> list[DecayState]:
        """获取 SEVERE 及以上等级的策略。"""
        return [s for s in self._states.values()
                if s.decay_level in (
                    DecayLevel.SEVERE, DecayLevel.CRITICAL)]

    def get_by_level(self, level: DecayLevel) -> list[DecayState]:
        return [s for s in self._states.values()
                if s.decay_level == level]

    def get_history(
        self,
        strategy_id: str,
        limit: int = 30,
    ) -> list[dict]:
        h = self._histories.get(strategy_id)
        return h.get_records(limit=limit) if h else []

    def get_score_series(self, strategy_id: str) -> list[float]:
        h = self._histories.get(strategy_id)
        return h.get_score_series() if h else []

    def get_level_changed_strategies(self) -> list[DecayState]:
        """获取本 bar 衰减等级发生变化的策略（用于事件广播）。"""
        return [s for s in self._states.values() if s.level_changed]

    # ------------------------------------------------------------------ #
    #  参数更新
    # ------------------------------------------------------------------ #

    def update_params(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, f"_{k}"):
                setattr(self, f"_{k}", v)

    # ------------------------------------------------------------------ #
    #  摘要
    # ------------------------------------------------------------------ #

    def summary(self) -> dict:
        all_s     = self.get_all()
        decaying  = self.get_decaying()
        critical  = self.get_critical()
        by_level: dict[str, int] = {}
        for s in all_s:
            k = s.decay_level.value
            by_level[k] = by_level.get(k, 0) + 1
        return {
            "tracked":   len(all_s),
            "decaying":  len(decaying),
            "critical":  len(critical),
            "by_level":  by_level,
            "phase":     3,
        }
