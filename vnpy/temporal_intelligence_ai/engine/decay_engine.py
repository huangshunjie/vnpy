"""
temporal_intelligence_ai/engine/decay_engine.py

Alpha Decay Engine — Alpha 衰减分析引擎（Phase 3）。

职责：
  - 消费 AlphaLoader 提供的 Alpha 信号记录
  - 对每个活跃 Alpha 计算三种衰减模式
  - 维护每个 Alpha 的衰减历史与衰减曲线
  - 输出 DecayState，由主引擎派发 EVENT_ALPHA_DECAY_UPDATED

严格禁止：价格预测、交易信号生成、任何前瞻偏差
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..constant import CyclePhase, DecayMode, RegimeType
from ..model.decay_model import (
    DecayCurve, DecayHistory, DecayState, DecayMetrics,
)
from ..datasource.alpha_loader import AlphaLoader, AlphaRecord
from ..utils.decay_utils import (
    compute_decay_metrics,
    build_decay_curve,
    half_life_to_rate,
)

_MIN_STRENGTH  = 0.05   # 低于此值视为 Alpha 已到期
_DEFAULT_HL    = 20     # 默认半衰期（交易日）
_CURVE_HORIZON = 60     # 衰减曲线前瞻 bar 数（仅用于可视化，非预测）


class DecayEngine:
    """
    Alpha Decay Engine.

    调用流程：
      1. configure()         — 设置衰减模式与全局参数
      2. set_context()       — 注入当前 Regime / 周期阶段 / 波动率（来自 CycleEngine）
      3. compute(bar)        — 触发一次全量衰减计算
      4. get_states()        — 获取所有活跃 Alpha 的最新 DecayState
      5. get_curves()        — 获取所有衰减曲线（供 UI 绘图）
      6. get_history(alpha)  — 获取单个 Alpha 的历史序列
    """

    def __init__(self) -> None:
        self._loader:  AlphaLoader = AlphaLoader()

        # 每个 alpha_id → 最新 DecayState
        self._states:    Dict[str, DecayState]   = {}
        # 每个 alpha_id → 衰减曲线
        self._curves:    Dict[str, DecayCurve]   = {}
        # 每个 alpha_id → 历史序列
        self._histories: Dict[str, DecayHistory] = {}

        # 当前市场上下文（由 TemporalEngine 注入）
        self._regime:      RegimeType  = RegimeType.UNKNOWN
        self._phase:       CyclePhase  = CyclePhase.UNKNOWN
        self._current_vol: float       = 0.20
        self._current_bar: int         = 0

        # 配置参数
        self._mode:          DecayMode = DecayMode.EXPONENTIAL
        self._baseline_vol:  float     = 0.20
        self._vol_sensitivity: float   = 2.0
        self._min_threshold: float     = _MIN_STRENGTH
        self._curve_horizon: int       = _CURVE_HORIZON
        self._weights: tuple[float, float, float] = (0.40, 0.35, 0.25)

    # ── configuration ────────────────────────────────────────────────

    def configure(
        self,
        mode:            DecayMode                    = DecayMode.EXPONENTIAL,
        baseline_vol:    float                        = 0.20,
        vol_sensitivity: float                        = 2.0,
        min_threshold:   float                        = _MIN_STRENGTH,
        curve_horizon:   int                          = _CURVE_HORIZON,
        weights:         tuple[float, float, float]   = (0.40, 0.35, 0.25),
    ) -> None:
        """设置全局衰减参数。"""
        self._mode            = mode
        self._baseline_vol    = baseline_vol
        self._vol_sensitivity = vol_sensitivity
        self._min_threshold   = min_threshold
        self._curve_horizon   = curve_horizon
        self._weights         = weights

    def set_context(
        self,
        regime:      RegimeType,
        phase:       CyclePhase,
        current_vol: float,
        current_bar: int,
    ) -> None:
        """
        注入当前市场上下文。

        由 TemporalEngine 在每次 analyze_cycle() 完成后调用，
        确保衰减计算使用最新的 Regime / 周期 / 波动率。
        """
        self._regime      = regime
        self._phase       = phase
        self._current_vol = current_vol
        self._current_bar = current_bar

    # ── alpha management ─────────────────────────────────────────────

    def register_alpha(self, record: AlphaRecord) -> None:
        """注册一个 Alpha 信号到衰减引擎。"""
        self._loader.register(record)
        if record.alpha_id not in self._histories:
            self._histories[record.alpha_id] = DecayHistory(
                alpha_id=record.alpha_id)

    def register_alphas(self, records: List[AlphaRecord]) -> None:
        """批量注册 Alpha 信号。"""
        for r in records:
            self.register_alpha(r)

    # ── core computation ─────────────────────────────────────────────

    def compute(self, bar: Optional[int] = None) -> List[DecayState]:
        """
        对所有活跃 Alpha 执行一次完整衰减计算。

        Args:
            bar: 当前 bar 计数，None 时使用内部 _current_bar

        Returns:
            所有活跃 Alpha 的 DecayState 列表
        """
        current_bar = bar if bar is not None else self._current_bar
        active = self._loader.load_active(current_bar)
        results: List[DecayState] = []

        for record in active:
            state = self._compute_single(record, current_bar)
            self._states[record.alpha_id] = state

            hist = self._histories.setdefault(
                record.alpha_id,
                DecayHistory(alpha_id=record.alpha_id))
            hist.append(state)

            curve = self._build_curve(record, current_bar)
            self._curves[record.alpha_id] = curve

            results.append(state)

        self._prune_expired(current_bar)
        return results

    def _compute_single(
        self, record: AlphaRecord, current_bar: int
    ) -> DecayState:
        """计算单个 Alpha 的衰减状态。"""
        age = max(0, current_bar - record.created_bar)

        base_rate = record.base_decay_rate
        if base_rate <= 0:
            base_rate = half_life_to_rate(_DEFAULT_HL)

        metrics = compute_decay_metrics(
            age_bars        = age,
            base_rate       = base_rate,
            initial         = record.initial_strength,
            regime          = self._regime,
            phase           = self._phase,
            current_vol     = self._current_vol,
            baseline_vol    = self._baseline_vol,
            vol_sensitivity = self._vol_sensitivity,
            min_threshold   = self._min_threshold,
            weights         = self._weights,
        )

        is_expired = metrics.combined_strength <= self._min_threshold

        return DecayState(
            timestamp    = datetime.now(),
            alpha_id     = record.alpha_id,
            mode         = self._mode,
            metrics      = metrics,
            cycle_phase  = self._phase,
            regime       = self._regime,
            is_expired   = is_expired,
            expiry_bar   = metrics.age_bars + metrics.age_bars,  # 剩余存续估计
        )

    def _build_curve(
        self, record: AlphaRecord, current_bar: int
    ) -> DecayCurve:
        """为单个 Alpha 生成衰减曲线（供 UI 可视化）。"""
        age = max(0, current_bar - record.created_bar)
        base_rate = record.base_decay_rate
        if base_rate <= 0:
            base_rate = half_life_to_rate(_DEFAULT_HL)

        return build_decay_curve(
            alpha_id     = record.alpha_id,
            mode         = self._mode,
            current_age  = age,
            base_rate    = base_rate,
            initial      = record.initial_strength,
            horizon      = self._curve_horizon,
            regime       = self._regime,
            phase        = self._phase,
            current_vol  = self._current_vol,
            baseline_vol = self._baseline_vol,
            vol_sensitivity = self._vol_sensitivity,
        )

    def _prune_expired(self, current_bar: int) -> None:
        """移除已超过最大存续期（age > 500 bar）的记录。"""
        for rec in self._loader.load_all():
            age = current_bar - rec.created_bar
            if age > 500:
                self._loader.remove(rec.alpha_id)

    # ── accessors ────────────────────────────────────────────────────

    def get_states(self) -> Dict[str, DecayState]:
        return dict(self._states)

    def get_state(self, alpha_id: str) -> Optional[DecayState]:
        return self._states.get(alpha_id)

    def get_curves(self) -> Dict[str, DecayCurve]:
        return dict(self._curves)

    def get_curve(self, alpha_id: str) -> Optional[DecayCurve]:
        return self._curves.get(alpha_id)

    def get_history(self, alpha_id: str) -> Optional[DecayHistory]:
        return self._histories.get(alpha_id)

    def get_loader(self) -> AlphaLoader:
        return self._loader

    def get_summary(self) -> dict:
        """供主引擎摘要查询使用。"""
        states = list(self._states.values())
        if not states:
            return {
                "active_alphas": 0,
                "avg_strength":  0.0,
                "expired_count": 0,
                "min_strength":  0.0,
                "max_strength":  0.0,
            }
        strengths = [s.metrics.combined_strength for s in states]
        expired   = sum(1 for s in states if s.is_expired)
        return {
            "active_alphas": len(states),
            "avg_strength":  round(sum(strengths) / len(strengths), 4),
            "expired_count": expired,
            "min_strength":  round(min(strengths), 4),
            "max_strength":  round(max(strengths), 4),
        }
