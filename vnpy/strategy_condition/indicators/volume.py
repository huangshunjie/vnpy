"""
strategy_condition/indicators/volume.py
成交量类指标：量比 / 放量上涨 / 缩量调整
"""
from __future__ import annotations
from typing import List, Tuple


def check_volume_ratio(volumes: List[float],
                       period: int = 20,
                       min_ratio: float = 1.5) -> Tuple[bool, float]:
    """当日成交量 / MA(period) 成交量 >= min_ratio"""
    if len(volumes) < period + 1:
        return False, 0.0
    ma_vol = sum(volumes[-period - 1:-1]) / period
    if ma_vol <= 0:
        return False, 0.0
    ratio  = volumes[-1] / ma_vol
    passed = ratio >= min_ratio
    score  = min(ratio / (min_ratio * 2 + 1e-9), 1.0)
    return passed, score if passed else 0.0


def check_volume_price_up(closes: List[float],
                           volumes: List[float],
                           period: int = 20,
                           min_ratio: float = 1.5,
                           min_chg: float = 1.0) -> Tuple[bool, float]:
    """
    放量上涨：
    当日涨幅 >= min_chg%  AND  成交量 >= 均量 min_ratio 倍
    """
    if len(closes) < 2 or len(volumes) < period + 1:
        return False, 0.0
    chg_pct = (closes[-1] - closes[-2]) / closes[-2] * 100 if closes[-2] > 0 else 0.0
    ma_vol  = sum(volumes[-period - 1:-1]) / period
    vol_r   = volumes[-1] / ma_vol if ma_vol > 0 else 0.0
    passed  = chg_pct >= min_chg and vol_r >= min_ratio
    score   = min((chg_pct / (min_chg * 2 + 1e-9)) * (vol_r / (min_ratio * 2 + 1e-9)), 1.0)
    return passed, max(score, 0.0) if passed else 0.0


def check_volume_shrink(volumes: List[float],
                        period: int = 20,
                        max_ratio: float = 0.7) -> Tuple[bool, float]:
    """缩量调整：当日成交量 <= 均量 max_ratio 倍"""
    if len(volumes) < period + 1:
        return False, 0.0
    ma_vol = sum(volumes[-period - 1:-1]) / period
    if ma_vol <= 0:
        return False, 0.0
    ratio  = volumes[-1] / ma_vol
    passed = ratio <= max_ratio
    score  = max(1.0 - ratio / (max_ratio + 1e-9), 0.0)
    return passed, score if passed else 0.0
