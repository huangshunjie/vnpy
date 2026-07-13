"""
cross_market_ai/engine/alpha_transfer_engine.py

Phase 3: Alpha Transfer Engine — Alpha 迁移引擎。

核心公式：Alpha_B = T(Alpha_A, Market_A → Market_B)

职责：
  1. 从 datasource 加载 Alpha 元数据 + 目标市场结构
  2. 计算四个迁移条件（correlation_stability / regime_invariance /
                       volatility_sensitivity / liquidity_sensitivity）
  3. 计算迁移系数 T ∈ [0,1]
  4. 输出完整 AlphaTransferRecord，含调整参数和预测性能
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from ..datasource.alpha_loader import AlphaDataLoader
from ..datasource.regime_loader import RegimeDataLoader
from ..model.alpha_model import AlphaTransferRecord, AlphaTransferState
from ..utils.transfer_utils import (
    compute_transfer_coefficient,
    is_transferable,
    classify_transfer_confidence,
    compute_vol_scale,
    compute_liq_scale,
    compute_signal_decay_adjustment,
    predict_transferred_ic,
    predict_transferred_sharpe,
    compute_ic_decay_rate,
    derive_transfer_conditions_from_structure,
)


class AlphaTransferEngine:
    """
    Alpha 迁移引擎。

    输出 AlphaTransferRecord，包含：
      - 四个迁移条件评分
      - 迁移系数 T ∈ [0,1]
      - 调整后的参数（vol_scale / liq_scale / decay）
      - 预测在目标市场的 IC 和 Sharpe
      - 迁移结论（可迁移 / 拒绝 + 原因）
    """

    def __init__(
        self,
        log_fn:      Callable | None = None,
        main_engine  = None,
        threshold:   float = 0.40,
    ) -> None:
        self._log         = log_fn or (lambda m, lvl="INFO": None)
        self._alpha_loader = AlphaDataLoader(main_engine=main_engine)
        self._regime_loader = RegimeDataLoader(main_engine=main_engine)
        self._state       = AlphaTransferState()
        self._cache:      dict[str, AlphaTransferRecord] = {}
        self._threshold   = threshold
        self._structure_cache: dict[str, object] = {}

    # ── 生命周期 ──────────────────────────────────────────────────────

    def init(self) -> None:
        self._state.status = "idle"
        self._log("[AlphaTransferEngine] init()")

    def start(self) -> None:
        self._state.status = "running"
        self._log("[AlphaTransferEngine] start()")

    def stop(self) -> None:
        self._state.status = "idle"
        self._log("[AlphaTransferEngine] stop()")

    def inject_structure_cache(self, cache: dict) -> None:
        """注入来自 StructureMapper 的结构向量缓存（Phase 2 成果复用）。"""
        self._structure_cache = cache

    # ── 核心接口 ──────────────────────────────────────────────────────

    def transfer(
        self,
        alpha_id:      str,
        market_src:    str,
        market_dst:    str,
        force_refresh: bool = False,
        params:        dict | None = None,
    ) -> AlphaTransferRecord:
        """
        计算 Alpha 从 market_src 迁移到 market_dst 的完整结果。

        Args:
            alpha_id:      Alpha 标识（momentum / mean_reversion / …）
            market_src:    训练市场
            market_dst:    目标市场
            force_refresh: 强制重算
            params:        可选覆盖参数（覆盖 threshold 等）

        Returns:
            AlphaTransferRecord
        """
        cache_key = f"{alpha_id}|{market_src}→{market_dst}"
        if not force_refresh and cache_key in self._cache:
            self._log(f"[AlphaTransferEngine] cache hit: {cache_key}")
            return self._cache[cache_key]

        self._log(f"[AlphaTransferEngine] transferring: {alpha_id}  {market_src}→{market_dst}")

        # 1. 加载 Alpha 元数据
        alpha_meta     = self._alpha_loader.load_alpha_metadata(alpha_id)
        alpha_perf_src = self._alpha_loader.load_alpha_performance(alpha_id, market_src)
        regime_profile = self._alpha_loader.load_alpha_regime_profile(alpha_id, market_src)

        vol_sens    = alpha_meta.get("vol_sensitivity",       0.5)
        liq_sens    = alpha_meta.get("liquidity_sensitivity", 0.5)
        regime_inv  = regime_profile.get("regime_invariance", 0.5)
        decay_days  = alpha_meta.get("signal_decay_days",     15)
        ic_src      = alpha_perf_src.get("ic_mean",           0.03)
        sharpe_src  = alpha_perf_src.get("sharpe",            0.5)

        # 2. 尝试从 StructureMapper 缓存获取结构向量
        vec_src = self._structure_cache.get(market_src)
        vec_dst = self._structure_cache.get(market_dst)

        if vec_src is not None and vec_dst is not None:
            # Phase 2 结构向量可用 → 精确计算迁移条件
            conditions = derive_transfer_conditions_from_structure(
                vec_src,
                vec_dst,
                alpha_vol_sensitivity   = vol_sens,
                alpha_liq_sensitivity   = liq_sens,
                alpha_regime_invariance = regime_inv,
            )
            corr_stab     = conditions["correlation_stability"]
            vol_sensitivity_cond  = conditions["volatility_sensitivity"]
            liq_sensitivity_cond  = conditions["liquidity_sensitivity"]
            regime_inv_cond       = conditions["regime_invariance"]

            vol_src = vec_src.volatility.annual_vol
            vol_dst = vec_dst.volatility.annual_vol
            spr_src = vec_src.liquidity.bid_ask_spread_bps
            spr_dst = vec_dst.liquidity.bid_ask_spread_bps
            regime_stab_dst = max(0.0, 1.0 - vec_dst.regime.entropy)
        else:
            # 降级：仅用 Alpha 元数据先验
            corr_stab             = 0.5
            vol_sensitivity_cond  = vol_sens * 0.6
            liq_sensitivity_cond  = liq_sens * 0.6
            regime_inv_cond       = regime_inv

            # 用 datasource 加载基础结构参数
            from ..datasource.market_loader import MarketDataLoader
            loader      = MarketDataLoader()
            vol_src     = loader.load_volatility_structure(market_src).get("annual_vol", 0.2)
            vol_dst     = loader.load_volatility_structure(market_dst).get("annual_vol", 0.2)
            spr_src     = loader.load_liquidity_structure(market_src).get("bid_ask_spread_bps", 5.0)
            spr_dst     = loader.load_liquidity_structure(market_dst).get("bid_ask_spread_bps", 5.0)
            regime_dist = self._regime_loader.load_regime_distribution(market_dst)
            regime_stab_dst = max(0.0, 1.0 - regime_dist.get("entropy", 0.5))

        # 3. 计算迁移系数 T
        threshold = (params or {}).get("threshold", self._threshold)
        t_coeff   = compute_transfer_coefficient(
            correlation_stability  = corr_stab,
            regime_invariance      = regime_inv_cond,
            volatility_sensitivity = vol_sensitivity_cond,
            liquidity_sensitivity  = liq_sensitivity_cond,
        )

        # 4. 计算调整参数
        vol_scale  = compute_vol_scale(vol_src, vol_dst, sensitivity=vol_sens)
        liq_scale  = compute_liq_scale(spr_src, spr_dst, sensitivity=liq_sens)
        decay_adj  = compute_signal_decay_adjustment(
            decay_days, vol_scale, regime_stab_dst
        )

        # 5. 预测目标市场性能
        ic_dst    = predict_transferred_ic(ic_src, t_coeff, vol_scale, regime_inv_cond)
        sharpe_dst = predict_transferred_sharpe(sharpe_src, t_coeff, liq_scale)
        ic_decay  = compute_ic_decay_rate(ic_src, ic_dst)

        # 6. 迁移结论
        transferable    = is_transferable(t_coeff, threshold)
        confidence_lbl  = classify_transfer_confidence(t_coeff)
        rejection_reason = ""
        if not transferable:
            reasons = []
            if regime_inv_cond < 0.3:
                reasons.append("低 Regime 不变性")
            if vol_sensitivity_cond > 0.7:
                reasons.append("高波动率敏感度")
            if liq_sensitivity_cond > 0.7:
                reasons.append("高流动性敏感度")
            if corr_stab < 0.3:
                reasons.append("低相关性稳定性")
            rejection_reason = "；".join(reasons) if reasons else "迁移系数低于门槛"

        record = AlphaTransferRecord(
            alpha_id                = alpha_id,
            market_src              = market_src,
            market_dst              = market_dst,
            correlation_stability   = corr_stab,
            regime_invariance       = regime_inv_cond,
            volatility_sensitivity  = vol_sensitivity_cond,
            liquidity_sensitivity   = liq_sensitivity_cond,
            transfer_coefficient    = t_coeff,
            vol_scale               = vol_scale,
            liq_scale               = liq_scale,
            signal_decay_adjusted   = decay_adj,
            expected_ic_src         = ic_src,
            expected_ic_dst         = ic_dst,
            expected_ic_decay       = ic_decay,
            expected_sharpe_dst     = sharpe_dst,
            is_transferable         = transferable,
            rejection_reason        = rejection_reason,
            confidence              = confidence_lbl,
            status                  = "computed",
            transferred_at          = _now(),
        )

        self._cache[cache_key] = record
        self._update_state(alpha_id, market_src, market_dst, t_coeff, transferable)

        self._log(
            f"[AlphaTransferEngine] {alpha_id}  {market_src}→{market_dst}  "
            f"T={t_coeff:.3f}  IC_decay={ic_decay:.3f}  "
            f"conf={confidence_lbl}  ok={transferable}"
        )
        return record

    def transfer_batch(
        self,
        alpha_id:   str,
        market_src: str,
        targets:    list[str],
        force_refresh: bool = False,
    ) -> list[AlphaTransferRecord]:
        """将一个 Alpha 批量迁移到多个目标市场。"""
        return [
            self.transfer(alpha_id, market_src, dst, force_refresh=force_refresh)
            for dst in targets
        ]

    def get_cached(
        self, alpha_id: str, market_src: str, market_dst: str
    ) -> Optional[AlphaTransferRecord]:
        return self._cache.get(f"{alpha_id}|{market_src}→{market_dst}")

    def get_all_cached(self) -> dict[str, AlphaTransferRecord]:
        return dict(self._cache)

    def get_state(self) -> AlphaTransferState:
        return self._state

    def clear_cache(self) -> None:
        self._cache.clear()
        self._log("[AlphaTransferEngine] cache cleared")

    # ── 内部工具 ──────────────────────────────────────────────────────

    def _update_state(
        self,
        alpha_id:    str,
        market_src:  str,
        market_dst:  str,
        coeff:       float,
        transferable: bool,
    ) -> None:
        self._state.total_transfers += 1
        if transferable:
            self._state.successful += 1
        else:
            self._state.rejected += 1
        n = self._state.total_transfers
        self._state.avg_coefficient = round(
            (self._state.avg_coefficient * (n - 1) + coeff) / n, 4
        )
        self._state.last_alpha_id = alpha_id
        self._state.last_pair     = f"{market_src}→{market_dst}"
        self._state.status        = "running"


def _now() -> str:
    return str(datetime.now())[:19]
