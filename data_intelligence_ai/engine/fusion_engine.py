"""
data_intelligence_ai/engine/fusion_engine.py  (Phase 4)

FusionEngine — 数据融合引擎。

职责：
  - 接收来自各子系统的 FusionInput
  - 按 symbol 汇聚输入
  - 执行 4 种融合模式：weighted_average / latest_wins / consensus / regime_aware
  - 维护每个 symbol 的最新 FusedState
  - 维护融合历史与状态快照
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import FusionMode, DataType, SystemStatus
from ..model.fusion_model import (
    FusionInput, FusedState, FusionRecord, FusionState)
from ..utils.fusion_utils import (
    fuse,
    make_market_input, make_alpha_input, make_portfolio_input,
    make_execution_input, make_risk_input, make_regime_input,
)


class FusionEngine:
    """数据融合引擎（Phase 4 完整实现）。"""

    def __init__(
        self,
        default_mode:    FusionMode = FusionMode.WEIGHTED_AVERAGE,
        log_fn:          Callable | None = None,
    ) -> None:
        self._log         = log_fn or (lambda m: None)
        self._status      = SystemStatus.IDLE
        self._mode        = default_mode

        # 每个 symbol 的待融合输入缓冲
        self._input_buffer: dict[str, list[FusionInput]] = {}
        # 最新融合结果：{symbol: FusedState}
        self._latest: dict[str, FusedState] = {}
        # 融合记录历史
        self._records: list[FusionRecord] = []
        # regime_prob 缓存（供 REGIME_AWARE 模式使用）
        self._regime_probs: dict[str, float] = {}

    def init(self)  -> None: self._log("[FusionEngine] init()")
    def start(self) -> None:
        self._status = SystemStatus.FUSING
        self._log("[FusionEngine] start()")

    def stop(self)  -> None:
        self._status = SystemStatus.STOPPED
        self._log("[FusionEngine] stop()")

    # ── input ingestion ───────────────────────────────────────────────
    def add_input(self, inp: FusionInput) -> None:
        """向指定 symbol 的缓冲区添加一条融合输入。"""
        self._input_buffer.setdefault(inp.symbol, []).append(inp)

    def set_regime_prob(self, symbol: str, bull_prob: float) -> None:
        """更新 regime 概率（供 REGIME_AWARE 模式使用）。"""
        self._regime_probs[symbol] = max(0.0, min(1.0, bull_prob))

    # ── convenience input builders ────────────────────────────────────
    def add_market(self, symbol: str, price_ret: float,
                    vol: float, quality: float = 1.0) -> None:
        self.add_input(make_market_input(symbol, price_ret, vol, quality))

    def add_alpha(self, symbol: str, ic_score: float,
                   quality: float = 1.0) -> None:
        self.add_input(make_alpha_input(symbol, ic_score, quality))

    def add_portfolio(self, symbol: str, weight_pct: float,
                       target_pct: float, quality: float = 1.0) -> None:
        self.add_input(make_portfolio_input(symbol, weight_pct, target_pct, quality))

    def add_execution(self, symbol: str, fill_rate: float,
                       slippage_bps: float, quality: float = 1.0) -> None:
        self.add_input(make_execution_input(symbol, fill_rate, slippage_bps, quality))

    def add_risk(self, symbol: str, utilization: float,
                  quality: float = 1.0) -> None:
        self.add_input(make_risk_input(symbol, utilization, quality))

    def add_regime(self, symbol: str, bull_prob: float,
                    quality: float = 1.0) -> None:
        self.set_regime_prob(symbol, bull_prob)
        self.add_input(make_regime_input(symbol, bull_prob, quality))

    # ── fusion execution ──────────────────────────────────────────────
    def fuse_symbol(
        self,
        symbol: str,
        mode:   FusionMode | None = None,
        clear_buffer: bool = True,
    ) -> FusedState:
        """
        对指定 symbol 执行一次融合，消费缓冲区输入。
        clear_buffer=True 时融合后清空输入缓冲。
        """
        inputs = self._input_buffer.get(symbol, [])
        eff_mode    = mode or self._mode
        regime_prob = self._regime_probs.get(symbol, 0.5)

        state = fuse(inputs, eff_mode, symbol, regime_prob)
        self._latest[symbol] = state

        rec = FusionRecord(
            record_id = f"REC_{uuid.uuid4().hex[:8].upper()}",
            symbol    = symbol,
            mode      = eff_mode,
            inputs    = list(inputs),
            result    = state,
        )
        self._records.append(rec)

        if clear_buffer:
            self._input_buffer[symbol] = []

        self._log(
            f"[FusionEngine] fuse {symbol}: mode={eff_mode.value} "
            f"n_inputs={len(inputs)} unified={state.unified_score:.4f} "
            f"conf={state.confidence:.4f}")
        return state

    def fuse_all(
        self,
        mode:         FusionMode | None = None,
        clear_buffer: bool = True,
    ) -> dict[str, FusedState]:
        """对所有有输入的 symbol 执行融合。"""
        results: dict[str, FusedState] = {}
        for symbol in list(self._input_buffer.keys()):
            if self._input_buffer[symbol]:
                results[symbol] = self.fuse_symbol(symbol, mode, clear_buffer)
        return results

    # ── query ─────────────────────────────────────────────────────────
    def get_latest(self, symbol: str) -> FusedState | None:
        return self._latest.get(symbol)

    def get_all_latest(self) -> dict[str, FusedState]:
        return dict(self._latest)

    def get_records(self, n: int = 50) -> list[FusionRecord]:
        return self._records[-n:]

    def get_pending_symbols(self) -> list[str]:
        """返回缓冲区中有待融合输入的 symbol 列表。"""
        return [s for s, inputs in self._input_buffer.items() if inputs]

    def get_buffer_size(self, symbol: str) -> int:
        return len(self._input_buffer.get(symbol, []))

    # ── state ─────────────────────────────────────────────────────────
    def get_state(self) -> FusionState:
        n = len(self._records)
        if not n:
            return FusionState(mode=self._mode)

        latest_vals = list(self._latest.values())
        avg_u   = sum(s.unified_score for s in latest_vals) / len(latest_vals)
        avg_c   = sum(s.confidence    for s in latest_vals) / len(latest_vals)

        source_counts: dict[str, int] = {}
        for rec in self._records[-100:]:
            for inp in rec.inputs:
                k = inp.source.value
                source_counts[k] = source_counts.get(k, 0) + 1

        sym_scores = {s: round(v.unified_score, 4)
                      for s, v in self._latest.items()}

        return FusionState(
            total_fusions   = n,
            active_symbols  = len(self._latest),
            avg_unified     = round(avg_u, 4),
            avg_confidence  = round(avg_c, 4),
            mode            = self._mode,
            source_counts   = source_counts,
            symbol_scores   = sym_scores,
            updated_at      = datetime.now(),
        )

    def summary(self) -> dict:
        s = self.get_state()
        return {
            "phase":          4,
            "status":         self._status.value,
            "total_fusions":  s.total_fusions,
            "active_symbols": s.active_symbols,
            "avg_unified":    s.avg_unified,
            "avg_confidence": s.avg_confidence,
            "mode":           s.mode.value,
        }
