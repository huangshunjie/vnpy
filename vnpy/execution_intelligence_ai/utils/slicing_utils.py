"""
execution_intelligence_ai/utils/slicing_utils.py  (Phase 2)

拆单工具函数 — TWAP / VWAP / POV / Adaptive 全套算法。
"""
from __future__ import annotations
import math
from datetime import datetime, timedelta


# ──────────────────────────────────────────────────────────────────────
#  TWAP
# ──────────────────────────────────────────────────────────────────────

def calc_twap_schedule(
    total_volume: float,
    n_slices: int,
    start_dt: datetime,
    interval_seconds: int = 60,
) -> list[tuple[datetime, float]]:
    """
    TWAP — 均匀时间分配拆单计划。

    Returns list of (scheduled_time, volume_per_slice).
    最后一片自动补齐尾差（避免浮点累积误差）。
    """
    if n_slices <= 0 or total_volume <= 0:
        return []
    vol_per = round(total_volume / n_slices, 6)
    schedule: list[tuple[datetime, float]] = []
    allocated = 0.0
    for i in range(n_slices):
        t = start_dt + timedelta(seconds=i * interval_seconds)
        if i == n_slices - 1:
            vol = round(total_volume - allocated, 6)
        else:
            vol = vol_per
        allocated += vol
        schedule.append((t, vol))
    return schedule


# ──────────────────────────────────────────────────────────────────────
#  VWAP
# ──────────────────────────────────────────────────────────────────────

def calc_vwap_weights(volume_profile: list[float]) -> list[float]:
    """
    根据历史成交量分布计算每个时段的 VWAP 权重。
    如果分布全为零，退化为等权。
    """
    total = sum(volume_profile)
    n = len(volume_profile)
    if n == 0:
        return []
    if total <= 0:
        return [round(1.0 / n, 8)] * n
    return [round(v / total, 8) for v in volume_profile]


def calc_vwap_schedule(
    total_volume: float,
    volume_profile: list[float],
    start_dt: datetime,
    interval_seconds: int = 60,
) -> list[tuple[datetime, float]]:
    """
    VWAP — 按历史成交量分布加权拆单。

    volume_profile: 每个时段的历史成交量（不要求归一化）。
    Returns list of (scheduled_time, volume_for_slot).
    """
    weights = calc_vwap_weights(volume_profile)
    if not weights or total_volume <= 0:
        return []
    schedule: list[tuple[datetime, float]] = []
    allocated = 0.0
    n = len(weights)
    for i, w in enumerate(weights):
        t = start_dt + timedelta(seconds=i * interval_seconds)
        if i == n - 1:
            vol = round(total_volume - allocated, 6)
        else:
            vol = round(total_volume * w, 6)
        allocated += vol
        schedule.append((t, max(vol, 0.0)))
    return schedule


# ──────────────────────────────────────────────────────────────────────
#  POV  (Percentage of Volume)
# ──────────────────────────────────────────────────────────────────────

def calc_pov_slice(
    market_volume_this_bar: float,
    pov_rate: float,
    remaining_volume: float,
    min_vol: float = 1.0,
) -> float:
    """
    POV — 按市场实时成交量的固定百分比计算本期下单量。

    pov_rate: 目标参与率，如 0.10 = 占市场成交量的 10%。
    返回本期应下单量（不超过剩余量）。
    """
    if market_volume_this_bar <= 0 or pov_rate <= 0:
        return 0.0
    target = market_volume_this_bar * pov_rate
    target = max(target, min_vol)
    return round(min(target, remaining_volume), 6)


def estimate_pov_n_slices(
    total_volume: float,
    avg_market_volume_per_bar: float,
    pov_rate: float,
) -> int:
    """
    POV — 估算完成所需时段数（用于初始计划）。
    """
    if avg_market_volume_per_bar <= 0 or pov_rate <= 0:
        return 1
    vol_per_bar = avg_market_volume_per_bar * pov_rate
    if vol_per_bar <= 0:
        return 1
    return max(1, math.ceil(total_volume / vol_per_bar))


# ──────────────────────────────────────────────────────────────────────
#  Adaptive
# ──────────────────────────────────────────────────────────────────────

def adaptive_slice_volume(
    base_volume: float,
    volatility: float,
    liquidity_score: float,
    vol_threshold: float = 0.015,
    liq_threshold: float = 0.5,
) -> float:
    """
    Adaptive — 根据实时波动率 + 流动性评分动态调整切片量。

    - 高波动 → 减小切片，降低冲击
    - 低流动性 → 减小切片，避免吃掉对盘

    volatility:      当日收益率标准差（如 0.02 = 2%）
    liquidity_score: [0,1]，越高流动性越好
    Returns adjusted volume.
    """
    factor = 1.0

    # 波动调整
    if volatility > vol_threshold:
        excess = volatility - vol_threshold
        vol_factor = max(0.25, 1.0 - excess * 12)
        factor *= vol_factor

    # 流动性调整
    if liquidity_score < liq_threshold:
        deficit = liq_threshold - liquidity_score
        liq_factor = max(0.3, 1.0 - deficit * 1.5)
        factor *= liq_factor

    return round(base_volume * factor, 6)


def build_adaptive_schedule(
    total_volume: float,
    n_slices: int,
    start_dt: datetime,
    interval_seconds: int,
    volatilities: list[float],
    liquidity_scores: list[float],
) -> list[tuple[datetime, float]]:
    """
    Adaptive — 使用预估的波动率 + 流动性序列构建自适应计划。

    如果 volatilities / liquidity_scores 长度不足，
    用最后一个值填充。
    """
    if n_slices <= 0 or total_volume <= 0:
        return []

    def _get(lst: list[float], i: int, default: float) -> float:
        if not lst:
            return default
        return lst[i] if i < len(lst) else lst[-1]

    base = total_volume / n_slices
    raw_vols: list[float] = []
    for i in range(n_slices):
        vol = adaptive_slice_volume(
            base_volume     = base,
            volatility      = _get(volatilities,     i, 0.01),
            liquidity_score = _get(liquidity_scores, i, 1.0),
        )
        raw_vols.append(vol)

    # 按比例缩放使总量精确等于 total_volume
    total_raw = sum(raw_vols)
    if total_raw <= 0:
        total_raw = 1.0

    schedule: list[tuple[datetime, float]] = []
    allocated = 0.0
    for i, rv in enumerate(raw_vols):
        t = start_dt + timedelta(seconds=i * interval_seconds)
        if i == n_slices - 1:
            vol = round(total_volume - allocated, 6)
        else:
            vol = round(total_volume * rv / total_raw, 6)
        allocated += vol
        schedule.append((t, max(vol, 0.0)))
    return schedule


# ──────────────────────────────────────────────────────────────────────
#  通用辅助
# ──────────────────────────────────────────────────────────────────────

def adjust_slice_for_volatility(
    base_volume: float,
    volatility: float,
    vol_threshold: float = 0.02,
) -> float:
    """简化版波动调整（向后兼容 Phase 1 接口）。"""
    return adaptive_slice_volume(
        base_volume     = base_volume,
        volatility      = volatility,
        liquidity_score = 1.0,
        vol_threshold   = vol_threshold,
    )


def validate_slice_plan(slices: list[dict], total_volume: float,
                        tol: float = 0.01) -> bool:
    """校验切片计划总量与父订单量一致（允许 tol 误差）。"""
    if not slices:
        return False
    total = sum(s.get("volume", 0.0) for s in slices)
    return abs(total - total_volume) <= tol
