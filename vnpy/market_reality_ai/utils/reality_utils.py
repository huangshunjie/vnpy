"""
market_reality_ai/utils/reality_utils.py

Phase 1: Stub — 通用仿真工具函数。
Phase 2+: 填充具体实现。
"""
from __future__ import annotations
import uuid
from datetime import datetime


def new_id(prefix: str = "SIM") -> str:
    """生成唯一仿真 ID。"""
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


def now_str() -> str:
    return str(datetime.now())[:19]


def clamp(value: float, lo: float, hi: float) -> float:
    """将 value 限制在 [lo, hi] 范围内。"""
    return max(lo, min(hi, value))


def bps_to_pct(bps: float) -> float:
    """基点转百分比。"""
    return bps / 10000.0


def pct_to_bps(pct: float) -> float:
    """百分比转基点。"""
    return pct * 10000.0


def safe_div(numerator: float, denominator: float,
              default: float = 0.0) -> float:
    """安全除法，避免除以零。"""
    if abs(denominator) < 1e-12:
        return default
    return numerator / denominator


def weighted_average(values: list[float],
                      weights: list[float]) -> float:
    """加权平均。"""
    total_w = sum(weights)
    if total_w < 1e-12:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_w
