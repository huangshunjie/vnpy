"""
execution_engine/utils/time_utils.py

时间与延迟工具函数（Phase 4）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


def now_ms() -> float:
    """返回当前时间的毫秒时间戳。"""
    return datetime.now().timestamp() * 1000.0


def elapsed_ms(start: datetime, end: Optional[datetime] = None) -> float:
    """计算两个时间点之间的毫秒差。"""
    if end is None:
        end = datetime.now()
    return (end - start).total_seconds() * 1000.0


def simulate_execution_delay(
    base_ms:    float = 50.0,
    jitter_ms:  float = 20.0,
    seed:       Optional[int] = None,
) -> timedelta:
    """
    模拟执行延迟（固定基础延迟 + 随机抖动）。

    Parameters
    ----------
    base_ms   : 基础延迟（毫秒）
    jitter_ms : 随机抖动范围（±jitter_ms）
    seed      : 随机种子（回测可复现）

    Returns
    -------
    timedelta  模拟延迟
    """
    import random
    rng = random.Random(seed)
    delay = base_ms + rng.uniform(-jitter_ms, jitter_ms)
    return timedelta(milliseconds=max(delay, 0.0))


def is_trading_hour(dt: Optional[datetime] = None) -> bool:
    """
    简单判断是否在国内期货主要交易时段（不含夜盘）。

    仅用于信号过滤，不作为交易系统的权威时段判断。
    """
    if dt is None:
        dt = datetime.now()
    weekday = dt.weekday()   # 0=Monday, 4=Friday
    if weekday >= 5:          # 周末
        return False
    hour, minute = dt.hour, dt.minute
    # 日盘：09:00 - 11:30  /  13:30 - 15:00
    morning   = (9, 0)  <= (hour, minute) <= (11, 30)
    afternoon = (13, 30) <= (hour, minute) <= (15, 0)
    return morning or afternoon


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化 datetime 为字符串。"""
    return dt.strftime(fmt)


def parse_datetime(s: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """解析字符串为 datetime。"""
    return datetime.strptime(s, fmt)
