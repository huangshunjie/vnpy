"""
temporal_intelligence_ai/engine/cycle_engine.py

Market Cycle Engine — 市场周期识别引擎（Phase 2）。

职责：
  - 消费历史市场数据（通过 MarketLoader）
  - 计算 Cycle = f(volatility, trend, liquidity, correlation)
  - 识别五种周期阶段：expansion / peak / contraction / trough / transition
  - 维护周期历史序列
  - 输出 CycleState，由主引擎派发 EVENT_CYCLE_DETECTED

严格禁止：价格预测、交易信号生成、任何前瞻偏差
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from vnpy.trader.constant import Interval, Exchange

from ..constant import CyclePhase, RegimeType
from ..model.cycle_model import CycleMetrics, CycleState, CycleHistory
from ..datasource.market_loader import MarketLoader, MarketSeries
from ..utils.cycle_utils import (
    annualized_volatility,
    trend_strength,
    momentum_score,
    max_drawdown,
    market_breadth,
    cross_asset_correlation,
    identify_cycle_phase,
    classify_regime,
    rolling_returns,
)


class CycleEngine:
    """
    Market Cycle Engine.

    调用流程：
      1. configure()   — 配置目标品种与参数
      2. analyze()     — 触发一次完整周期分析
      3. get_state()   — 获取最新 CycleState
      4. get_history() — 获取完整历史序列
    """

    def __init__(self) -> None:
        self._loader:  MarketLoader    = MarketLoader()
        self._history: CycleHistory    = CycleHistory(max_size=500)
        self._current: Optional[CycleState] = None

        # 配置参数（由 configure() 设置）
        self._symbols:     List[tuple[str, Exchange]] = []
        self._interval:    Interval  = Interval.DAILY
        self._lookback:    int       = 120      # 回看天数
        self._vol_window:  int       = 20       # 波动率计算窗口
        self._trend_fast:  int       = 10       # 趋势快线
        self._trend_slow:  int       = 30       # 趋势慢线
        self._mom_window:  int       = 20       # 动量窗口
        self._dd_window:   int       = 60       # 回撤窗口

    # ── configuration ────────────────────────────────────────────────

    def configure(
        self,
        symbols:    List[tuple[str, Exchange]],
        interval:   Interval  = Interval.DAILY,
        lookback:   int       = 120,
        vol_window: int       = 20,
        trend_fast: int       = 10,
        trend_slow: int       = 30,
        mom_window: int       = 20,
        dd_window:  int       = 60,
    ) -> None:
        """设置分析品种列表与计算参数。"""
        self._symbols    = symbols
        self._interval   = interval
        self._lookback   = lookback
        self._vol_window = vol_window
        self._trend_fast = trend_fast
        self._trend_slow = trend_slow
        self._mom_window = mom_window
        self._dd_window  = dd_window

    # ── core analysis ────────────────────────────────────────────────

    def analyze(self, as_of: Optional[datetime] = None) -> Optional[CycleState]:
        """
        执行一次完整市场周期分析。

        Args:
            as_of: 分析截止时间，None 表示当前时刻（用于历史回测时传入指定时间）

        Returns:
            CycleState 或 None（数据不足时）
        """
        if not self._symbols:
            return None

        end_dt   = as_of if as_of else datetime.now()
        start_dt = end_dt - timedelta(days=self._lookback + 30)

        series_map = self._loader.load_multi(
            symbols=self._symbols,
            interval=self._interval,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        if not series_map:
            return None

        metrics = self._compute_metrics(series_map)
        if metrics is None:
            return None

        phase, confidence = identify_cycle_phase(
            volatility = metrics.volatility,
            trend      = metrics.trend_strength,
            momentum   = metrics.momentum,
            drawdown   = metrics.drawdown,
            breadth    = metrics.breadth,
        )

        regime = classify_regime(
            volatility = metrics.volatility,
            trend      = metrics.trend_strength,
        )

        prev = self._current
        is_transitioning = (
            prev is not None and prev.phase != phase
            and phase != CyclePhase.UNKNOWN
        )

        phase_duration = 1
        if prev is not None and prev.phase == phase:
            phase_duration = prev.phase_duration + 1

        state = CycleState(
            timestamp       = end_dt,
            phase           = phase,
            regime          = regime,
            confidence      = confidence,
            metrics         = metrics,
            phase_duration  = phase_duration,
            prev_phase      = prev.phase if prev else CyclePhase.UNKNOWN,
            is_transitioning = is_transitioning,
        )

        self._current = state
        self._history.append(state)
        return state

    # ── metrics computation ──────────────────────────────────────────

    def _compute_metrics(
        self, series_map: dict[str, MarketSeries]
    ) -> Optional[CycleMetrics]:
        """
        从多品种数据中聚合计算 CycleMetrics。

        多品种时取均值，单品种时直接计算。
        """
        all_closes:    List[List[float]] = []
        all_returns:   List[float]       = []
        volatilities:  List[float]       = []
        trends:        List[float]       = []
        momenta:       List[float]       = []
        drawdowns:     List[float]       = []

        for series in series_map.values():
            closes = series.close_prices
            if len(closes) < self._trend_slow + 1:
                continue

            vol  = annualized_volatility(closes, self._vol_window)
            trd  = trend_strength(closes, self._trend_fast, self._trend_slow)
            mom  = momentum_score(closes, self._mom_window)
            dd   = max_drawdown(closes, self._dd_window)
            rets = rolling_returns(closes, 1)
            if rets:
                all_returns.append(rets[-1])

            volatilities.append(vol)
            trends.append(trd)
            momenta.append(mom)
            drawdowns.append(dd)
            all_closes.append(closes)

        if not volatilities:
            return None

        def avg(lst: List[float]) -> float:
            return sum(lst) / len(lst) if lst else 0.0

        breadth = market_breadth(all_returns)

        corr = 0.0
        if len(all_closes) >= 2:
            pairs = 0
            corr_sum = 0.0
            for i in range(len(all_closes)):
                for j in range(i + 1, len(all_closes)):
                    corr_sum += cross_asset_correlation(
                        all_closes[i], all_closes[j])
                    pairs += 1
            corr = corr_sum / pairs if pairs > 0 else 0.0

        return CycleMetrics(
            volatility      = avg(volatilities),
            trend_strength  = avg(trends),
            liquidity_score = 0.0,   # Phase 2 暂用占位，Phase 4 接入流动性数据
            correlation     = corr,
            momentum        = avg(momenta),
            breadth         = breadth,
            drawdown        = avg(drawdowns),
        )

    # ── accessors ────────────────────────────────────────────────────

    def get_state(self) -> Optional[CycleState]:
        """返回最新周期状态快照。"""
        return self._current

    def get_history(self) -> CycleHistory:
        """返回完整周期历史序列。"""
        return self._history

    def get_summary(self) -> dict:
        """供主引擎摘要查询使用。"""
        if self._current is None:
            return {
                "phase":      CyclePhase.UNKNOWN.value,
                "regime":     RegimeType.UNKNOWN.value,
                "confidence": 0.0,
                "duration":   0,
                "volatility": 0.0,
                "trend":      0.0,
            }
        m = self._current.metrics
        return {
            "phase":      self._current.phase.value,
            "regime":     self._current.regime.value,
            "confidence": self._current.confidence,
            "duration":   self._current.phase_duration,
            "volatility": round(m.volatility, 4),
            "trend":      round(m.trend_strength, 4),
        }
