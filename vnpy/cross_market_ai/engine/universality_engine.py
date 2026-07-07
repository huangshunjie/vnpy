"""
cross_market_ai/engine/universality_engine.py

Phase 4: Universality Scoring Engine — 四维普适性评分引擎。
Score ∈ [0,1]，Grade: UNIVERSAL / PORTABLE / LOCAL / FRAGILE
复用 Phase 2/3 缓存：structure_cache / transfer_cache / alignment_cache
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Callable, Optional

from ..datasource.alpha_loader import AlphaDataLoader
from ..model.universality_model import (
    UniversalityScoreRecord, UniversalityState,
    DimensionScore, MarketPerformanceSlice,
)
from ..utils.validation_utils import (
    compute_cross_market_stability,
    compute_regime_robustness,
    compute_structural_invariance,
    compute_execution_independence,
    compute_universality_score,
    classify_universality_grade,
)


class UniversalityEngine:
    """普适性评分引擎（Phase 4 完整实现）。"""

    def __init__(
        self,
        log_fn:     Callable | None = None,
        main_engine = None,
        weights:    dict[str, float] | None = None,
    ) -> None:
        self._log          = log_fn or (lambda m, lvl="INFO": None)
        self._alpha_loader = AlphaDataLoader(main_engine=main_engine)
        self._state        = UniversalityState()
        self._cache:       dict[str, UniversalityScoreRecord] = {}
        self._weights      = weights or {
            "cross_market_stability": 0.35,
            "regime_robustness":      0.25,
            "structural_invariance":  0.25,
            "execution_independence": 0.15,
        }
        self._structure_cache: dict = {}
        self._transfer_cache:  dict = {}
        self._alignment_cache: dict = {}

    def init(self) -> None:
        self._state.status = "idle"
        self._log("[UniversalityEngine] init()")

    def start(self) -> None:
        self._state.status = "running"
        self._log("[UniversalityEngine] start()")

    def stop(self) -> None:
        self._state.status = "idle"
        self._log("[UniversalityEngine] stop()")

    def inject_caches(self, structure_cache: dict,
                      transfer_cache: dict, alignment_cache: dict) -> None:
        """注入 Phase 2/3 缓存，实现跨阶段成果复用。"""
        self._structure_cache = structure_cache
        self._transfer_cache  = transfer_cache
        self._alignment_cache = alignment_cache

    # ── 核心：score() ─────────────────────────────────────────────────

    def score(self, alpha_id: str, markets: list[str] | None = None,
              force_refresh: bool = False, params: dict | None = None,
              ) -> UniversalityScoreRecord:
        """计算 Alpha 的四维普适性评分。"""
        target = markets or self._get_available_markets()
        cache_key = f"{alpha_id}|{'|'.join(sorted(target))}"
        if not force_refresh and cache_key in self._cache:
            self._log(f"[UniversalityEngine] cache hit: {alpha_id}")
            return self._cache[cache_key]

        self._log(f"[UniversalityEngine] scoring: {alpha_id}  n={len(target)}")

        meta     = self._alpha_loader.load_alpha_metadata(alpha_id)
        vol_sens = meta.get("vol_sensitivity",       0.5)
        liq_sens = meta.get("liquidity_sensitivity", 0.5)

        slices        = self._collect_slices(alpha_id, target)
        t_coeffs      = [s.transfer_coeff    for s in slices]
        ic_decays     = [s.ic_decay           for s in slices]
        align_scores  = [s.alignment_score    for s in slices]
        port_scores   = [s.portability_prior  for s in slices]
        vol_scales    = [self._get_vol_scale(alpha_id, m)  for m in target]
        liq_scales    = [self._get_liq_scale(alpha_id, m)  for m in target]
        struct_dists  = self._collect_struct_distances(target)
        reg_invs      = [self._get_regime_inv(alpha_id, m) for m in target]
        n_transferable = sum(1 for s in slices if s.is_transferable)

        w  = (params or {}).get("weights", self._weights)
        cs = compute_cross_market_stability(t_coeffs, n_transferable, len(target))
        rr = compute_regime_robustness(align_scores, reg_invs)
        si = compute_structural_invariance(port_scores, struct_dists, ic_decays)
        ei = compute_execution_independence(vol_scales, liq_scales, vol_sens, liq_sens)
        total = compute_universality_score(cs, rr, si, ei, weights=w)
        grade, verdict = classify_universality_grade(total)

        avg_t     = sum(t_coeffs)     / max(len(t_coeffs),     1)
        t_std     = _std(t_coeffs)
        avg_align = sum(align_scores) / max(len(align_scores),  1)
        avg_decay = sum(ic_decays)    / max(len(ic_decays),     1)

        def _dim(name: str, score: float, wk: str, evidence: str) -> DimensionScore:
            wv = w.get(wk, 0.25)
            return DimensionScore(name=name, score=score, weight=wv,
                                  contribution=round(score * wv, 4),
                                  evidence=evidence)

        record = UniversalityScoreRecord(
            alpha_id               = alpha_id,
            markets                = target,
            dim_cross_market       = _dim(
                "cross_market_stability", cs, "cross_market_stability",
                f"{n_transferable}/{len(target)} 市场可迁移，平均T={avg_t:.3f}"),
            dim_regime             = _dim(
                "regime_robustness", rr, "regime_robustness",
                f"平均对齐分={avg_align:.3f}，平均Regime不变性={sum(reg_invs)/max(len(reg_invs),1):.3f}"),
            dim_structural         = _dim(
                "structural_invariance", si, "structural_invariance",
                f"平均IC衰减={avg_decay:.3f}，可迁移性先验均值={sum(port_scores)/max(len(port_scores),1):.3f}"),
            dim_execution          = _dim(
                "execution_independence", ei, "execution_independence",
                f"vol_sens={vol_sens:.2f}，liq_sens={liq_sens:.2f}，vol_cv={_cv(vol_scales):.3f}"),
            market_slices          = slices,
            n_markets_tested       = len(target),
            n_markets_transferable = n_transferable,
            avg_transfer_coeff     = round(avg_t,     4),
            transfer_coeff_std     = round(t_std,     4),
            avg_alignment_score    = round(avg_align, 4),
            avg_ic_decay           = round(avg_decay, 4),
            score                  = total,
            grade                  = grade,
            verdict                = verdict,
            status                 = "computed",
            scored_at              = _now(),
        )
        self._cache[cache_key] = record
        self._update_state(alpha_id, total, grade)
        self._log(f"[UniversalityEngine] {alpha_id}  score={total:.4f}  "
                  f"grade={grade}  CS={cs:.3f} RR={rr:.3f} SI={si:.3f} EI={ei:.3f}")
        return record

    def score_batch(self, alpha_ids: list[str],
                    markets: list[str] | None = None,
                    force_refresh: bool = False) -> list[UniversalityScoreRecord]:
        return [self.score(a, markets=markets, force_refresh=force_refresh)
                for a in alpha_ids]

    def get_leaderboard(self, limit: int = 20) -> list[dict]:
        records = sorted(self._cache.values(), key=lambda r: r.score, reverse=True)
        return [r.to_dict() for r in records[:limit]]

    def get_cached(self, alpha_id: str) -> Optional[UniversalityScoreRecord]:
        for key, rec in self._cache.items():
            if key.startswith(f"{alpha_id}|"):
                return rec
        return None

    def get_all_cached(self) -> dict[str, UniversalityScoreRecord]:
        return dict(self._cache)

    def get_state(self) -> UniversalityState:
        return self._state

    def clear_cache(self) -> None:
        self._cache.clear()
        self._log("[UniversalityEngine] cache cleared")

    # ���� �����ռ������� Phase 2/3 ���棩������������������������������������������������������������

    def _collect_slices(self, alpha_id: str, markets: list[str]) -> list:
        slices = []
        for mkt in markets:
            t  = self._find_transfer(alpha_id, mkt)
            al = self._find_alignment(mkt)
            sv = self._structure_cache.get(mkt)
            slices.append(MarketPerformanceSlice(
                market_id        = mkt,
                transfer_coeff   = t.transfer_coefficient  if t  else 0.35,
                ic_estimated     = t.expected_ic_dst       if t  else 0.02,
                ic_decay         = t.expected_ic_decay     if t  else 0.40,
                alignment_score  = al.alignment_score      if al else 0.40,
                portability_prior = sv.portability_score   if sv else 0.40,
                is_transferable  = t.is_transferable       if t  else False,
            ))
        return slices

    def _get_vol_scale(self, alpha_id: str, mkt: str) -> float:
        t = self._find_transfer(alpha_id, mkt)
        return t.vol_scale if t else 1.0

    def _get_liq_scale(self, alpha_id: str, mkt: str) -> float:
        t = self._find_transfer(alpha_id, mkt)
        return t.liq_scale if t else 1.0

    def _get_regime_inv(self, alpha_id: str, mkt: str) -> float:
        t = self._find_transfer(alpha_id, mkt)
        return t.regime_invariance if t else 0.5

    def _collect_struct_distances(self, markets: list[str]) -> list[float]:
        from ..utils.cross_market_utils import compute_structural_distance
        vecs   = [self._structure_cache.get(m) for m in markets]
        valids = [v for v in vecs if v is not None]
        if len(valids) < 2:
            return [0.3] * len(markets)
        dists = []
        for v in vecs:
            if v is None:
                dists.append(0.3)
            else:
                others = [o for o in valids if o.market_id != v.market_id]
                avg_d  = sum(compute_structural_distance(v, o) for o in others) / len(others)
                dists.append(round(avg_d, 4))
        return dists

    def _find_transfer(self, alpha_id: str, market_dst: str):
        for key, rec in self._transfer_cache.items():
            if key.startswith(f"{alpha_id}|") and key.endswith(f">{market_dst}"):
                return rec
        return None

    def _find_alignment(self, market_b: str):
        best = None
        for key, rec in self._alignment_cache.items():
            if market_b in key:
                if best is None or rec.alignment_score > best.alignment_score:
                    best = rec
        return best

    def _get_available_markets(self) -> list[str]:
        if self._structure_cache:
            return list(self._structure_cache.keys())
        from ..datasource.market_loader import MarketDataLoader
        return MarketDataLoader().list_available_markets()

    # ���� ״̬���� ������������������������������������������������������������������������������������������������������������

    def _update_state(self, alpha_id: str, score: float, grade: str) -> None:
        self._state.total_scored += 1
        n = self._state.total_scored
        self._state.avg_score = round(
            (self._state.avg_score * (n - 1) + score) / n, 4
        )
        if score > self._state.top_score:
            self._state.top_alpha = alpha_id
            self._state.top_score = score
        grade_map = {
            "UNIVERSAL": "universal_count", "PORTABLE": "portable_count",
            "LOCAL":     "local_count",     "FRAGILE":  "fragile_count",
        }
        attr = grade_map.get(grade)
        if attr:
            setattr(self._state, attr, getattr(self._state, attr) + 1)
        self._state.status = "running"


# ���� ���������� ����������������������������������������������������������������������������������������������������������������

def _now() -> str:
    return str(datetime.now())[:19]


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return math.sqrt(sum((x - avg) ** 2 for x in values) / len(values))


def _cv(values: list[float]) -> float:
    if not values:
        return 0.0
    avg = sum(values) / len(values)
    return _std(values) / max(abs(avg), 1e-9)
