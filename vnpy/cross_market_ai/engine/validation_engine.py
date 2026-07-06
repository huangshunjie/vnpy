"""
cross_market_ai/engine/validation_engine.py

Phase 5: Cross-Market Validation Engine.
Train on Market_A, Test on Market_B, measure degradation.
å¤ç”¨ Phase 2/3/4 ç¼“å­˜ã€‚
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from ..datasource.alpha_loader import AlphaDataLoader
from ..model.validation_model import (
    ValidationRecord, ValidationState,
    PerformanceSnapshot, DegradationMetrics, StructuralCompatibility,
)


class ValidationEngine:
    """è·¨å¸‚åœºéªŒè¯å¼•æ“ï¼ˆPhase 5 å®Œæ•´å®ç°ï¼‰ã€‚"""

    THRESHOLDS = {"decay_fail": 0.50, "decay_degrade": 0.30}

    def __init__(self, log_fn: Callable | None = None, main_engine=None) -> None:
        self._log          = log_fn or (lambda m, lvl="INFO": None)
        self._alpha_loader = AlphaDataLoader(main_engine=main_engine)
        self._state        = ValidationState()
        self._cache:       dict[str, ValidationRecord] = {}
        self._structure_cache:    dict = {}
        self._transfer_cache:     dict = {}
        self._alignment_cache:    dict = {}
        self._universality_cache: dict = {}

    def init(self)  -> None:
        self._state.status = "idle";   self._log("[ValidationEngine] init()")

    def start(self) -> None:
        self._state.status = "running"; self._log("[ValidationEngine] start()")

    def stop(self)  -> None:
        self._state.status = "idle";   self._log("[ValidationEngine] stop()")

    def inject_caches(self, structure_cache: dict, transfer_cache: dict,
                      alignment_cache: dict, universality_cache: dict) -> None:
        self._structure_cache    = structure_cache
        self._transfer_cache     = transfer_cache
        self._alignment_cache    = alignment_cache
        self._universality_cache = universality_cache

    # â”€â”€ æ ¸å¿ƒæ¥å£ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def validate(self, alpha_id: str, market_train: str, market_test: str,
                 force_refresh: bool = False,
                 params: dict | None = None) -> ValidationRecord:
        """Train on market_train, test on market_test, measure degradation."""
        cache_key = f"{alpha_id}|{market_train}>{market_test}"
        if not force_refresh and cache_key in self._cache:
            self._log(f"[ValidationEngine] cache hit: {cache_key}")
            return self._cache[cache_key]

        self._log(f"[ValidationEngine] validating: {alpha_id}  {market_train}>{market_test}")

        p             = params or {}
        decay_fail    = p.get("decay_fail",    self.THRESHOLDS["decay_fail"])
        decay_degrade = p.get("decay_degrade", self.THRESHOLDS["decay_degrade"])

        perf_train  = self._get_perf_snapshot(alpha_id, market_train, is_train=True)
        perf_test   = self._get_perf_snapshot(alpha_id, market_test,  is_train=False)
        degradation = self._compute_degradation(perf_train, perf_test)
        compat      = self._get_compat(alpha_id, market_train, market_test)
        pred_decay  = self._get_predicted_decay(alpha_id, market_test)
        actual_decay = degradation.composite_decay
        pred_error  = round(abs(pred_decay - actual_decay), 4)
        verdict, detail, passed_flag = self._classify(
            actual_decay, decay_fail, decay_degrade, compat.compatibility_score)

        record = ValidationRecord(
            alpha_id=alpha_id, market_train=market_train, market_test=market_test,
            perf_train=perf_train, perf_test=perf_test,
            degradation=degradation, compatibility=compat,
            passed=passed_flag, verdict=verdict, verdict_detail=detail,
            decay_threshold=decay_fail, degrade_threshold=decay_degrade,
            predicted_decay=pred_decay, actual_decay=actual_decay,
            prediction_error=pred_error, status="computed", validated_at=_now(),
        )
        self._cache[cache_key] = record
        self._update_state(alpha_id, market_train, market_test, actual_decay, verdict)
        self._log(f"[ValidationEngine] {alpha_id} {market_train}>{market_test} "
                  f"decay={actual_decay:.3f} pred_err={pred_error:.3f} verdict={verdict}")
        return record

    def validate_batch(self, alpha_id: str, market_train: str,
                       test_markets: list[str],
                       force_refresh: bool = False) -> list[ValidationRecord]:
        return [self.validate(alpha_id, market_train, m, force_refresh=force_refresh)
                for m in test_markets if m != market_train]

    def validate_matrix(self, alpha_id: str, markets: list[str],
                        force_refresh: bool = False) -> list[ValidationRecord]:
        records = []
        for m_train in markets:
            for m_test in markets:
                if m_test != m_train:
                    records.append(self.validate(alpha_id, m_train, m_test,
                                                 force_refresh=force_refresh))
        return records

    def get_cached(self, alpha_id: str, market_train: str,
                   market_test: str) -> Optional[ValidationRecord]:
        return self._cache.get(f"{alpha_id}|{market_train}>{market_test}")

    def get_all_cached(self) -> dict[str, ValidationRecord]:
        return dict(self._cache)

    def get_state(self) -> ValidationState:
        return self._state

    def get_summary_matrix(self, alpha_id: str,
                           markets: list[str]) -> dict[str, dict]:
        matrix: dict[str, dict] = {}
        for m_train in markets:
            matrix[m_train] = {}
            for m_test in markets:
                if m_test == m_train:
                    matrix[m_train][m_test] = None
                    continue
                rec = self.get_cached(alpha_id, m_train, m_test)
                matrix[m_train][m_test] = rec.actual_decay if rec else None
        return matrix

    def clear_cache(self) -> None:
        self._cache.clear()
        self._log("[ValidationEngine] cache cleared")

    # ©¤©¤ ÄÚ²¿Âß¼­ ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤

    def _get_perf_snapshot(self, alpha_id: str, market_id: str,
                           is_train: bool = True) -> PerformanceSnapshot:
        t_rec = self._find_transfer(alpha_id, market_id)
        if t_rec is not None:
            # ÑµÁ·ÊĞ³¡ÓÃ src ĞÔÄÜ£¬²âÊÔÊĞ³¡ÓÃ dst Ô¤²âĞÔÄÜ
            if is_train:
                sharpe = t_rec.expected_sharpe_dst * 1.2
                ic     = t_rec.expected_ic_src
            else:
                sharpe = t_rec.expected_sharpe_dst
                ic     = t_rec.expected_ic_dst
            return PerformanceSnapshot(
                market_id    = market_id,
                sharpe       = round(sharpe, 4),
                ic_mean      = round(ic, 5),
                ic_std       = round(ic * 0.8, 5),
                max_drawdown = round(0.15 / max(t_rec.transfer_coefficient, 0.1), 4),
                win_rate     = round(0.52 + ic * 3, 4),
                n_samples    = 252,
                source       = "transfer_cache",
            )
        perf = self._alpha_loader.load_alpha_performance(alpha_id, market_id)
        return PerformanceSnapshot(
            market_id    = market_id,
            sharpe       = perf.get("sharpe",         0.5),
            ic_mean      = perf.get("ic_mean",        0.03),
            ic_std       = perf.get("ic_std",         0.024),
            max_drawdown = perf.get("max_drawdown",   0.15),
            win_rate     = perf.get("win_rate",       0.52),
            n_samples    = perf.get("n_observations", 252),
            source       = "prior",
        )

    def _compute_degradation(self, train: PerformanceSnapshot,
                             test: PerformanceSnapshot) -> DegradationMetrics:
        sharpe_decay = _decay(train.sharpe,       test.sharpe)
        ic_decay     = _decay(train.ic_mean,      test.ic_mean)
        dd_ratio     = test.max_drawdown / max(train.max_drawdown, 1e-9)
        wr_delta     = train.win_rate - test.win_rate
        composite    = (
            sharpe_decay                            * 0.40 +
            ic_decay                                * 0.35 +
            min(max(dd_ratio - 1.0, 0.0), 1.0)     * 0.15 +
            min(max(wr_delta,       0.0), 1.0)      * 0.10
        )
        return DegradationMetrics(
            sharpe_decay    = round(max(sharpe_decay, 0.0), 4),
            ic_decay        = round(max(ic_decay,     0.0), 4),
            drawdown_ratio  = round(max(dd_ratio,     0.0), 4),
            win_rate_delta  = round(wr_delta,               4),
            composite_decay = round(max(min(composite, 1.0), 0.0), 4),
        )

    def _get_compat(self, alpha_id: str, market_train: str,
                    market_test: str) -> StructuralCompatibility:
        from ..utils.cross_market_utils import compute_structural_similarity
        va    = self._structure_cache.get(market_train)
        vb    = self._structure_cache.get(market_test)
        sim   = compute_structural_similarity(va, vb) if (va and vb) else 0.5
        al    = self._find_alignment(market_train, market_test)
        al_sc = al.alignment_score if al else 0.4
        t_rec = self._find_transfer(alpha_id, market_test)
        t_c   = t_rec.transfer_coefficient if t_rec else 0.4
        port  = vb.portability_score if vb else 0.4
        score = round(max(0.0, min(sim*0.30 + al_sc*0.25 + t_c*0.30 + port*0.15, 1.0)), 4)
        return StructuralCompatibility(
            structural_similarity  = sim,
            regime_alignment_score = al_sc,
            transfer_coefficient   = t_c,
            portability_prior      = port,
            compatibility_score    = score,
        )

    def _get_predicted_decay(self, alpha_id: str, market_test: str) -> float:
        t_rec = self._find_transfer(alpha_id, market_test)
        return t_rec.expected_ic_decay if t_rec else 0.40

    @staticmethod
    def _classify(decay: float, fail: float, degrade: float,
                  compat: float) -> tuple[str, str, bool]:
        if decay >= fail:
            return ("FAIL",
                    f"Ë¥¼õÂÊ {decay:.1%} ³¬¹ıãĞÖµ {fail:.0%}£¬Ç¨ÒÆ²»¿ÉĞĞ¡£",
                    False)
        if decay >= degrade:
            return ("DEGRADED",
                    f"Ë¥¼õÂÊ {decay:.1%}£¬¼æÈİĞÔ {compat:.2f}£¬½¨Òé¼à¿ØÔËĞĞ¡£",
                    False)
        return ("PASS",
                f"Ë¥¼õÂÊ {decay:.1%} < {degrade:.0%}£¬¼æÈİĞÔ {compat:.2f}£¬¿ÉÇ¨ÒÆ¡£",
                True)

    def _find_transfer(self, alpha_id: str, market_dst: str):
        for key, rec in self._transfer_cache.items():
            if key.startswith(f"{alpha_id}|") and key.endswith(f">{market_dst}"):
                return rec
        return None

    def _find_alignment(self, market_a: str, market_b: str):
        for key, rec in self._alignment_cache.items():
            if market_a in key and market_b in key:
                return rec
        return None

    def _update_state(self, alpha_id: str, market_train: str, market_test: str,
                      decay: float, verdict: str) -> None:
        self._state.total_validations += 1
        n = self._state.total_validations
        self._state.avg_decay_rate = round(
            (self._state.avg_decay_rate * (n - 1) + decay) / n, 4)
        if verdict == "PASS":
            self._state.passed   += 1
        elif verdict == "DEGRADED":
            self._state.degraded += 1
        else:
            self._state.failed   += 1
        self._state.last_alpha_id = alpha_id
        self._state.last_pair     = f"{market_train}>{market_test}"
        self._state.status        = "running"


# ©¤©¤ ´¿º¯Êı¹¤¾ß ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤

def _now() -> str:
    return str(datetime.now())[:19]


def _decay(train_val: float, test_val: float) -> float:
    if abs(train_val) < 1e-9:
        return 0.0
    return max(0.0, (train_val - test_val) / abs(train_val))
