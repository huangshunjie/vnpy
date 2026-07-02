"""
market_regime_ai/engine/regime_engine.py  (Phase 2)

RegimeEngine — 市场状态识别引擎（完整实现）。

实现：
  - 接收 VolatilityState / TrendState / LiquidityState
  - 计算多因子评分
  - 输出 MarketRegimeState（含置信度、因子分解、稳定性）
  - 维护 RegimeHistory（状态序列 + 切换记录）

❌ 无 IO / 无网络 / 无线程 / 纯计算
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import (
    MarketRegime, RegimeConfidence, StrategyRecommendation,
    VolatilityRegime, TrendDirection, LiquidityLevel,
)
from ..model.regime_model import MarketRegimeState, RegimeHistory
from ..utils.regime_utils import (
    compute_regime_scores,
    classify_regime,
    detect_regime_change,
    compute_regime_stability,
    score_to_confidence,
    build_regime_summary,
    normalize_score,
)


# ─────────────────────────────────────────────────────────────────────────────
#  状态 → 策略推荐 映射表
# ─────────────────────────────────────────────────────────────────────────────

_REGIME_TO_STRATEGY: dict[MarketRegime, StrategyRecommendation] = {
    MarketRegime.BULL:     StrategyRecommendation.MOMENTUM,
    MarketRegime.BEAR:     StrategyRecommendation.DEFENSIVE,
    MarketRegime.SIDEWAYS: StrategyRecommendation.MEAN_REVERSION,
    MarketRegime.HIGH_VOL: StrategyRecommendation.RISK_REDUCTION,
    MarketRegime.LOW_LIQ:  StrategyRecommendation.REDUCE_FREQ,
    MarketRegime.UNKNOWN:  StrategyRecommendation.NEUTRAL,
}


# ─────────────────────────────────────────────────────────────────────────────
#  因子状态 → 数值映射
# ─────────────────────────────────────────────────────────────────────────────

_VOL_REGIME_SCORE: dict[VolatilityRegime, float] = {
    VolatilityRegime.LOW:     0.15,
    VolatilityRegime.NORMAL:  0.40,
    VolatilityRegime.HIGH:    0.70,
    VolatilityRegime.EXTREME: 0.95,
}

_TREND_DIR_SIGN: dict[TrendDirection, float] = {
    TrendDirection.STRONG_UP:   +1.0,
    TrendDirection.WEAK_UP:     +0.5,
    TrendDirection.FLAT:         0.0,
    TrendDirection.WEAK_DOWN:   -0.5,
    TrendDirection.STRONG_DOWN: -1.0,
}

_LIQ_LEVEL_SCORE: dict[LiquidityLevel, float] = {
    LiquidityLevel.HIGH:     0.85,
    LiquidityLevel.NORMAL:   0.60,
    LiquidityLevel.LOW:      0.30,
    LiquidityLevel.VERY_LOW: 0.05,
}


def _vol_state_to_score(vol_state) -> float:
    """VolatilityState → vol_score [0,1]。"""
    if vol_state is None:
        return 0.4
    if hasattr(vol_state, "vol_percentile") and vol_state.vol_percentile > 0:
        return float(vol_state.vol_percentile)
    return _VOL_REGIME_SCORE.get(vol_state.regime, 0.4)


def _trend_state_to_score_sign(trend_state) -> tuple[float, float]:
    """TrendState → (trend_score [0,1], trend_sign {-1, 0, +1})。"""
    if trend_state is None:
        return 0.0, 0.0
    strength = float(getattr(trend_state, "strength", 0.0))
    direction = getattr(trend_state, "direction", TrendDirection.FLAT)
    sign = _TREND_DIR_SIGN.get(direction, 0.0)
    return strength, sign


def _liq_state_to_score(liq_state) -> float:
    """LiquidityState → liq_score [0,1]（高 = 流动性好）。"""
    if liq_state is None:
        return 0.6
    ill = getattr(liq_state, "illiquidity_score", -1.0)
    if ill >= 0:
        return round(1.0 - float(ill), 6)
    return _LIQ_LEVEL_SCORE.get(liq_state.level, 0.6)


class RegimeEngine:
    """
    市场状态识别引擎（Phase 2 完整实现）。

    用法：
        engine = RegimeEngine(log_fn=print)
        state  = engine.detect(vol_state, trend_state, liq_state,
                               corr_score=0.3)
    """

    def __init__(
        self,
        log_fn:              Callable | None = None,
        history_max_len:     int   = 500,
        min_confidence:      float = 0.40,
        high_vol_threshold:  float = 0.65,
        low_liq_threshold:   float = 0.65,
        stability_window:    int   = 5,
    ) -> None:
        self._log            = log_fn or (lambda m: None)
        self._state          = MarketRegimeState()
        self._history        = RegimeHistory(max_len=history_max_len)
        self._min_confidence = min_confidence
        self._high_vol_thr   = high_vol_threshold
        self._low_liq_thr    = low_liq_threshold
        self._stab_window    = stability_window
        self._bar_count      = 0

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def detect(
        self,
        vol_state   = None,
        trend_state = None,
        liq_state   = None,
        corr_score: float = 0.0,
    ) -> MarketRegimeState:
        """
        多因子状态识别（Phase 2 完整实现）。

        Parameters
        ----------
        vol_state   : VolatilityState（可为 None）
        trend_state : TrendState（可为 None）
        liq_state   : LiquidityState（可为 None）
        corr_score  : 相关性因子评分 [0,1]，高 = 高相关

        Returns
        -------
        MarketRegimeState
        """
        self._bar_count += 1

        # 1. 因子 → 标准化评分
        vol_s                = _vol_state_to_score(vol_state)
        trend_s, trend_sign  = _trend_state_to_score_sign(trend_state)
        liq_s                = _liq_state_to_score(liq_state)
        corr_s               = float(corr_score)

        # 2. 多因子评分矩阵
        scores = compute_regime_scores(
            vol_score   = vol_s,
            trend_score = trend_s,
            trend_sign  = trend_sign,
            liq_score   = liq_s,
            corr_score  = corr_s,
        )

        # 3. 状态分类
        regime, conf_score = classify_regime(
            scores              = scores,
            min_score           = self._min_confidence,
            high_vol_threshold  = self._high_vol_thr,
            low_liq_threshold   = self._low_liq_thr,
        )

        # 4. 置信度枚举
        confidence = score_to_confidence(conf_score)

        # 5. 状态持续计数 + 切换检测
        prev_regime     = self._state.regime
        regime_changed  = detect_regime_change(prev_regime, regime)
        if regime_changed or regime == prev_regime:
            duration = 1 if regime_changed else (self._state.duration_bars + 1)
        else:
            duration = self._state.duration_bars + 1

        # 6. 稳定性
        temp_seq = self._history.get_sequence(limit=self._stab_window)
        temp_seq_enum = []
        for s in temp_seq:
            try:
                temp_seq_enum.append(MarketRegime(s))
            except ValueError:
                pass
        stability = compute_regime_stability(temp_seq_enum, self._stab_window)

        # 7. 策略推荐
        recommendation = _REGIME_TO_STRATEGY.get(
            regime, StrategyRecommendation.NEUTRAL
        )

        # 8. 构建新状态
        new_state = MarketRegimeState(
            regime           = regime,
            confidence       = confidence,
            confidence_score = conf_score,
            recommendation   = recommendation,
            regime_score     = conf_score,
            factor_scores    = scores,
            vol_score        = vol_s,
            trend_score      = trend_s,
            trend_sign       = trend_sign,
            liq_score        = liq_s,
            corr_score       = corr_s,
            prev_regime      = prev_regime,
            regime_changed   = regime_changed,
            duration_bars    = duration,
            stability        = stability,
            detected_at      = datetime.now(),
        )

        # 9. 更新历史
        self._history.append(new_state)
        self._state = new_state

        self._log(
            f"[RegimeEngine] bar={self._bar_count}"
            f"  regime={regime.value}"
            f"  conf={conf_score:.3f}"
            f"  changed={regime_changed}"
        )

        return new_state

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_state(self) -> MarketRegimeState:
        return self._state

    def get_history(self) -> RegimeHistory:
        return self._history

    def get_factor_scores(self) -> dict[str, float]:
        return dict(self._state.factor_scores)

    def summary(self) -> dict:
        return build_regime_summary(
            regime     = self._state.regime,
            confidence = self._state.confidence_score,
            scores     = self._state.factor_scores,
            stability  = self._state.stability,
            duration   = self._state.duration_bars,
        ) | {"phase": 2}

    # ------------------------------------------------------------------ #
    #  参数更新
    # ------------------------------------------------------------------ #

    def update_params(
        self,
        min_confidence:     float | None = None,
        high_vol_threshold: float | None = None,
        low_liq_threshold:  float | None = None,
        stability_window:   int   | None = None,
    ) -> None:
        if min_confidence     is not None: self._min_confidence = min_confidence
        if high_vol_threshold is not None: self._high_vol_thr   = high_vol_threshold
        if low_liq_threshold  is not None: self._low_liq_thr    = low_liq_threshold
        if stability_window   is not None: self._stab_window     = stability_window
