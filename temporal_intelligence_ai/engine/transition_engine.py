"""
temporal_intelligence_ai/engine/transition_engine.py

Regime Transition Engine — 状态转移检测引擎（Phase 5）。

职责：
  - 检测三类状态转移：Regime Shift / Volatility Break / Liquidity Regime
  - 估算各 Regime 概率分布
  - 计算综合转移概率与置信度
  - 维护已确认转移事件列表
  - 输出 TransitionState，由主引擎派发 EVENT_TRANSITION_DETECTED

严格禁止：价格预测、交易信号生成、任何前瞻偏差
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ..constant import CyclePhase, RegimeType, TransitionType
from ..model.transition_model import (
    TransitionEvent,
    TransitionHistory,
    TransitionState,
)
from ..utils.transition_utils import (
    compute_transition_probability,
    detect_liquidity_regime,
    detect_regime_shift,
    detect_volatility_break,
    estimate_regime_probabilities,
)

_CONFIRM_THRESHOLD = 0.60   # 置信度超过此值才生成确认事件
_DEFAULT_WEIGHTS   = (0.45, 0.35, 0.20)


class TransitionEngine:
    """
    Regime Transition Engine.

    调用流程：
      1. configure()      — 设置检测参数
      2. set_context()    — 注入当前 Regime / 周期阶段（来自 CycleEngine）
      3. update_series()  — 更新价格 / 收益率 / 成交量序列
      4. detect()         — 触发一次完整转移检测
      5. get_state()      — 获取最新 TransitionState
      6. get_history()    — 获取完整历史
    """

    def __init__(self) -> None:
        self._prices:  List[float] = []
        self._returns: List[float] = []
        self._volumes: List[float] = []

        self._current_regime: RegimeType  = RegimeType.UNKNOWN
        self._current_phase:  CyclePhase  = CyclePhase.UNKNOWN
        self._current_vol:    float       = 0.0
        self._current_trend:  float       = 0.0

        self._current:  Optional[TransitionState] = None
        self._history:  TransitionHistory         = TransitionHistory()

        # 配置参数
        self._regime_fast:    int   = 10
        self._regime_slow:    int   = 40
        self._regime_thresh:  float = 2.0
        self._vol_short:      int   = 10
        self._vol_long:       int   = 40
        self._vol_ratio:      float = 1.8
        self._liq_short:      int   = 10
        self._liq_long:       int   = 40
        self._liq_thresh:     float = 1.5
        self._weights         = _DEFAULT_WEIGHTS
        self._confirm_thresh: float = _CONFIRM_THRESHOLD

    # ── configuration ────────────────────────────────────────────────

    def configure(
        self,
        regime_fast:    int   = 10,
        regime_slow:    int   = 40,
        regime_thresh:  float = 2.0,
        vol_short:      int   = 10,
        vol_long:       int   = 40,
        vol_ratio:      float = 1.8,
        liq_short:      int   = 10,
        liq_long:       int   = 40,
        liq_thresh:     float = 1.5,
        weights:        tuple = _DEFAULT_WEIGHTS,
        confirm_thresh: float = _CONFIRM_THRESHOLD,
    ) -> None:
        self._regime_fast    = regime_fast
        self._regime_slow    = regime_slow
        self._regime_thresh  = regime_thresh
        self._vol_short      = vol_short
        self._vol_long       = vol_long
        self._vol_ratio      = vol_ratio
        self._liq_short      = liq_short
        self._liq_long       = liq_long
        self._liq_thresh     = liq_thresh
        self._weights        = weights
        self._confirm_thresh = confirm_thresh

    # ── context injection ────────────────────────────────────────────

    def set_context(
        self,
        regime:      RegimeType,
        phase:       CyclePhase,
        current_vol: float,
        current_trend: float = 0.0,
    ) -> None:
        """注入当前市场上下文（由 TemporalEngine 在 CycleEngine 分析后调用）。"""
        self._current_regime = regime
        self._current_phase  = phase
        self._current_vol    = current_vol
        self._current_trend  = current_trend

    # ── data update ──────────────────────────────────────────────────

    def update_series(
        self,
        prices:  Optional[List[float]] = None,
        returns: Optional[List[float]] = None,
        volumes: Optional[List[float]] = None,
    ) -> None:
        """
        更新价格 / 收益率 / 成交量序列（追加最新数据）。

        传 None 表示不更新该序列。
        """
        if prices  is not None:
            self._prices  = list(prices)
        if returns is not None:
            self._returns = list(returns)
        if volumes is not None:
            self._volumes = list(volumes)

    # ── core detection ───────────────────────────────────────────────

    def detect(self) -> Optional[TransitionState]:
        """
        执行一次完整状态转移检测。

        Returns:
            TransitionState 或 None（数据不足时）
        """
        min_data = max(self._regime_slow, self._vol_long, self._liq_long) + 4
        if len(self._returns) < min_data and len(self._prices) < min_data:
            return None

        # 三类检测器独立运行
        regime_sig = detect_regime_shift(
            returns   = self._returns,
            fast_window = self._regime_fast,
            slow_window = self._regime_slow,
            threshold   = self._regime_thresh,
        )

        vol_sig = detect_volatility_break(
            prices       = self._prices,
            short_window = self._vol_short,
            long_window  = self._vol_long,
            break_ratio  = self._vol_ratio,
        )

        liq_sig = detect_liquidity_regime(
            volumes      = self._volumes if self._volumes else [1.0] * len(self._returns),
            returns      = self._returns,
            short_window = self._liq_short,
            long_window  = self._liq_long,
            threshold    = self._liq_thresh,
        )

        # Regime 概率估计
        regime_probs = estimate_regime_probabilities(
            volatility                  = self._current_vol,
            trend                       = self._current_trend,
            regime_signal_strength      = regime_sig.strength,
            volatility_signal_strength  = vol_sig.strength,
        )

        # 综合转移概率
        t_prob, t_conf = compute_transition_probability(
            regime_signal     = regime_sig,
            volatility_signal = vol_sig,
            liquidity_signal  = liq_sig,
            weights           = self._weights,
        )

        is_transitioning = t_prob > 0.4

        # 如果置信度超过确认阈值，生成事件
        latest_event: Optional[TransitionEvent] = None
        if t_conf >= self._confirm_thresh:
            new_regime = RegimeType(regime_probs.dominant())
            if new_regime != self._current_regime:
                # 判断主导转移类型
                sigs = [regime_sig, vol_sig, liq_sig]
                dominant_sig = max(sigs, key=lambda s: s.strength)
                latest_event = TransitionEvent(
                    timestamp        = datetime.now(),
                    transition_type  = dominant_sig.signal_type,
                    from_regime      = self._current_regime,
                    to_regime        = new_regime,
                    from_phase       = self._current_phase,
                    confidence       = t_conf,
                    trigger_signals  = [s for s in sigs if s.is_triggered],
                    description      = (
                        f"{self._current_regime.value} → {new_regime.value}  "
                        f"置信度={t_conf:.1%}"
                    ),
                )
                self._history.append_event(latest_event)

        state = TransitionState(
            timestamp              = datetime.now(),
            regime_probs           = regime_probs,
            regime_signal          = regime_sig,
            volatility_signal      = vol_sig,
            liquidity_signal       = liq_sig,
            transition_prob        = t_prob,
            transition_confidence  = t_conf,
            is_transitioning       = is_transitioning,
            latest_event           = latest_event,
            current_regime         = self._current_regime,
            current_phase          = self._current_phase,
        )

        self._current = state
        self._history.append_snapshot(state)
        return state

    # ── accessors ────────────────────────────────────────────────────

    def get_state(self) -> Optional[TransitionState]:
        return self._current

    def get_history(self) -> TransitionHistory:
        return self._history

    def get_summary(self) -> dict:
        if self._current is None:
            return {
                "transition_prob":       0.0,
                "transition_confidence": 0.0,
                "is_transitioning":      False,
                "current_regime":        RegimeType.UNKNOWN.value,
                "event_count":           0,
            }
        return {
            "transition_prob":       round(self._current.transition_prob, 4),
            "transition_confidence": round(self._current.transition_confidence, 4),
            "is_transitioning":      self._current.is_transitioning,
            "current_regime":        self._current.current_regime.value,
            "event_count":           len(self._history.events),
        }
