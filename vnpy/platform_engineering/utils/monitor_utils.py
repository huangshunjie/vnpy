"""
platform_engineering/utils/monitor_utils.py
系统资源采集工具。
"""
from __future__ import annotations
from typing import Dict


def get_system_metrics() -> Dict[str, float]:
    """采集 CPU/内存使用率，无 psutil 时返回 0。"""
    try:
        import psutil
        return {
            "cpu_pct": psutil.cpu_percent(interval=None),
            "mem_pct": psutil.virtual_memory().percent,
            "disk_pct": psutil.disk_usage("/").percent,
        }
    except Exception:
        return {"cpu_pct": 0.0, "mem_pct": 0.0, "disk_pct": 0.0}


def format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def health_color(score: float) -> str:
    if score >= 80:
        return "#52c41a"
    if score >= 50:
        return "#faad14"
    return "#ff4d4f"
