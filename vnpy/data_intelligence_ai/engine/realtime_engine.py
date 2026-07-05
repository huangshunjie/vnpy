"""
data_intelligence_ai/engine/realtime_engine.py  (Phase 5)

RealtimeEngine — 实时更新引擎。

闭环：Data → Feature → Quality → Fusion → System Update

职责：
  - 事件驱动的增量数据接入
  - 增量特征更新（只更新变化的特征）
  - 流式质量检查（实时结果）
  - 触发融合更新
  - 维护实时系统状态与更新速率统计
"""
from __future__ import annotations
from collections import deque
from datetime import datetime
from typing import Callable
import uuid

from ..constant import DataType, FusionMode, SystemStatus
from ..model.feature_model import FeatureRecord
from ..model.quality_model import QualityReport
from ..model.fusion_model  import FusedState
from .feature_engine import FeatureEngine
from .quality_engine import QualityEngine
from .fusion_engine  import FusionEngine
from ..utils.feature_utils import features_from_market, compute_alpha_feature
from ..utils.fusion_utils  import (
    make_market_input, make_alpha_input,
    make_risk_input, make_regime_input, make_execution_input,
)


class StreamEvent:
    """单条流式数据事件（原始数据包）。"""
    __slots__ = ("event_id", "data_type", "symbol", "payload", "received_at")

    def __init__(self, data_type: DataType, symbol: str, payload: dict) -> None:
        self.event_id   = f"SE_{uuid.uuid4().hex[:8].upper()}"
        self.data_type  = data_type
        self.symbol     = symbol
        self.payload    = payload
        self.received_at= datetime.now()

    def to_dict(self) -> dict:
        return {
            "event_id":    self.event_id,
            "data_type":   self.data_type.value,
            "symbol":      self.symbol,
            "received_at": str(self.received_at)[:19],
        }


class RealtimeEngine:
    """实时更新引擎（Phase 5 完整实现）。"""

    def __init__(
        self,
        feature_engine:  FeatureEngine,
        quality_engine:  QualityEngine,
        fusion_engine:   FusionEngine,
        stream_buffer_size: int  = 500,
        auto_fuse:          bool = True,
        log_fn: Callable | None  = None,
    ) -> None:
        self._fe   = feature_engine
        self._qe   = quality_engine
        self._fuse = fusion_engine
        self._log  = log_fn or (lambda m: None)
        self._auto_fuse = auto_fuse
        self._status    = SystemStatus.IDLE

        # 流式事件缓冲区（环形队列）
        self._stream_buffer: deque[StreamEvent] = deque(maxlen=stream_buffer_size)

        # 每个 symbol 的最近价格/成交量缓冲（用于增量计算）
        self._price_buf:  dict[str, list[float]] = {}
        self._volume_buf: dict[str, list[float]] = {}
        self._buf_maxlen  = 60   # 保留最近 60 根 K 线

        # 实时质量报告缓存（最近 200 条）
        self._rt_reports: deque[QualityReport] = deque(maxlen=200)
        # 实时融合结果缓存（最近 200 条）
        self._rt_fused:   deque[FusedState]    = deque(maxlen=200)

        # 统计
        self._n_events:   int = 0
        self._n_features: int = 0
        self._n_fusions:  int = 0
        self._n_issues:   int = 0
        self._started_at: datetime | None = None

        # 回调钩子（外部注册，供 UI 刷新使用）
        self._on_feature_cb:  Callable | None = None
        self._on_quality_cb:  Callable | None = None
        self._on_fused_cb:    Callable | None = None

    def init(self)  -> None: self._log("[RealtimeEngine] init()")
    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SystemStatus.STREAMING
        self._log("[RealtimeEngine] start()")

    def stop(self)  -> None:
        self._status = SystemStatus.STOPPED
        self._log("[RealtimeEngine] stop()")

    # ── callback registration ─────────────────────────────────────────
    def on_feature(self, cb: Callable) -> None:
        self._on_feature_cb = cb

    def on_quality(self, cb: Callable) -> None:
        self._on_quality_cb = cb

    def on_fused(self, cb: Callable) -> None:
        self._on_fused_cb = cb

    # ── streaming ingestion ───────────────────────────────────────────
    def ingest(self, data_type: DataType, symbol: str,
                payload: dict) -> StreamEvent:
        """
        接收单条流式数据，执行完整闭环处理：
        Data → Feature → Quality → (Fusion)
        """
        evt = StreamEvent(data_type, symbol, payload)
        self._stream_buffer.append(evt)
        self._n_events += 1

        if data_type == DataType.MARKET:
            self._process_market(symbol, payload)
        elif data_type == DataType.ALPHA:
            self._process_alpha(symbol, payload)
        elif data_type == DataType.RISK:
            self._process_risk(symbol, payload)
        elif data_type == DataType.REGIME:
            self._process_regime(symbol, payload)
        elif data_type == DataType.EXECUTION:
            self._process_execution(symbol, payload)
        elif data_type == DataType.PORTFOLIO:
            self._process_portfolio(symbol, payload)

        return evt

    def ingest_batch(self, events: list[tuple[DataType, str, dict]]
                      ) -> list[StreamEvent]:
        """批量流式接入。"""
        return [self.ingest(dt, sym, payload) for dt, sym, payload in events]

    # ── incremental processors ────────────────────────────────────────
    def _process_market(self, symbol: str, payload: dict) -> None:
        price  = float(payload.get("price",  payload.get("close", 0.0)))
        volume = float(payload.get("volume", 0.0))
        if price <= 0:
            return

        # 更新价格/成交量缓冲
        prices  = self._price_buf.setdefault(symbol, [])
        volumes = self._volume_buf.setdefault(symbol, [])
        prices.append(price)
        volumes.append(volume)
        if len(prices)  > self._buf_maxlen: prices.pop(0)
        if len(volumes) > self._buf_maxlen: volumes.pop(0)

        # 增量特征计算（需要至少2个价格点）
        if len(prices) < 2:
            return
        feats = features_from_market(symbol, prices, volumes)
        res = self._fe.write_many(feats)
        self._n_features += res["written"]

        # 流式质量检查
        for feat in feats:
            report = self._qe.check_feature(feat)
            self._rt_reports.append(report)
            if report.n_issues > 0:
                self._n_issues += report.n_issues

        # 融合输入
        if len(prices) >= 2:
            ret = (prices[-1] - prices[-2]) / max(abs(prices[-2]), 1e-10)
            vol_arr = prices[-min(20, len(prices)):]
            import math
            mu   = sum(vol_arr) / len(vol_arr)
            vol  = math.sqrt(sum((p - mu)**2 for p in vol_arr) / len(vol_arr)) / max(mu, 1e-10)
            self._fuse.add_market(symbol, ret, max(vol, 1e-6))

        self._trigger_fusion(symbol)
        if self._on_feature_cb and feats:
            self._on_feature_cb(feats[-1])

    def _process_alpha(self, symbol: str, payload: dict) -> None:
        feat_name = payload.get("feature_name", "alpha_signal")
        value     = float(payload.get("value", payload.get("ic", 0.0)))
        feat      = compute_alpha_feature(value, feat_name, symbol)
        ok, _     = self._fe.write(feat)
        if ok:
            self._n_features += 1
        report = self._qe.check_feature(feat)
        self._rt_reports.append(report)

        ic = float(payload.get("ic", value))
        self._fuse.add_alpha(symbol, max(min(ic, 1.0), -1.0))
        self._trigger_fusion(symbol)
        if self._on_feature_cb:
            self._on_feature_cb(feat)

    def _process_risk(self, symbol: str, payload: dict) -> None:
        utilization = float(payload.get("utilization", payload.get("usage", 0.5)))
        self._fuse.add_risk(symbol, max(min(utilization, 1.0), 0.0))
        self._trigger_fusion(symbol)

    def _process_regime(self, symbol: str, payload: dict) -> None:
        bull_prob = float(payload.get("bull_prob", payload.get("prob", 0.5)))
        self._fuse.set_regime_prob(symbol, bull_prob)
        self._fuse.add_regime(symbol, bull_prob)
        self._trigger_fusion(symbol)

    def _process_execution(self, symbol: str, payload: dict) -> None:
        fill_rate    = float(payload.get("fill_rate",    0.95))
        slippage_bps = float(payload.get("slippage_bps", 5.0))
        self._fuse.add_execution(symbol, fill_rate, slippage_bps)
        self._trigger_fusion(symbol)

    def _process_portfolio(self, symbol: str, payload: dict) -> None:
        weight_pct = float(payload.get("weight_pct", payload.get("weight", 0.0)))
        target_pct = float(payload.get("target_pct", payload.get("target", weight_pct)))
        self._fuse.add_portfolio(symbol, weight_pct, target_pct)
        self._trigger_fusion(symbol)

    def _trigger_fusion(self, symbol: str) -> None:
        """当 auto_fuse 且缓冲区有输入时触发融合。"""
        if not self._auto_fuse:
            return
        if self._fuse.get_buffer_size(symbol) < 1:
            return
        try:
            state = self._fuse.fuse_symbol(symbol)
            self._rt_fused.append(state)
            self._n_fusions += 1
            if self._on_fused_cb:
                self._on_fused_cb(state)
        except Exception as e:
            self._log(f"[RealtimeEngine] fusion error {symbol}: {e}")

    # ── query ─────────────────────────────────────────────────────────
    def get_stream_buffer(self, n: int = 50) -> list[StreamEvent]:
        buf = list(self._stream_buffer)
        return buf[-n:]

    def get_rt_reports(self, n: int = 50) -> list[QualityReport]:
        reps = list(self._rt_reports)
        return reps[-n:]

    def get_rt_fused(self, n: int = 50) -> list[FusedState]:
        fused = list(self._rt_fused)
        return fused[-n:]

    def get_latest_fused(self, symbol: str) -> FusedState | None:
        for state in reversed(list(self._rt_fused)):
            if state.symbol == symbol:
                return state
        return None

    # ── state & stats ─────────────────────────────────────────────────
    def get_event_rate(self) -> float:
        """每分钟事件数。"""
        if self._started_at is None or self._n_events == 0:
            return 0.0
        elapsed = (datetime.now() - self._started_at).total_seconds() / 60.0
        return round(self._n_events / max(elapsed, 1/60), 2)

    def summary(self) -> dict:
        return {
            "phase":        5,
            "status":       self._status.value,
            "n_events":     self._n_events,
            "n_features":   self._n_features,
            "n_fusions":    self._n_fusions,
            "n_issues":     self._n_issues,
            "event_rate":   self.get_event_rate(),
            "buffer_size":  len(self._stream_buffer),
            "active_symbols": len(self._price_buf),
        }
