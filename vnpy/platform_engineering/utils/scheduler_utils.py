"""
platform_engineering/utils/scheduler_utils.py
Cron 解析 / 定时工具。
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional


def next_run_from_cron(cron_expr: str, after: Optional[datetime] = None) -> Optional[datetime]:
    """简单 Cron 解析：支持 '*/N' 和 固定值，5字段格式。
    返回 after 之后的下次运行时间，解析失败返回 None。
    """
    try:
        base = after or datetime.now()
        fields = cron_expr.strip().split()
        if len(fields) != 5:
            return None
        minute_f, hour_f, dom_f, month_f, dow_f = fields

        def _matches(f: str, val: int) -> bool:
            if f == "*":
                return True
            if f.startswith("*/"):
                step = int(f[2:])
                return val % step == 0
            try:
                return int(f) == val
            except ValueError:
                return False

        # brute-force next minute within 10 days
        candidate = base.replace(second=0, microsecond=0) + timedelta(minutes=1)
        for _ in range(14400):  # 14400 min = 10 days
            if (_matches(month_f, candidate.month) and
                    _matches(dom_f, candidate.day) and
                    _matches(dow_f, candidate.weekday()) and
                    _matches(hour_f, candidate.hour) and
                    _matches(minute_f, candidate.minute)):
                return candidate
            candidate += timedelta(minutes=1)
        return None
    except Exception:
        return None


def human_duration(seconds: float) -> str:
    """将秒数转为可读字符串，例如 '2h 15m 30s'。"""
    if seconds < 0:
        return "—"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)
