"""
market_reality_ai/engine/walkforward_engine.py

Phase 4: Walk-Forward Reality Engine — complete implementation.

Rolling window reality gap analysis:
  For each window:
    1. Simulate "ideal" backtest return (what strategy expected)
    2. Apply execution reality (slippage + impact) to get realized return
    3. reality_gap_bps = (backtest - realized) * 10000
    4. Classify regime for the window

Aggregate:
  avg_reality_gap, worst_gap, best_gap, regime_breakdown
  reality_gap_score = max(0, 100 - abs(avg_gap_bps))
"""
from __future__ import annotations
import math
import random
from datetime import datetime, timedelta

from ..constant import SimulationStatus
from ..model.stress_model import WalkForwardWindow, WalkForwardState
from ..utils.stress_utils import (
    new_wf_id, reality_gap_bps, reality_gap_score, regime_label_from_vol)


class WalkForwardEngine:
    """
    Walk-Forward Reality Engine — Phase 4 完整实现。

    每次 run() 调用生成 n_windows 个滚动窗口，每个窗口:
      1. 随机生成该窗口的市场参数 (vol, regime, n_trades)
      2. 计算 backtest_return = ideal return (no friction)
      3. 计算 realized_return = backtest minus execution costs
      4. reality_gap_bps = (backtest - realized) * 10000
      5. 按 regime 分组统计

    WalkForwardState 聚合所有窗口。
    """

    def __init__(self, log_fn=None) -> None:
        self._log    = log_fn or (lambda m: None)
        self._status = SimulationStatus.IDLE
        self._state  = WalkForwardState()

        # baseline execution parameters
        self._avg_slippage_bps: float = 5.0
        self._avg_impact_bps:   float = 10.0
        self._avg_fill_rate:    float = 0.95
        self._base_vol:         float = 0.02

    # ── lifecycle ─────────────────────────────────────────────────────
    def init(self) -> None:
        self._status = SimulationStatus.IDLE
        self._state  = WalkForwardState()
        self._log("[WalkForwardEngine] initialised")

    def start(self) -> None:
        self._status = SimulationStatus.RUNNING
        self._log("[WalkForwardEngine] started")

    def stop(self) -> None:
        self._status = SimulationStatus.IDLE
        self._log("[WalkForwardEngine] stopped")

    def configure(
        self,
        avg_slippage_bps: float = 5.0,
        avg_impact_bps:   float = 10.0,
        avg_fill_rate:    float = 0.95,
        base_vol:         float = 0.02,
    ) -> None:
        self._avg_slippage_bps = avg_slippage_bps
        self._avg_impact_bps   = avg_impact_bps
        self._avg_fill_rate    = avg_fill_rate
        self._base_vol         = base_vol

    # ── main entry ────────────────────────────────────────────────────
    def run(
        self,
        window_days: int = 60,
        step_days:   int = 10,
        n_windows:   int = 12,
        seed:        int = 42,
    ) -> WalkForwardState:
        """
        Run walk-forward analysis over n_windows rolling periods.

        Parameters
        ----------
        window_days : days per rolling window
        step_days   : step between windows
        n_windows   : total number of windows to simulate
        seed        : random seed for reproducibility

        Returns WalkForwardState with all windows populated.
        """
        rng = random.Random(seed)
        self._state  = WalkForwardState(status=SimulationStatus.RUNNING)
        windows      = []

        start_date = datetime(2023, 1, 1)

        for i in range(n_windows):
            w_start = start_date + timedelta(days=i * step_days)
            w_end   = w_start + timedelta(days=window_days)

            # ── simulate window market environment ───────────────
            # volatility varies by window (regime clustering)
            vol_cycle = 1.0 + 0.5 * math.sin(i * math.pi / 4)
            window_vol = self._base_vol * vol_cycle * rng.uniform(0.8, 1.2)
            regime     = regime_label_from_vol(window_vol)

            # number of trades in this window
            n_trades = int(rng.uniform(20, 80))

            # ── backtest return (ideal, no execution costs) ──────
            # annualised return ~ N(12%, vol) prorated to window
            annual_ret   = rng.gauss(0.12, window_vol * 10)
            bt_return    = annual_ret * (window_days / 252.0)

            # ── execution costs ──────────────────────────────────
            # slippage drag: vol-amplified
            slip_amp  = 1.0 + max(0.0, (window_vol - self._base_vol) / self._base_vol)
            slip_drag = (self._avg_slippage_bps * slip_amp
                         * n_trades / 252.0 / 10000.0)

            # impact drag: larger in stressed regimes
            regime_mult = {"low_vol": 0.5, "normal": 1.0,
                           "stressed": 2.5, "crisis": 5.0}.get(regime, 1.0)
            impact_drag = (self._avg_impact_bps * regime_mult
                           * n_trades / 252.0 / 10000.0)

            # fill rate penalty: missed trades
            fill_pen  = max(0.0, (1.0 - self._avg_fill_rate) * abs(bt_return))

            # total execution drag
            total_drag   = slip_drag + impact_drag + fill_pen
            realized_ret = bt_return - total_drag

            # ── reality gap ──────────────────────────────────────
            gap_bps = reality_gap_bps(bt_return, realized_ret)

            win = WalkForwardWindow(
                window_id        = new_wf_id(),
                start_date       = str(w_start.date()),
                end_date         = str(w_end.date()),
                window_days      = window_days,
                backtest_return  = round(bt_return,   6),
                realized_return  = round(realized_ret, 6),
                reality_gap_bps  = round(gap_bps,      4),
                slippage_drag_bps= round(slip_drag * 10000, 4),
                impact_drag_bps  = round(impact_drag * 10000, 4),
                regime           = regime,
                n_trades         = n_trades,
            )
            windows.append(win)
            self._log(
                f"[WFEngine] window {i+1}/{n_windows}  "
                f"{win.start_date}→{win.end_date}  "
                f"regime={regime}  "
                f"bt={bt_return:.2%}  "
                f"realized={realized_ret:.2%}  "
                f"gap={gap_bps:.1f}bps")

        self._state.windows = windows
        self._state.update_from_windows()
        self._state.status  = SimulationStatus.COMPLETED

        self._log(
            f"[WFEngine] complete  n={n_windows}  "
            f"avg_gap={self._state.avg_reality_gap:.1f}bps  "
            f"score={self._state.reality_gap_score:.1f}  "
            f"regimes={list(self._state.regime_breakdown.keys())}")
        return self._state

    # ── query ──────────────────────────────────────────────────────────
    def get_state(self) -> WalkForwardState:
        return self._state

    def get_statistics(self) -> dict:
        return self._state.to_dict()

    def get_windows(self, limit: int = 100) -> list[WalkForwardWindow]:
        return self._state.windows[-limit:]

    def get_latest_window(self) -> WalkForwardWindow | None:
        if not self._state.windows:
            return None
        return self._state.windows[-1]

    @property
    def status(self) -> SimulationStatus:
        return self._status
