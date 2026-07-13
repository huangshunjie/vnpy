"""
market_regime_ai/engine/decision_engine.py  (Phase 4)

DecisionEngine — 状态决策引擎（完整实现）。

实现：
  - 接收 MarketRegimeState + VolatilityState + LiquidityState
  - 输出 DecisionSignal（资本调整 / 风险调整 / 策略推荐 / 仓位上限 / 再平衡紧迫度）
  - 维护 DecisionHistory
  - 输出接口供 Phase 5 联动

❌ 无 IO / 无网络 / 纯计算 / 不执行交易
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import (
    MarketRegime, StrategyRecommendation,
    VolatilityRegime, LiquidityLevel,
)
from ..model.decision_model import DecisionSignal, DecisionHistory
from ..utils.decision_utils import (
    map_regime_to_strategy,
    compute_capital_adjustment,
    compute_risk_adjustment,
    compute_position_limit,
    compute_rebalance_urgency,
    build_decision_summary,
)


class DecisionEngine:
    """
    状态决策引擎（Phase 4 完整实现）。

    用法：
        engine = DecisionEngine(log_fn=print)
        signal = engine.decide(regime_state, vol_state, liq_state)
    """

    def __init__(
        self,
        log_fn:           Callable | None = None,
        history_max_len:  int   = 200,
        capital_min:      float = 0.40,
        capital_max:      float = 1.50,
        risk_min:         float = 0.30,
        risk_max:         float = 1.30,
    ) -> None:
        self._log          = log_fn or (lambda m: None)
        self._history      = DecisionHistory(max_len=history_max_len)
        self._capital_min  = capital_min
        self._capital_max  = capital_max
        self._risk_min     = risk_min
        self._risk_max     = risk_max
        self._bar_count    = 0
        self._last_signal  = DecisionSignal()

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def decide(
        self,
        regime_state = None,
        vol_state    = None,
        liq_state    = None,
    ) -> DecisionSignal:
        """
        生成决策信号。

        Parameters
        ----------
        regime_state : MarketRegimeState（来自 RegimeEngine）
        vol_state    : VolatilityState（来自 VolatilityEngine）
        liq_state    : LiquidityState（来自 LiquidityEngine）

        Returns
        -------
        DecisionSignal
        """
        self._bar_count += 1

        # ── 提取因子 ──────────────────────────────────────────────────
        regime      = MarketRegime.UNKNOWN
        confidence  = 0.0
        stability   = 0.0
        changed     = False

        if regime_state is not None:
            regime     = regime_state.regime
            confidence = float(getattr(regime_state, "confidence_score", 0.0))
            stability  = float(getattr(regime_state, "stability",        0.0))
            changed    = bool(getattr(regime_state,  "regime_changed",   False))

        vol_regime = VolatilityRegime.NORMAL
        if vol_state is not None:
            vol_regime = getattr(vol_state, "regime", VolatilityRegime.NORMAL)

        liq_level = LiquidityLevel.NORMAL
        if liq_state is not None:
            liq_level = getattr(liq_state, "level", LiquidityLevel.NORMAL)

        # ── 策略推荐 ──────────────────────────────────────────────────
        recommendation = map_regime_to_strategy(regime)

        # ── 资本调整系数 ──────────────────────────────────────────────
        capital_adj = compute_capital_adjustment(
            regime     = regime,
            confidence = confidence,
            vol_regime = vol_regime,
            liq_level  = liq_level,
            min_factor = self._capital_min,
            max_factor = self._capital_max,
        )

        # ── 风险调整系数 ──────────────────────────────────────────────
        risk_adj = compute_risk_adjustment(
            regime     = regime,
            confidence = confidence,
            vol_regime = vol_regime,
            min_factor = self._risk_min,
            max_factor = self._risk_max,
        )

        # ── 仓位上限 ──────────────────────────────────────────────────
        position_limit = compute_position_limit(
            regime     = regime,
            confidence = confidence,
        )

        # ── 再平衡紧迫度 ──────────────────────────────────────────────
        rebalance_urgency = compute_rebalance_urgency(
            regime_changed = changed,
            regime         = regime,
            confidence     = confidence,
            stability      = stability,
        )

        # ── 行动建议 ──────────────────────────────────────────────────
        summary = build_decision_summary(
            regime            = regime,
            recommendation    = recommendation,
            capital_adj       = capital_adj,
            risk_adj          = risk_adj,
            position_limit    = position_limit,
            rebalance_urgency = rebalance_urgency,
            confidence        = confidence,
        )
        action = summary["action"]

        # ── 构建信号 ──────────────────────────────────────────────────
        signal = DecisionSignal(
            regime             = regime,
            recommendation     = recommendation,
            capital_adjustment = capital_adj,
            risk_adjustment    = risk_adj,
            position_limit     = position_limit,
            rebalance_urgency  = rebalance_urgency,
            confidence         = confidence,
            action             = action,
            regime_changed     = changed,
            created_at         = datetime.now(),
            meta               = {
                "bar_count": self._bar_count,
                "vol_regime": vol_regime.value,
                "liq_level":  liq_level.value,
                "stability":  round(stability, 4),
            },
        )

        self._history.append(signal)
        self._last_signal = signal

        self._log(
            f"[DecisionEngine] bar={self._bar_count}"
            f"  regime={regime.value:10s}"
            f"  cap={capital_adj:.3f}"
            f"  risk={risk_adj:.3f}"
            f"  action={action}"
        )

        return signal

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_signal(self) -> DecisionSignal:
        return self._last_signal

    def get_history(self, limit: int = 20) -> list[dict]:
        return self._history.get_records(limit=limit)

    def get_capital_adjustment(self) -> float:
        return self._last_signal.capital_adjustment

    def get_risk_adjustment(self) -> float:
        return self._last_signal.risk_adjustment

    def get_recommendation(self) -> StrategyRecommendation:
        return self._last_signal.recommendation

    def get_rebalance_urgency(self) -> float:
        return self._last_signal.rebalance_urgency

    def summary(self) -> dict:
        s = self._last_signal
        return {
            "regime":             s.regime.value,
            "recommendation":     s.recommendation.value,
            "capital_adjustment": round(s.capital_adjustment, 4),
            "risk_adjustment":    round(s.risk_adjustment,    4),
            "position_limit":     round(s.position_limit,     4),
            "rebalance_urgency":  round(s.rebalance_urgency,  4),
            "action":             s.action,
            "history_len":        len(self._history),
            "phase":              4,
        }

    # ------------------------------------------------------------------ #
    #  参数更新
    # ------------------------------------------------------------------ #

    def update_params(
        self,
        capital_min: float | None = None,
        capital_max: float | None = None,
        risk_min:    float | None = None,
        risk_max:    float | None = None,
    ) -> None:
        if capital_min is not None: self._capital_min = capital_min
        if capital_max is not None: self._capital_max = capital_max
        if risk_min    is not None: self._risk_min    = risk_min
        if risk_max    is not None: self._risk_max    = risk_max
