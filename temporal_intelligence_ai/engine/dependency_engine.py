"""
temporal_intelligence_ai/engine/dependency_engine.py

Time Dependency Engine — 时间依赖分析引擎（Phase 4）。

职责：
  - 分析多个信号序列之间的时间依赖结构
  - 识别短/中/长期时间维度的贡献度
  - 计算信号自相关与互相关矩阵
  - 输出 DependencyState，附带 EVENT_TEMPORAL_ANALYSIS_COMPLETED 派发

Signal(t) = f(Signal(t-1), Signal(t-5), Signal(t-n))

严格禁止：价格预测、交易信号生成、任何前瞻偏差
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..constant import SignalHorizon
from ..model.dependency_model import (
    AutoCorrResult,
    CrossCorrResult,
    DependencyHistory,
    DependencyMatrix,
    DependencyState,
    HorizonDecomposition,
)
from ..utils.dependency_utils import (
    compute_autocorr,
    compute_crosscorr,
    decompose_horizons,
    overall_memory_score,
)

_DEFAULT_MAX_LAG   = 30
_DEFAULT_CROSS_LAG = 20


class DependencyEngine:
    """
    Time Dependency Engine.

    调用流程：
      1. register_signal()   — 注册信号序列
      2. analyze()           — 触发完整时间依赖分析
      3. get_state()         — 获取最新 DependencyState
      4. get_history()       — 获取历史快照
    """

    def __init__(self) -> None:
        self._signals:  Dict[str, List[float]] = {}   # signal_id → 价格/收益率序列
        self._current:  Optional[DependencyState]  = None
        self._history:  DependencyHistory          = DependencyHistory()

        self._max_lag:   int = _DEFAULT_MAX_LAG
        self._cross_lag: int = _DEFAULT_CROSS_LAG

    # ── configuration ────────────────────────────────────────────────

    def configure(
        self,
        max_lag:   int = _DEFAULT_MAX_LAG,
        cross_lag: int = _DEFAULT_CROSS_LAG,
    ) -> None:
        """设置最大自相关滞后阶和互相关滞后阶。"""
        self._max_lag   = max_lag
        self._cross_lag = cross_lag

    # ── signal management ────────────────────────────────────────────

    def register_signal(self, signal_id: str, series: List[float]) -> None:
        """
        注册或更新一个信号序列。

        Args:
            signal_id: 唯一标识符
            series:    时间升序的数值序列（价格、收益率、因子值均可）
        """
        self._signals[signal_id] = list(series)

    def register_signals(self, signals: Dict[str, List[float]]) -> None:
        """批量注册信号序列。"""
        for sid, series in signals.items():
            self.register_signal(sid, series)

    def remove_signal(self, signal_id: str) -> None:
        self._signals.pop(signal_id, None)

    def clear_signals(self) -> None:
        self._signals.clear()

    # ── core analysis ────────────────────────────────────────────────

    def analyze(self) -> Optional[DependencyState]:
        """
        对所有已注册信号执行完整时间依赖分析。

        Returns:
            DependencyState 或 None（信号不足时）
        """
        if not self._signals:
            return None

        signal_ids = list(self._signals.keys())

        # 1. 自相关分析
        autocorr_results: Dict[str, AutoCorrResult] = {}
        for sid, series in self._signals.items():
            if len(series) < self._max_lag + 2:
                continue
            result = compute_autocorr(sid, series, self._max_lag)
            autocorr_results[sid] = result

        if not autocorr_results:
            return None

        # 2. 互相关分析（所有非重复信号对）
        crosscorr_results: List[CrossCorrResult] = []
        ids = list(self._signals.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a_id, b_id = ids[i], ids[j]
                sa = self._signals[a_id]
                sb = self._signals[b_id]
                min_len = min(len(sa), len(sb))
                if min_len < self._cross_lag + 4:
                    continue
                cc = compute_crosscorr(
                    a_id, sa[-min_len:],
                    b_id, sb[-min_len:],
                    self._cross_lag,
                )
                crosscorr_results.append(cc)

        # 3. 依赖矩阵
        dep_matrix = DependencyMatrix(signal_ids=signal_ids)
        for cc in crosscorr_results:
            dep_matrix.set(cc.signal_a, cc.signal_b, cc.dependency_strength)

        # 4. 时间维度分解（取所有信号分解结果的均值）
        horizon_decomp = self._aggregate_horizons(autocorr_results)

        # 5. 综合记忆强度
        memory = overall_memory_score(autocorr_results)

        state = DependencyState(
            timestamp         = datetime.now(),
            signal_ids        = signal_ids,
            autocorr_results  = autocorr_results,
            crosscorr_results = crosscorr_results,
            dep_matrix        = dep_matrix,
            horizon_decomp    = horizon_decomp,
            overall_memory    = memory,
        )

        self._current = state
        self._history.append(state)
        return state

    # ── helpers ──────────────────────────────────────────────────────

    def _aggregate_horizons(
        self,
        autocorr_results: Dict[str, AutoCorrResult],
    ) -> HorizonDecomposition:
        """对多信号的时间维度分解结果取均值，返回系统级分解。"""
        sw_list, mw_list, lw_list = [], [], []

        for sid, series in self._signals.items():
            if sid not in autocorr_results:
                continue
            decomp = decompose_horizons(series)
            sw_list.append(decomp.short_term_weight)
            mw_list.append(decomp.mid_term_weight)
            lw_list.append(decomp.long_term_weight)

        def avg(lst: List[float]) -> float:
            return sum(lst) / len(lst) if lst else 0.0

        sw = avg(sw_list)
        mw = avg(mw_list)
        lw = avg(lw_list)

        if sw >= mw and sw >= lw:
            dom = SignalHorizon.SHORT_TERM
        elif mw >= lw:
            dom = SignalHorizon.MID_TERM
        else:
            dom = SignalHorizon.LONG_TERM

        return HorizonDecomposition(
            short_term_weight = round(sw, 4),
            mid_term_weight   = round(mw, 4),
            long_term_weight  = round(lw, 4),
            dominant_horizon  = dom,
        )

    # ── accessors ────────────────────────────────────────────────────

    def get_state(self) -> Optional[DependencyState]:
        return self._current

    def get_history(self) -> DependencyHistory:
        return self._history

    def get_signal_ids(self) -> List[str]:
        return list(self._signals.keys())

    def get_summary(self) -> dict:
        if self._current is None:
            return {
                "signal_count":   0,
                "overall_memory": 0.0,
                "dominant_horizon": SignalHorizon.UNKNOWN.value
                    if hasattr(SignalHorizon, "UNKNOWN") else "unknown",
                "short_weight":   0.0,
                "mid_weight":     0.0,
                "long_weight":    0.0,
            }
        h = self._current.horizon_decomp
        return {
            "signal_count":     len(self._current.signal_ids),
            "overall_memory":   round(self._current.overall_memory, 4),
            "dominant_horizon": h.dominant_horizon.value,
            "short_weight":     h.short_term_weight,
            "mid_weight":       h.mid_term_weight,
            "long_weight":      h.long_term_weight,
        }
