"""
data_intelligence_ai/engine/__init__.py  (Phase 5 Final)

GlobalDataEngine — 完整五阶段数据智能系统顶层引擎。
"""
from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from ..constant import APP_NAME, SystemStatus, FeatureType, QualityStatus, FusionMode, DataType
from ..event import (
    EVENT_DATA_INGESTED, EVENT_FEATURE_UPDATED,
    EVENT_DATA_QUALITY_CHECKED, EVENT_DATA_FUSED, EVENT_DATA_UPDATED,
)
from .data_engine     import DataEngine
from .feature_engine  import FeatureEngine
from .quality_engine  import QualityEngine
from .fusion_engine   import FusionEngine
from .realtime_engine import RealtimeEngine
from ..model.feature_model import FeatureRecord, FeatureState
from ..model.quality_model import QualityReport, DriftReport, QualityState
from ..model.fusion_model  import FusionInput, FusedState, FusionRecord, FusionState


class GlobalDataEngine(BaseEngine):
    """数据智能系统 — VeighNa 顶层引擎（Phase 5 Final）。"""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._status:      SystemStatus    = SystemStatus.IDLE
        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []

        self._data_engine     = DataEngine(log_fn=self._log)
        self._feature_engine  = FeatureEngine(log_fn=self._log)
        self._quality_engine  = QualityEngine(log_fn=self._log)
        self._fusion_engine   = FusionEngine(log_fn=self._log)
        self._realtime_engine = RealtimeEngine(
            self._feature_engine, self._quality_engine,
            self._fusion_engine, log_fn=self._log)
        self._log(f"[{APP_NAME}] GlobalDataEngine created (Phase 5)")

    def init(self) -> None:
        self._log(f"[{APP_NAME}] init()")
        for e in [self._data_engine, self._feature_engine,
                  self._quality_engine, self._fusion_engine,
                  self._realtime_engine]:
            e.init()
        self._status = SystemStatus.IDLE

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SystemStatus.STREAMING
        for e in [self._data_engine, self._feature_engine,
                  self._quality_engine, self._fusion_engine,
                  self._realtime_engine]:
            e.start()
        self.dispatch_event(EVENT_DATA_UPDATED,
                            {"status": self._status.value, "phase": 5})

    def stop(self) -> None:
        self._status = SystemStatus.STOPPED
        for e in [self._data_engine, self._feature_engine,
                  self._quality_engine, self._fusion_engine,
                  self._realtime_engine]:
            e.stop()
        self._log(f"[{APP_NAME}] stop()")

    def close(self) -> None:
        self.stop()

    # ── Phase 5: real-time interface ─────────────────────────────────
    def stream_ingest(self, data_type, symbol, payload):
        evt = self._realtime_engine.ingest(data_type, symbol, payload)
        self.dispatch_event(EVENT_DATA_UPDATED, evt.to_dict())
        return evt

    def stream_ingest_batch(self, events):
        results = self._realtime_engine.ingest_batch(events)
        self.dispatch_event(EVENT_DATA_UPDATED, {"n_events": len(results)})
        return results

    def stream_market(self, symbol, price, volume=0.0):
        self._realtime_engine.ingest(
            DataType.MARKET, symbol, {"price": price, "volume": volume})

    def stream_alpha(self, symbol, feature_name, value, ic=None):
        self._realtime_engine.ingest(
            DataType.ALPHA, symbol,
            {"feature_name": feature_name, "value": value,
             "ic": ic if ic is not None else value})

    def stream_risk(self, symbol, utilization):
        self._realtime_engine.ingest(
            DataType.RISK, symbol, {"utilization": utilization})

    def stream_regime(self, symbol, bull_prob):
        self._realtime_engine.ingest(
            DataType.REGIME, symbol, {"bull_prob": bull_prob})

    def stream_execution(self, symbol, fill_rate, slippage_bps):
        self._realtime_engine.ingest(
            DataType.EXECUTION, symbol,
            {"fill_rate": fill_rate, "slippage_bps": slippage_bps})

    def stream_portfolio(self, symbol, weight_pct, target_pct):
        self._realtime_engine.ingest(
            DataType.PORTFOLIO, symbol,
            {"weight_pct": weight_pct, "target_pct": target_pct})

    def register_on_feature(self, cb): self._realtime_engine.on_feature(cb)
    def register_on_quality(self, cb): self._realtime_engine.on_quality(cb)
    def register_on_fused(self,   cb): self._realtime_engine.on_fused(cb)

    def get_stream_buffer(self, n=50):
        return self._realtime_engine.get_stream_buffer(n)

    def get_rt_reports(self, n=50):
        return self._realtime_engine.get_rt_reports(n)

    def get_rt_fused(self, n=50):
        return self._realtime_engine.get_rt_fused(n)

    def get_latest_fused(self, symbol):
        return self._realtime_engine.get_latest_fused(symbol)

    def get_realtime_summary(self):
        return self._realtime_engine.summary()

    # ── Phase 4 interface ────────────────────────────────────────────
    def add_fusion_input(self, inp):       self._fusion_engine.add_input(inp)
    def add_market_fusion(self, sym, pr, vol, q=1.0):  self._fusion_engine.add_market(sym, pr, vol, q)
    def add_alpha_fusion(self, sym, ic, q=1.0):        self._fusion_engine.add_alpha(sym, ic, q)
    def add_portfolio_fusion(self, sym, wp, tp, q=1.0):self._fusion_engine.add_portfolio(sym, wp, tp, q)
    def add_execution_fusion(self, sym, fr, sp, q=1.0):self._fusion_engine.add_execution(sym, fr, sp, q)
    def add_risk_fusion(self, sym, util, q=1.0):       self._fusion_engine.add_risk(sym, util, q)
    def add_regime_fusion(self, sym, bp, q=1.0):       self._fusion_engine.add_regime(sym, bp, q)

    def fuse_symbol(self, symbol, mode=None):
        state = self._fusion_engine.fuse_symbol(symbol, mode)
        self.dispatch_event(EVENT_DATA_FUSED, state.to_dict())
        return state

    def fuse_all(self, mode=None):
        results = self._fusion_engine.fuse_all(mode)
        if results: self.dispatch_event(EVENT_DATA_FUSED, {"n_fused": len(results)})
        return results

    def get_fused_state(self, sym):   return self._fusion_engine.get_latest(sym)
    def get_all_fused_states(self):   return self._fusion_engine.get_all_latest()
    def get_fusion_records(self, n=50): return self._fusion_engine.get_records(n)
    def get_fusion_state(self):       return self._fusion_engine.get_state()
    def set_fusion_mode(self, mode):  self._fusion_engine._mode = mode

    # ── Phase 3 interface ────────────────────────────────────────────
    def check_feature_quality(self, record, related=None, rules=None):
        report = self._quality_engine.check_feature(record, related, rules)
        self.dispatch_event(EVENT_DATA_QUALITY_CHECKED, report.to_dict())
        return report

    def check_features_quality(self, records):
        reports = self._quality_engine.check_many(records)
        self.dispatch_event(EVENT_DATA_QUALITY_CHECKED, {"n_checked": len(reports)})
        return reports

    def check_drift(self, fn, sym, curr, hist=None):
        r = self._quality_engine.check_drift(fn, sym, curr, hist)
        self.dispatch_event(EVENT_DATA_QUALITY_CHECKED, r.to_dict())
        return r

    def check_drift_from_feature(self, rec): return self._quality_engine.check_drift_from_feature(rec)
    def get_quality_reports(self, n=50, status=None): return self._quality_engine.get_reports(n, status)
    def get_drift_reports(self, n=20, drifted_only=False): return self._quality_engine.get_drift_reports(n, drifted_only)
    def get_feature_quality(self, fn, sym): return self._quality_engine.get_feature_quality(fn, sym)
    def get_quality_blockers(self):         return self._quality_engine.get_blockers()
    def get_quality_state(self):            return self._quality_engine.get_state()

    # ── Phase 2 interface ────────────────────────────────────────────
    def write_feature(self, record):
        ok, reason = self._feature_engine.write(record)
        if ok: self.dispatch_event(EVENT_FEATURE_UPDATED, record.to_dict())
        return ok, reason

    def write_features(self, records):
        result = self._feature_engine.write_many(records)
        if result["written"] > 0:
            self.dispatch_event(EVENT_FEATURE_UPDATED, {"written": result["written"]})
        return result

    def ingest_market_features(self, sym, prices, vols, version=1):
        r = self._feature_engine.ingest_market(sym, prices, vols, version)
        self.dispatch_event(EVENT_FEATURE_UPDATED, {"symbol": sym, "written": r["written"]})
        return r

    def ingest_alpha_feature(self, fn, sym, val, src="", ver=1):
        ok, reason = self._feature_engine.ingest_alpha(fn, sym, val, src, ver)
        if ok: self.dispatch_event(EVENT_FEATURE_UPDATED, {"feature_name": fn})
        return ok, reason

    def ingest_regime_feature(self, fn, prob, sym="_market", ver=1):
        ok, reason = self._feature_engine.ingest_regime(fn, prob, sym, "", ver)
        if ok: self.dispatch_event(EVENT_FEATURE_UPDATED, {"feature_name": fn})
        return ok, reason

    def ingest_execution_feature(self, fn, val, sym="", ver=1):
        ok, reason = self._feature_engine.ingest_execution(fn, val, sym, "", ver)
        if ok: self.dispatch_event(EVENT_FEATURE_UPDATED, {"feature_name": fn})
        return ok, reason

    def get_feature(self, fn, sym):       return self._feature_engine.get(fn, sym)
    def get_features_by_type(self, ft):   return self._feature_engine.get_by_type(ft)
    def get_features_by_symbol(self, sym):return self._feature_engine.get_by_symbol(sym)
    def get_all_features(self):           return self._feature_engine.get_all()
    def list_feature_names(self):         return self._feature_engine.list_feature_names()
    def list_symbols(self):               return self._feature_engine.list_symbols()
    def get_feature_lineage(self, fn):    return self._feature_engine.get_lineage(fn)
    def get_version_history(self, fn, sym, n=10): return self._feature_engine.get_version_history(fn, sym, n)
    def get_feature_state(self):          return self._feature_engine.get_state()

    # ── Phase 1 interface ────────────────────────────────────────────
    def ingest_data(self, raw):
        result = self._data_engine.ingest_data(raw)
        self.dispatch_event(EVENT_DATA_INGESTED, raw)
        return result

    def update_feature_store(self, feature):
        result = self._data_engine.update_feature_store(feature)
        self.dispatch_event(EVENT_FEATURE_UPDATED, feature)
        return result

    # ── events / summary ─────────────────────────────────────────────
    def dispatch_event(self, event_type, data=None):
        self.event_engine.put(Event(event_type, data or {}))

    def get_status(self):   return self._status
    def get_logs(self, limit=200): return self._log_records[-limit:]

    def get_summary(self) -> dict:
        return {
            "app":      APP_NAME, "phase": 5,
            "status":   self._status.value,
            "uptime":   self._uptime(),
            "engine":   self._data_engine.summary(),
            "feature":  self._feature_engine.summary(),
            "quality":  self._quality_engine.summary(),
            "fusion":   self._fusion_engine.summary(),
            "realtime": self._realtime_engine.summary(),
        }

    def _uptime(self):
        if self._started_at is None: return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def _log(self, msg):
        ts = str(datetime.now())[:19]
        self._log_records.append(f"{ts}  {msg}")
        try:    self.write_log(msg)
        except: pass


__all__ = [
    "GlobalDataEngine", "DataEngine",
    "FeatureEngine", "QualityEngine",
    "FusionEngine", "RealtimeEngine",
]
