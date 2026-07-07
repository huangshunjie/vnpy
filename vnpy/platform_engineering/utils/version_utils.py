"""
platform_engineering/utils/version_utils.py
版本号工具。
"""
from __future__ import annotations
import re


def bump_version(tag: str, part: str = "patch") -> str:
    """
    将版本标签中的指定部分 +1。
    例如 bump_version('v1.2.3', 'minor') -> 'v1.3.0'
    """
    prefix = ""
    clean  = tag
    if tag.startswith("v") or tag.startswith("V"):
        prefix = tag[0]
        clean  = tag[1:]

    parts = clean.split(".")
    while len(parts) < 3:
        parts.append("0")

    idx = {"major": 0, "minor": 1, "patch": 2}.get(part, 2)
    try:
        parts[idx] = str(int(parts[idx]) + 1)
    except ValueError:
        parts[idx] = "1"

    for i in range(idx + 1, 3):
        parts[i] = "0"

    return prefix + ".".join(parts)


def is_valid_version(tag: str) -> bool:
    """检查是否为 semver 格式（可带 'v' 前缀）。"""
    pattern = r"^[vV]?\d+\.\d+\.\d+$"
    return bool(re.match(pattern, tag))


def compare_versions(a: str, b: str) -> int:
    """比较版本大小：返回 -1 / 0 / 1。"""
    def _to_tuple(v: str):
        v = v.lstrip("vV")
        parts = v.split(".")
        try:
            return tuple(int(p) for p in parts[:3])
        except ValueError:
            return (0, 0, 0)

    ta, tb = _to_tuple(a), _to_tuple(b)
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0


def generate_version_tag(prefix: str = "v", base: int = 1) -> str:
    """生成带时间戳的版本标签，例如 'v1.20240707.001'。"""
    from datetime import datetime
    now = datetime.now()
    return f"{prefix}{base}.{now.strftime('%Y%m%d')}.001"
