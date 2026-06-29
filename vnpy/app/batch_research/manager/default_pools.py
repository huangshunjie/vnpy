"""
manager/default_pools.py

Default stock pool definitions and online-update interface.

Responsibilities:
  - Declare built-in seed pools (shown on first launch)
  - Provide OnlineUpdater interface for future Tushare / AkShare updates
  - Keep all pool data in one place so it is easy to maintain

Design rules:
  - No Qt dependency
  - No network calls in this module (OnlineUpdater is a skeleton)
  - seed_pools() is idempotent: safe to call every startup
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Seed pool definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DefaultPoolDef:
    """Immutable definition of one built-in default pool."""

    name:        str
    symbols:     tuple[str, ...]
    description: str = ""


# Symbols use full vt_symbol format so no exchange inference is needed.
# These are example / demo pools; users can edit or delete them freely.
_DEFAULT_POOLS: list[DefaultPoolDef] = [
    DefaultPoolDef(
        name="示例：汪深蓝笹",
        description="汪深大盘蓝笹示例股票池，可自行编辑或删除",
        symbols=(
            "600519.SSE",   # 贵州茅台
            "000858.SZSE",  # 五粮液
            "600036.SSE",   # 招商银行
            "000001.SZSE",  # 平安银行
            "600900.SSE",   # 长江电力
            "601318.SSE",   # 中国平安
            "600276.SSE",   # 恒瑞医药
            "002594.SZSE",  # 比亚迪
            "300750.SZSE",  # 宁德时代
            "601166.SSE",   # 兴业银行
        ),
    ),
    DefaultPoolDef(
        name="示例：科创板样本",
        description="科创板示例股票池，可自行编辑或删除",
        symbols=(
            "688599.SSE",   # 天窞落地
            "688041.SSE",   # 海光电子
            "688036.SSE",   # 传风科技
            "688012.SSE",   # 中微公司
            "688111.SSE",   # 金山办公
            "688169.SSE",   # 第一元素
            "688303.SSE",   # 大全张盘
            "688047.SSE",   # 存储机器人
            "688561.SSE",   # 芝麻信息
            "688772.SSE",   # u计算机
        ),
    ),
    DefaultPoolDef(
        name="示例：创业板50",
        description="创业板示例股票池，可自行编辑或删除",
        symbols=(
            "300750.SZSE",  # 宁德时代
            "300015.SZSE",  # 爱尔眼科
            "300059.SZSE",  # 东方财富
            "300122.SZSE",  # 智飞健康
            "300142.SZSE",  # 沃森股份
            "300274.SZSE",  # 阳光电源
            "300496.SZSE",  # 迪蒂数据
            "300760.SZSE",  # 迟炽山
            "301155.SZSE",  # 普报悧
            "300999.SZSE",  # 金龙鱼
        ),
    ),
]


def get_default_pool_defs() -> list[DefaultPoolDef]:
    """Return the full list of built-in default pool definitions."""
    return list(_DEFAULT_POOLS)


# ---------------------------------------------------------------------------
# OnlineUpdater interface (skeleton for future Tushare / AkShare support)
# ---------------------------------------------------------------------------

@runtime_checkable
class OnlineUpdater(Protocol):
    """
    Interface for providers that can fetch up-to-date symbol lists.

    Future implementations:
      - TushareUpdater   (requires tushare token)
      - AkShareUpdater   (no token needed)

    Each implementation must be stateless or manage its own state.
    StockPoolManager calls fetch() and stores the result; it never
    calls network code directly.
    """

    def fetch(self, pool_name: str) -> list[str]:
        """
        Fetch a fresh vt_symbol list for *pool_name*.

        :param pool_name: One of the names returned by supported_pools().
        :return:          List of vt_symbol strings.
        :raises NotImplementedError: If pool_name is not supported.
        :raises RuntimeError:        If network call fails.
        """
        ...

    def supported_pools(self) -> list[str]:
        """Return the list of pool names this updater can refresh."""
        ...


class _StubUpdater:
    """
    Stub implementation of OnlineUpdater.

    Returns an empty list for all pools and logs a warning.
    Used as a safe default when no real updater is configured.
    """

    def fetch(self, pool_name: str) -> list[str]:
        import logging
        logging.getLogger(__name__).warning(
            "OnlineUpdater not configured; cannot fetch pool %r", pool_name
        )
        return []

    def supported_pools(self) -> list[str]:
        return []


# Module-level default updater (replaced by callers that inject a real one)
DEFAULT_UPDATER: _StubUpdater = _StubUpdater()
