"""
cross_market_ai/engine.py

Cross-Market Intelligence System.
Phase 2: StructureMapper
Phase 3: AlphaTransferEngine + RegimeAlignmentEngine
Phase 4: UniversalityEngine
Phase 5: ValidationEngine
"""
from __future__ import annotations
from datetime import datetime
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine
from .constant import APP_NAME, APP_VERSION, EngineStatus
from .event import (
    EVENT_CROSS_MARKET_MAPPING_COMPLETED, EVENT_ALPHA_TRANSFERRED,
    EVENT_REGIME_ALIGNED, EVENT_UNIVERSALITY_SCORED,
    EVENT_VALIDATION_COMPLETED, EVENT_CROSS_MARKET_LOG,
)
from .engine.structure_mapper import StructureMapper
from .engine.alpha_transfer_engine import AlphaTransferEngine
from .engine.regime_alignment_engine import RegimeAlignmentEngine
from .engine.universality_engine import UniversalityEngine
from .engine.validation_engine import ValidationEngine
from .utils.cross_market_utils import (
    compute_transfer_feasibility, rank_markets_by_similarity,
)


class CrossMarketEngine(BaseEngine):
    """
    Cross-Market Intelligence System.
    Phase 2: map_structure
    Phase 3: transfer_alpha / align_regime
    Phase 4: evaluate_universality
    Phase 5: validate_cross_market
    """
    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._version     = APP_VERSION
        self._status      = EngineStatus.IDLE
        self._started_at: datetime | None = None
        self._log_records: list[str] = []
        self._structure_mapper = StructureMapper(log_fn=self._log, main_engine=main_engine)
        self._alpha_transfer   = AlphaTransferEngine(log_fn=self._log, main_engine=main_engine)
        self._regime_alignment = RegimeAlignmentEngine(log_fn=self._log, main_engine=main_engine)
        self._universality     = UniversalityEngine(log_fn=self._log, main_engine=main_engine)
        self._validation       = ValidationEngine(log_fn=self._log, main_engine=main_engine)
        self._log(f"[{APP_NAME}] v{self._version} engine created (Phase 5)")

    # lifecycle

    def init(self) -> None:
        for e in [self._structure_mapper, self._alpha_transfer,
                  self._regime_alignment, self._universality, self._validation]:
            e.init()
        self._log(f"[{APP_NAME}] init() Phase 5 ready")

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = EngineStatus.RUNNING
        for e in [self._structure_mapper, self._alpha_transfer,
                  self._regime_alignment, self._universality, self._validation]:
            e.start()
        self._log(f"[{APP_NAME}] start()")

    def stop(self) -> None:
        for e in [self._structure_mapper, self._alpha_transfer,
                  self._regime_alignment, self._universality, self._validation]:
            e.stop()
        self._status = EngineStatus.STOPPED
        self._log(f"[{APP_NAME}] stop()")

    def close(self) -> None:
        self.stop()

    # Phase 2

    def map_structure(self, market_id: str, other_markets: list[str] | None = None,
                      force_refresh: bool = False, params: dict | None = None) -> dict:
        try:
            vector = self._structure_mapper.compute(
                market_id=market_id, other_markets=other_markets,
                force_refresh=force_refresh, params=params)
            self._sync_caches()
            result = {"status": "ok", "phase": 2, "market_id": market_id,
                      "vector": vector.to_dict(),
                      "state":  self._structure_mapper.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 2, "market_id": market_id,
                      "error": str(e), "vector": None}
            self._log(f"map_structure error: {e}", "ERROR")
        self.dispatch_event(EVENT_CROSS_MARKET_MAPPING_COMPLETED, result)
        return result

    def map_all_structures(self, markets: list[str] | None = None,
                           force_refresh: bool = False) -> dict:
        try:
            vectors = self._structure_mapper.compute_all(
                markets=markets, force_refresh=force_refresh)
            self._sync_caches()
            results = {mid: v.to_dict() for mid, v in vectors.items()}
            result  = {"status": "ok", "phase": 2, "count": len(results),
                       "vectors": results,
                       "state":   self._structure_mapper.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 2, "error": str(e)}
            self._log(f"map_all_structures error: {e}", "ERROR")
        self.dispatch_event(EVENT_CROSS_MARKET_MAPPING_COMPLETED, result)
        return result

    def get_structure_similarity(self, market_a: str, market_b: str) -> dict:
        va = self._structure_mapper.get_cached(market_a) or \
             self._structure_mapper.compute(market_a)
        vb = self._structure_mapper.get_cached(market_b) or \
             self._structure_mapper.compute(market_b)
        return {"status": "ok", "phase": 2, **compute_transfer_feasibility(va, vb)}

    def rank_markets_by_similarity(self, source_market: str,
                                   candidate_markets: list[str] | None = None) -> dict:
        src  = self._structure_mapper.get_cached(source_market) or \
               self._structure_mapper.compute(source_market)
        tgts = [m for m in (candidate_markets or
                self._structure_mapper._loader.list_available_markets())
                if m != source_market]
        cvecs = [self._structure_mapper.get_cached(m) or
                 self._structure_mapper.compute(m) for m in tgts]
        ranked = rank_markets_by_similarity(src, cvecs)
        return {"status": "ok", "phase": 2, "source_market": source_market,
                "ranked": [{"market_id": m, "similarity": s} for m, s in ranked]}

    def get_structure_state(self) -> dict:
        return self._structure_mapper.get_state().to_dict()

    def get_cached_structures(self) -> dict:
        return {mid: v.to_dict()
                for mid, v in self._structure_mapper.get_all_cached().items()}

    # Phase 3: Alpha Transfer

    def transfer_alpha(self, alpha_id: str, market_src: str, market_dst: str,
                       force_refresh: bool = False, params: dict | None = None) -> dict:
        try:
            record = self._alpha_transfer.transfer(
                alpha_id=alpha_id, market_src=market_src, market_dst=market_dst,
                force_refresh=force_refresh, params=params)
            self._sync_caches()
            result = {"status": "ok", "phase": 3, "record": record.to_dict(),
                      "state": self._alpha_transfer.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 3, "alpha_id": alpha_id,
                      "market_src": market_src, "market_dst": market_dst, "error": str(e)}
            self._log(f"transfer_alpha error: {e}", "ERROR")
        self.dispatch_event(EVENT_ALPHA_TRANSFERRED, result)
        return result

    def transfer_alpha_batch(self, alpha_id: str, market_src: str,
                             targets: list[str] | None = None) -> dict:
        dst = targets or [m for m in
            self._structure_mapper._loader.list_available_markets()
            if m != market_src]
        try:
            records = self._alpha_transfer.transfer_batch(alpha_id, market_src, dst)
            self._sync_caches()
            result = {"status": "ok", "phase": 3, "alpha_id": alpha_id,
                      "count": len(records), "records": [r.to_dict() for r in records],
                      "state": self._alpha_transfer.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 3, "error": str(e)}
            self._log(f"transfer_alpha_batch error: {e}", "ERROR")
        self.dispatch_event(EVENT_ALPHA_TRANSFERRED, result)
        return result

    def get_transfer_state(self) -> dict:
        return self._alpha_transfer.get_state().to_dict()

    def get_cached_transfers(self) -> dict:
        return {k: v.to_dict() for k, v in self._alpha_transfer.get_all_cached().items()}

    # Phase 3: Regime Alignment

    def align_regime(self, market_a: str, market_b: str,
                     force_refresh: bool = False, params: dict | None = None) -> dict:
        try:
            record = self._regime_alignment.align(
                market_a=market_a, market_b=market_b,
                force_refresh=force_refresh, params=params)
            self._sync_caches()
            result = {"status": "ok", "phase": 3, "record": record.to_dict(),
                      "state": self._regime_alignment.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 3,
                      "market_a": market_a, "market_b": market_b, "error": str(e)}
            self._log(f"align_regime error: {e}", "ERROR")
        self.dispatch_event(EVENT_REGIME_ALIGNED, result)
        return result

    def align_regime_batch(self, pairs: list[tuple[str, str]],
                           force_refresh: bool = False) -> dict:
        try:
            records = self._regime_alignment.align_batch(pairs, force_refresh=force_refresh)
            self._sync_caches()
            result = {"status": "ok", "phase": 3, "count": len(records),
                      "records": [r.to_dict() for r in records],
                      "state":   self._regime_alignment.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 3, "error": str(e)}
            self._log(f"align_regime_batch error: {e}", "ERROR")
        self.dispatch_event(EVENT_REGIME_ALIGNED, result)
        return result

    def get_regime_state(self) -> dict:
        return self._regime_alignment.get_state().to_dict()

    def get_cached_alignments(self) -> dict:
        return {k: v.to_dict() for k, v in self._regime_alignment.get_all_cached().items()}

    # Phase 4: Universality Scoring

    def evaluate_universality(self, alpha_id: str, markets: list[str] | None = None,
                               force_refresh: bool = False,
                               params: dict | None = None) -> dict:
        try:
            self._sync_caches()
            record = self._universality.score(
                alpha_id=alpha_id, markets=markets,
                force_refresh=force_refresh, params=params)
            result = {"status": "ok", "phase": 4, "record": record.to_dict(),
                      "state": self._universality.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 4, "alpha_id": alpha_id, "error": str(e)}
            self._log(f"evaluate_universality error: {e}", "ERROR")
        self.dispatch_event(EVENT_UNIVERSALITY_SCORED, result)
        return result

    def evaluate_universality_batch(self, alpha_ids: list[str],
                                    markets: list[str] | None = None,
                                    force_refresh: bool = False) -> dict:
        try:
            self._sync_caches()
            records = self._universality.score_batch(
                alpha_ids=alpha_ids, markets=markets, force_refresh=force_refresh)
            result = {"status": "ok", "phase": 4, "count": len(records),
                      "records": [r.to_dict() for r in records],
                      "state":   self._universality.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 4, "error": str(e)}
            self._log(f"evaluate_universality_batch error: {e}", "ERROR")
        self.dispatch_event(EVENT_UNIVERSALITY_SCORED, result)
        return result

    def get_universality_leaderboard(self, limit: int = 20) -> dict:
        return {"status": "ok", "phase": 4,
                "leaderboard": self._universality.get_leaderboard(limit)}

    def get_universality_state(self) -> dict:
        return self._universality.get_state().to_dict()

    def get_cached_universality(self) -> dict:
        return {k: v.to_dict() for k, v in self._universality.get_all_cached().items()}

    # Phase 5: Cross-Market Validation

    def validate_cross_market(self, alpha_id: str, market_train: str, market_test: str,
                               force_refresh: bool = False,
                               params: dict | None = None) -> dict:
        try:
            self._sync_caches()
            record = self._validation.validate(
                alpha_id=alpha_id, market_train=market_train, market_test=market_test,
                force_refresh=force_refresh, params=params)
            result = {"status": "ok", "phase": 5, "record": record.to_dict(),
                      "state": self._validation.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 5, "alpha_id": alpha_id, "error": str(e)}
            self._log(f"validate_cross_market error: {e}", "ERROR")
        self.dispatch_event(EVENT_VALIDATION_COMPLETED, result)
        return result

    def validate_batch(self, alpha_id: str, market_train: str,
                       test_markets: list[str] | None = None,
                       force_refresh: bool = False) -> dict:
        tests = test_markets or [
            m for m in self._structure_mapper._loader.list_available_markets()
            if m != market_train]
        try:
            self._sync_caches()
            records = self._validation.validate_batch(
                alpha_id, market_train, tests, force_refresh=force_refresh)
            result = {"status": "ok", "phase": 5, "alpha_id": alpha_id,
                      "count": len(records), "records": [r.to_dict() for r in records],
                      "state": self._validation.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 5, "error": str(e)}
            self._log(f"validate_batch error: {e}", "ERROR")
        self.dispatch_event(EVENT_VALIDATION_COMPLETED, result)
        return result

    def validate_matrix(self, alpha_id: str, markets: list[str] | None = None,
                        force_refresh: bool = False) -> dict:
        mks = markets or list(self._structure_mapper.get_all_cached().keys())
        try:
            self._sync_caches()
            records = self._validation.validate_matrix(
                alpha_id, mks, force_refresh=force_refresh)
            matrix  = self._validation.get_summary_matrix(alpha_id, mks)
            result  = {"status": "ok", "phase": 5, "alpha_id": alpha_id,
                       "count": len(records), "records": [r.to_dict() for r in records],
                       "matrix": matrix,
                       "state":  self._validation.get_state().to_dict()}
        except Exception as e:
            result = {"status": "error", "phase": 5, "error": str(e)}
            self._log(f"validate_matrix error: {e}", "ERROR")
        self.dispatch_event(EVENT_VALIDATION_COMPLETED, result)
        return result

    def get_validation_state(self) -> dict:
        return self._validation.get_state().to_dict()

    def get_cached_validations(self) -> dict:
        return {k: v.to_dict() for k, v in self._validation.get_all_cached().items()}

    # event

    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    # query

    def get_status(self) -> EngineStatus:
        return self._status

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    def get_summary(self) -> dict:
        ss = self._structure_mapper.get_state().to_dict()
        ts = self._alpha_transfer.get_state().to_dict()
        rs = self._regime_alignment.get_state().to_dict()
        us = self._universality.get_state().to_dict()
        vs = self._validation.get_state().to_dict()
        return {
            "app":               APP_NAME,
            "version":           self._version,
            "phase":             5,
            "status":            self._status.value,
            "uptime":            self._uptime(),
            "markets_mapped":    ss.get("total_mapped",       0),
            "mapped_list":       ss.get("markets",            []),
            "last_market":       ss.get("last_market_id",     ""),
            "total_transfers":   ts.get("total_transfers",    0),
            "transfer_success":  ts.get("successful",         0),
            "transfer_rejected": ts.get("rejected",           0),
            "avg_transfer_coeff":ts.get("avg_coefficient",    0.0),
            "total_alignments":  rs.get("total_alignments",   0),
            "align_success":     rs.get("successful",         0),
            "avg_alignment":     rs.get("avg_alignment",      0.0),
            "total_scored":      us.get("total_scored",       0),
            "avg_univ_score":    us.get("avg_score",          0.0),
            "top_alpha":         us.get("top_alpha",          ""),
            "universal_count":   us.get("universal_count",    0),
            "portable_count":    us.get("portable_count",     0),
            "total_validations": vs.get("total_validations",  0),
            "validation_passed": vs.get("passed",             0),
            "validation_failed": vs.get("failed",             0),
            "avg_decay_rate":    vs.get("avg_decay_rate",     0.0),
        }

    # internal

    def _sync_caches(self) -> None:
        sc = self._structure_mapper.get_all_cached()
        tc = self._alpha_transfer.get_all_cached()
        ac = self._regime_alignment.get_all_cached()
        uc = self._universality.get_all_cached()
        self._alpha_transfer.inject_structure_cache(sc)
        self._universality.inject_caches(
            structure_cache=sc, transfer_cache=tc, alignment_cache=ac)
        self._validation.inject_caches(
            structure_cache=sc, transfer_cache=tc,
            alignment_cache=ac, universality_cache=uc)

    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def _log(self, msg: str, level: str = "INFO") -> None:
        ts   = str(datetime.now())[:19]
        line = f"{ts}  [{level}]  {msg}"
        self._log_records.append(line)
        if len(self._log_records) > 5000:
            self._log_records = self._log_records[-5000:]
        self.dispatch_event(EVENT_CROSS_MARKET_LOG, {"line": line, "level": level})
        try:
            self.write_log(msg)
        except Exception:
            pass
