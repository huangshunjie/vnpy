"""
cross_market_ai/engine/structure_mapper.py

Phase 2: Market Structure Mapper — 五维市场结构向量计算引擎。

核心逻辑：
  Market = Vector(σ, liquidity, regime, noise, correlation)

设计原则：
  - Market-agnostic: 不绑定任何单一市场
  - 纯计算，无交易逻辑
  - 结果缓存，支持增量更新
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Callable, Optional

from ..datasource.market_loader import MarketDataLoader
from ..model.structure_model import (
    MarketStructureVector,
    VolatilityStructure,
    LiquidityStructure,
    ParticipantStructure,
    MicrostructureNoise,
    RegimeDistribution,
    StructureState,
)


class StructureMapper:
    """
    市场结构映射器。

    职责：
      1. 从 MarketDataLoader 拉取五维原始数据
      2. 标准化各维度到 [0,1] 或统一量纲
      3. 计算综合评分（complexity / tradability / portability）
      4. 维护结构向量缓存
    """

    def __init__(self, log_fn: Callable | None = None, main_engine=None) -> None:
        self._log         = log_fn or (lambda m, lvl="INFO": None)
        self._loader      = MarketDataLoader(main_engine=main_engine)
        self._cache:  dict[str, MarketStructureVector] = {}
        self._state       = StructureState()
        self._started_at: datetime | None = None

    # ── 生命周期 ──────────────────────────────────────────────────────

    def init(self) -> None:
        self._state.status = "idle"
        self._log("[StructureMapper] init()")

    def start(self) -> None:
        self._started_at   = datetime.now()
        self._state.status = "running"
        self._log("[StructureMapper] start()")

    def stop(self) -> None:
        self._state.status = "idle"
        self._log("[StructureMapper] stop()")

    # ── 核心接口 ──────────────────────────────────────────────────────

    def compute(
        self,
        market_id:       str,
        other_markets:   list[str] | None = None,
        force_refresh:   bool = False,
        params:          dict | None = None,
    ) -> MarketStructureVector:
        """
        计算并返回指定市场的结构向量。

        Args:
            market_id:     市场标识（equity_cn / futures_cn / equity_us / crypto …）
            other_markets: 需要计算跨市场相关性的市场列表
            force_refresh: 强制重新计算，忽略缓存
            params:        可选覆盖参数

        Returns:
            MarketStructureVector — 完整五维结构向量
        """
        if not force_refresh and market_id in self._cache:
            self._log(f"[StructureMapper] cache hit: {market_id}")
            return self._cache[market_id]

        self._log(f"[StructureMapper] computing structure for: {market_id}")

        vol_data     = self._loader.load_volatility_structure(market_id)
        liq_data     = self._loader.load_liquidity_structure(market_id)
        part_data    = self._loader.load_participant_structure(market_id)
        noise_data   = self._loader.load_microstructure_noise(market_id)
        regime_data  = self._loader.load_regime_distribution(market_id)

        vol_struct   = _build_volatility(vol_data)
        liq_struct   = _build_liquidity(liq_data)
        part_struct  = _build_participant(part_data)
        noise_struct = _build_noise(noise_data)
        regime_struct = _build_regime(regime_data)

        cross_corr: dict[str, float] = {}
        for other in (other_markets or []):
            if other != market_id:
                corr_data = self._loader.load_cross_market_correlation(market_id, other)
                cross_corr[other] = corr_data.get("correlation", 0.0)

        complexity   = _compute_complexity(vol_struct, liq_struct, noise_struct)
        tradability  = _compute_tradability(liq_struct, part_struct, noise_struct)
        portability  = _compute_portability(
            vol_struct, liq_struct, part_struct, noise_struct, regime_struct
        )

        vector = MarketStructureVector(
            market_id          = market_id,
            market_type        = _infer_market_type(market_id),
            volatility         = vol_struct,
            liquidity          = liq_struct,
            participant        = part_struct,
            noise              = noise_struct,
            regime             = regime_struct,
            cross_correlations = cross_corr,
            complexity_score   = complexity,
            tradability_score  = tradability,
            portability_score  = portability,
            computed_at        = _now(),
            phase              = 2,
        )

        self._cache[market_id] = vector
        self._update_state(market_id)
        self._log(
            f"[StructureMapper] {market_id}  "
            f"complexity={complexity:.3f}  tradability={tradability:.3f}  "
            f"portability={portability:.3f}"
        )
        return vector

    def compute_all(
        self,
        markets: list[str] | None = None,
        force_refresh: bool = False,
    ) -> dict[str, MarketStructureVector]:
        """批量计算所有市场的结构向量，并互相计算跨市场相关性。"""
        target = markets or self._loader.list_available_markets()
        results: dict[str, MarketStructureVector] = {}
        others = [m for m in target]
        for market_id in target:
            results[market_id] = self.compute(
                market_id,
                other_markets=[m for m in others if m != market_id],
                force_refresh=force_refresh,
            )
        return results

    def get_cached(self, market_id: str) -> Optional[MarketStructureVector]:
        return self._cache.get(market_id)

    def get_all_cached(self) -> dict[str, MarketStructureVector]:
        return dict(self._cache)

    def get_state(self) -> StructureState:
        return self._state

    def clear_cache(self) -> None:
        self._cache.clear()
        self._log("[StructureMapper] cache cleared")

    # ── 内部工具 ──────────────────────────────────────────────────────

    def _update_state(self, market_id: str) -> None:
        if market_id not in self._state.markets:
            self._state.markets.append(market_id)
        self._state.total_mapped  = len(self._cache)
        self._state.last_market_id = market_id
        self._state.last_updated   = _now()
        self._state.status         = "running"


# ── 构建各维度结构对象 ────────────────────────────────────────────────

def _build_volatility(d: dict) -> VolatilityStructure:
    return VolatilityStructure(
        annual_vol      = d.get("annual_vol", 0.0),
        daily_vol       = d.get("daily_vol",  0.0),
        vol_of_vol      = d.get("vol_of_vol", 0.0),
        skew            = d.get("skew",       0.0),
        excess_kurtosis = d.get("excess_kurtosis", 0.0),
        jump_intensity  = d.get("jump_intensity",  0.0),
        source          = d.get("source", "prior"),
    )


def _build_liquidity(d: dict) -> LiquidityStructure:
    return LiquidityStructure(
        bid_ask_spread_bps  = d.get("bid_ask_spread_bps",  0.0),
        depth_score         = d.get("depth_score",         0.0),
        turnover_ratio      = d.get("turnover_ratio",      0.0),
        market_impact_coeff = d.get("market_impact_coeff", 0.0),
        lot_size            = d.get("lot_size",  1.0),
        tick_size           = d.get("tick_size", 0.01),
        source              = d.get("source", "prior"),
    )


def _build_participant(d: dict) -> ParticipantStructure:
    return ParticipantStructure(
        retail_ratio        = d.get("retail_ratio",         0.0),
        institutional_ratio = d.get("institutional_ratio",  0.0),
        hft_ratio           = d.get("hft_ratio",            0.0),
        info_asymmetry      = d.get("info_asymmetry",       0.0),
        source              = d.get("source", "prior"),
    )


def _build_noise(d: dict) -> MicrostructureNoise:
    return MicrostructureNoise(
        noise_ratio        = d.get("noise_ratio",        0.0),
        autocorr_lag1      = d.get("autocorr_lag1",      0.0),
        price_discreteness = d.get("price_discreteness", 0.0),
        adverse_selection  = d.get("adverse_selection",  0.0),
        limit_distortion   = d.get("limit_distortion",   0.0),
        source             = d.get("source", "prior"),
    )


def _build_regime(d: dict) -> RegimeDistribution:
    dist     = d.get("distribution", {})
    dominant = max(dist, key=lambda k: dist[k]) if dist else ""
    entropy  = _shannon_entropy(dist)
    return RegimeDistribution(
        distribution    = dist,
        n_regimes       = d.get("n_regimes", len(dist)),
        dominant_regime = dominant,
        entropy         = entropy,
        source          = d.get("source", "prior"),
    )


# ── 评分计算 ──────────────────────────────────────────────────────────

def _compute_complexity(
    vol: VolatilityStructure,
    liq: LiquidityStructure,
    noise: MicrostructureNoise,
) -> float:
    """
    市场复杂度评分 ∈ [0, 1]。
    高复杂度 = 高波动 + 低流动性 + 高噪音。
    """
    vol_score   = min(vol.annual_vol / 1.0, 1.0)
    spread_score = min(liq.bid_ask_spread_bps / 20.0, 1.0)
    noise_score = noise.noise_ratio
    return round((vol_score * 0.4 + spread_score * 0.35 + noise_score * 0.25), 4)


def _compute_tradability(
    liq: LiquidityStructure,
    part: ParticipantStructure,
    noise: MicrostructureNoise,
) -> float:
    """
    可交易性评分 ∈ [0, 1]。
    高可交易性 = 低价差 + 高深度 + 低信息不对称。
    """
    spread_score = max(0.0, 1.0 - liq.bid_ask_spread_bps / 20.0)
    depth_score  = liq.depth_score
    asym_score   = max(0.0, 1.0 - part.info_asymmetry)
    limit_pen    = max(0.0, 1.0 - noise.limit_distortion)
    return round((spread_score * 0.35 + depth_score * 0.30 + asym_score * 0.20 + limit_pen * 0.15), 4)


def _compute_portability(
    vol:   VolatilityStructure,
    liq:   LiquidityStructure,
    part:  ParticipantStructure,
    noise: MicrostructureNoise,
    reg:   RegimeDistribution,
) -> float:
    """
    Alpha 可迁移性先验评分 ∈ [0, 1]。
    高可迁移性 = 低噪音 + 低跳跃 + 高流动性 + 低参与者偏斜 + Regime稳定。

    这是 Phase 3 迁移引擎的输入先验，而非最终评分。
    """
    noise_score   = max(0.0, 1.0 - noise.noise_ratio * 2)
    jump_score    = max(0.0, 1.0 - vol.jump_intensity * 10)
    liq_score     = liq.depth_score
    retail_pen    = max(0.0, 1.0 - part.retail_ratio * 0.5)
    regime_stable = max(0.0, 1.0 - reg.entropy)
    limit_pen     = max(0.0, 1.0 - noise.limit_distortion)
    raw = (
        noise_score   * 0.25 +
        jump_score    * 0.20 +
        liq_score     * 0.20 +
        retail_pen    * 0.15 +
        regime_stable * 0.12 +
        limit_pen     * 0.08
    )
    return round(max(0.0, min(1.0, raw)), 4)


# ── 纯函数工具 ────────────────────────────────────────────────────────

def _shannon_entropy(dist: dict) -> float:
    """计算 Regime 分布的香农熵（归一化到 [0,1]）。"""
    values = [v for v in dist.values() if v > 0]
    if not values:
        return 0.0
    raw = -sum(p * math.log2(p) for p in values)
    max_entropy = math.log2(len(values)) if len(values) > 1 else 1.0
    return round(raw / max_entropy, 4) if max_entropy > 0 else 0.0


def _infer_market_type(market_id: str) -> str:
    """从 market_id 推断市场类型标签。"""
    for key in ("equity_cn", "futures_cn", "equity_us", "crypto", "forex", "fixed_income"):
        if market_id.startswith(key.split("_")[0]) or market_id == key:
            return key
    return "custom"


def _now() -> str:
    return str(datetime.now())[:19]
