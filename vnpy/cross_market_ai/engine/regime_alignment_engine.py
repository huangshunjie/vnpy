"""
cross_market_ai/engine/regime_alignment_engine.py

Phase 3: Regime Alignment Engine — 市场状态对齐引擎。

职责：
  1. 加载两市场的 Regime 分布数据
  2. 计算分布相似度（Bhattacharyya / KL / JS 散度）
  3. 对齐 Regime 标签映射
  4. 输出对齐评分，作为 Alpha 迁移的预条件
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..datasource.regime_loader import RegimeDataLoader
from ..model.regime_model import RegimeAlignmentRecord, RegimeAlignmentState
from ..utils.regime_utils import (
    compute_bhattacharyya,
    compute_kl_divergence,
    compute_regime_entropy,
    align_regime_labels,
    get_unmatched_regimes,
    compute_regime_alignment_score,
    is_regime_alignable,
    compute_persistence,
)


class RegimeAlignmentEngine:
    """
    Regime 对齐引擎。

    输出 RegimeAlignmentRecord，包含：
      - 分布相似度（overlap / kl_div）
      - 标签对齐映射 {regime_a: regime_b}
      - 综合对齐评分 ∈ [0,1]
      - 是否可对齐（作为 Alpha 迁移预条件）
    """

    def __init__(
        self,
        log_fn: Callable | None = None,
        main_engine=None,
        alignable_threshold: float = 0.35,
    ) -> None:
        self._log       = log_fn or (lambda m, lvl="INFO": None)
        self._loader    = RegimeDataLoader(main_engine=main_engine)
        self._state     = RegimeAlignmentState()
        self._cache:    dict[str, RegimeAlignmentRecord] = {}
        self._threshold = alignable_threshold

    # ── 生命周期 ──────────────────────────────────────────────────────

    def init(self) -> None:
        self._state.status = "idle"
        self._log("[RegimeAlignmentEngine] init()")

    def start(self) -> None:
        self._state.status = "running"
        self._log("[RegimeAlignmentEngine] start()")

    def stop(self) -> None:
        self._state.status = "idle"
        self._log("[RegimeAlignmentEngine] stop()")

    # ── 核心接口 ──────────────────────────────────────────────────────

    def align(
        self,
        market_a:      str,
        market_b:      str,
        force_refresh: bool = False,
        params:        dict | None = None,
    ) -> RegimeAlignmentRecord:
        """
        计算两市场的 Regime 对齐结果。

        Args:
            market_a:      源市场（Alpha 训练市场）
            market_b:      目标市场（Alpha 迁移市场）
            force_refresh: 强制重算，忽略缓存
            params:        可选覆盖参数

        Returns:
            RegimeAlignmentRecord — 完整对齐结果
        """
        cache_key = f"{market_a}|{market_b}"
        if not force_refresh and cache_key in self._cache:
            self._log(f"[RegimeAlignmentEngine] cache hit: {cache_key}")
            return self._cache[cache_key]

        self._log(f"[RegimeAlignmentEngine] aligning: {market_a} ↔ {market_b}")

        # 加载两市场 Regime 分布
        dist_data_a = self._loader.load_regime_distribution(market_a)
        dist_data_b = self._loader.load_regime_distribution(market_b)
        dist_a      = dist_data_a.get("distribution", {})
        dist_b      = dist_data_b.get("distribution", {})

        # 加载历史序列（用于计算留存概率）
        hist_a      = self._loader.load_regime_history(market_a, lookback_days=100)
        hist_b      = self._loader.load_regime_history(market_b, lookback_days=100)
        seq_a       = hist_a.get("sequence", [])
        seq_b       = hist_b.get("sequence", [])

        # 计算分布相似度指标
        overlap     = compute_bhattacharyya(dist_a, dist_b)
        kl_div      = compute_kl_divergence(dist_a, dist_b)
        entropy_a   = compute_regime_entropy(dist_a)
        entropy_b   = compute_regime_entropy(dist_b)
        entropy_diff = abs(entropy_a - entropy_b)

        # 计算留存概率
        persistence_a = compute_persistence(seq_a) if seq_a else dist_data_a.get("persistence", 0.72)
        persistence_b = compute_persistence(seq_b) if seq_b else dist_data_b.get("persistence", 0.72)
        persistence_gap = abs(persistence_a - persistence_b)

        # 对齐 Regime 标签
        threshold    = (params or {}).get("label_threshold", 0.15)
        mapping      = align_regime_labels(dist_a, dist_b, similarity_threshold=threshold)
        n_total      = max(len(dist_a), len(dist_b))
        unmatched_a, unmatched_b = get_unmatched_regimes(dist_a, dist_b, mapping)

        # 综合对齐评分
        alignment_score = compute_regime_alignment_score(
            overlap=overlap,
            kl_div=kl_div,
            persistence_gap=persistence_gap,
            n_matched=len(mapping),
            n_total=n_total,
        )
        alignable = is_regime_alignable(alignment_score, self._threshold)

        record = RegimeAlignmentRecord(
            market_a         = market_a,
            market_b         = market_b,
            overlap_score    = overlap,
            kl_divergence    = kl_div,
            entropy_a        = entropy_a,
            entropy_b        = entropy_b,
            entropy_diff     = entropy_diff,
            aligned_regimes  = mapping,
            unmatched_a      = unmatched_a,
            unmatched_b      = unmatched_b,
            persistence_a    = persistence_a,
            persistence_b    = persistence_b,
            persistence_gap  = persistence_gap,
            alignment_score  = alignment_score,
            is_alignable     = alignable,
            status           = "computed",
            aligned_at       = _now(),
        )

        self._cache[cache_key] = record
        self._update_state(market_a, market_b, alignment_score, alignable)

        self._log(
            f"[RegimeAlignmentEngine] {market_a}↔{market_b}  "
            f"overlap={overlap:.3f}  kl={kl_div:.3f}  "
            f"score={alignment_score:.3f}  alignable={alignable}"
        )
        return record

    def align_batch(
        self,
        pairs: list[tuple[str, str]],
        force_refresh: bool = False,
    ) -> list[RegimeAlignmentRecord]:
        """批量对齐多对市场。"""
        return [self.align(a, b, force_refresh=force_refresh) for a, b in pairs]

    def get_cached(self, market_a: str, market_b: str) -> RegimeAlignmentRecord | None:
        return self._cache.get(f"{market_a}|{market_b}")

    def get_all_cached(self) -> dict[str, RegimeAlignmentRecord]:
        return dict(self._cache)

    def get_state(self) -> RegimeAlignmentState:
        return self._state

    def clear_cache(self) -> None:
        self._cache.clear()
        self._log("[RegimeAlignmentEngine] cache cleared")

    # ── 内部工具 ──────────────────────────────────────────────────────

    def _update_state(
        self,
        market_a: str,
        market_b: str,
        score:    float,
        alignable: bool,
    ) -> None:
        self._state.total_alignments += 1
        if alignable:
            self._state.successful += 1
        else:
            self._state.failed += 1
        n = self._state.total_alignments
        self._state.avg_alignment = round(
            (self._state.avg_alignment * (n - 1) + score) / n, 4
        )
        self._state.last_pair = f"{market_a}↔{market_b}"
        self._state.status    = "running"


def _now() -> str:
    return str(datetime.now())[:19]
