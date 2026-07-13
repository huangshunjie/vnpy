"""
risk_engine_2/datasource/database_loader.py

RiskDatabaseLoader — 风控数据接口 stub（Phase 1）。

所有数据必须来自 VeighNa DatabaseManager + Portfolio Engine + Execution Engine。
Phase 1 仅定义接口签名，禁止任何 SQL 实现。
Phase 2+ 按需填充具体实现。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class RiskDatabaseLoader:
    """
    风控系统数据加载接口。

    Phase 1 : 全部为 stub，返回空结构。
    Phase 2+: 接入 vnpy.trader.database 实现。
    """

    def __init__(self) -> None:
        # Phase 2+: self._db = get_database()
        pass

    # ------------------------------------------------------------------ #
    #  接口 1：Portfolio 数据
    # ------------------------------------------------------------------ #

    def load_portfolio_data(
        self,
        start: datetime | None = None,
        end:   datetime | None = None,
    ) -> dict[str, Any]:
        """
        从 Portfolio Engine 加载组合持仓与权重数据。

        Returns（Phase 2+ 实现后）
        -------
        {
          "positions": list[dict],   # 各标的持仓
          "weights":   dict[str, float],  # 各标的权重
          "nav":       float,         # 组合总净值
          "timestamp": datetime,
        }

        Phase 1: 返回空结构。
        """
        return {
            "positions": [],
            "weights":   {},
            "nav":       0.0,
            "timestamp": datetime.now(),
        }

    # ------------------------------------------------------------------ #
    #  接口 2：Execution 数据
    # ------------------------------------------------------------------ #

    def load_execution_data(
        self,
        start: datetime | None = None,
        end:   datetime | None = None,
    ) -> dict[str, Any]:
        """
        从 Execution Engine 加载历史执行记录与成交数据。

        Returns（Phase 2+ 实现后）
        -------
        {
          "orders":   list[dict],   # 历史订单
          "fills":    list[dict],   # 历史成交
          "pnl":      float,        # 累计 PnL
          "timestamp": datetime,
        }

        Phase 1: 返回空结构。
        """
        return {
            "orders":    [],
            "fills":     [],
            "pnl":       0.0,
            "timestamp": datetime.now(),
        }

    # ------------------------------------------------------------------ #
    #  接口 3：Factor 数据
    # ------------------------------------------------------------------ #

    def load_factor_data(
        self,
        factor_names: list[str] | None = None,
        start: datetime | None = None,
        end:   datetime | None = None,
    ) -> dict[str, Any]:
        """
        从 Factor Research Engine 加载因子暴露数据。

        Returns（Phase 2+ 实现后）
        -------
        {
          "exposures":  dict[str, float],  # factor_name -> portfolio exposure
          "ic_series":  dict[str, list],   # factor_name -> IC 时间序列
          "timestamp":  datetime,
        }

        Phase 1: 返回空结构。
        """
        return {
            "exposures":  {},
            "ic_series":  {},
            "timestamp":  datetime.now(),
        }

    # ------------------------------------------------------------------ #
    #  工具
    # ------------------------------------------------------------------ #

    @property
    def is_available(self) -> bool:
        """数据库连接是否可用（Phase 2+ 实现）。"""
        return False
