"""
research_ops/utils/version.py

语义版本工具：生成、解析、比较、递增。
格式：v{major}.{minor}.{patch}
"""
from __future__ import annotations
import re
from typing import Tuple

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse(version: str) -> Tuple[int, int, int]:
    """
    解析版本字符串，返回 (major, minor, patch)。
    支持 "v1.2.3" 和 "1.2.3" 两种格式。
    """
    m = _VERSION_RE.match(version.strip())
    if not m:
        raise ValueError(f"Invalid version string: '{version}'")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def fmt(major: int, minor: int, patch: int) -> str:
    return f"v{major}.{minor}.{patch}"


def bump_major(version: str) -> str:
    major, _, _ = parse(version)
    return fmt(major + 1, 0, 0)


def bump_minor(version: str) -> str:
    major, minor, _ = parse(version)
    return fmt(major, minor + 1, 0)


def bump_patch(version: str) -> str:
    major, minor, patch = parse(version)
    return fmt(major, minor, patch + 1)


def compare(v1: str, v2: str) -> int:
    """
    比较两个版本。
    返回 -1 (v1 < v2) / 0 (相等) / 1 (v1 > v2)。
    """
    t1 = parse(v1)
    t2 = parse(v2)
    if t1 < t2:
        return -1
    if t1 > t2:
        return 1
    return 0


def is_valid(version: str) -> bool:
    try:
        parse(version)
        return True
    except ValueError:
        return False


def latest(versions: list[str]) -> str:
    """从列表中返回最大版本号字符串。"""
    if not versions:
        raise ValueError("Empty version list")
    return max(versions, key=parse)


def initial() -> str:
    """返回初始版本 v1.0.0。"""
    return "v1.0.0"
