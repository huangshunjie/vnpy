"""
execution_intelligence_ai/utils/execution_utils.py  (Phase 1 stub)

执行工具函数骨架。Phase 2+ 实现。
"""
from __future__ import annotations
import uuid
from datetime import datetime


def generate_execution_id() -> str:
    """生成唯一执行任务 ID。"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"EXE_{ts}_{uuid.uuid4().hex[:6].upper()}"


def generate_slice_id(execution_id: str, sequence: int) -> str:
    """生成切片子订单 ID。"""
    return f"{execution_id}_S{sequence:04d}"


def calc_fill_rate(filled: float, total: float) -> float:
    """计算成交率。"""
    if total <= 0:
        return 0.0
    return round(min(filled / total, 1.0), 6)


def calc_slippage_bps(target_price: float, filled_price: float,
                      direction: str) -> float:
    """计算滑点（基点）。direction: 'long' or 'short'。"""
    if target_price <= 0:
        return 0.0
    if direction == "long":
        slip = (filled_price - target_price) / target_price
    else:
        slip = (target_price - filled_price) / target_price
    return round(slip * 10000, 4)
