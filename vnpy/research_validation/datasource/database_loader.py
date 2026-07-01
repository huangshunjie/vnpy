"""
research_validation/datasource/database_loader.py

DatabaseLoader — 只读数据接口 stub（Phase 1）。

强制只使用 VeighNa DatabaseManager 读取数据。
❌ 不允许 SQL 实现（Phase 1）。
❌ 不允许连接 CTP 或任何交易接口。
"""

from __future__ import annotations

from datetime import datetime


class DatabaseLoader:
    """
    只读数据加载接口（Phase 1 骨架）。

    Phase 2+ 对接 VeighNa DatabaseManager 实现具体加载逻辑。
    所有方法当前为 stub，调用时直接抛出 NotImplementedError。
    """

    def load_factor_data(
        self,
        factor_name: str,
        start_date:  datetime,
        end_date:    datetime,
        symbols:     list[str] | None = None,
    ):
        """
        从 Factor Research Engine 加载因子值截面数据。

        Returns
        -------
        Phase 2+: dict[date, dict[symbol, float]]
        """
        raise NotImplementedError("Phase 2 实现：对接 Factor Research Engine。")

    def load_price_data(
        self,
        symbols:    list[str],
        start_date: datetime,
        end_date:   datetime,
        interval:   str = "d",
    ):
        """
        从 VeighNa DatabaseManager 加载历史价格数据。

        Returns
        -------
        Phase 2+: dict[symbol, list[BarData]]
        """
        raise NotImplementedError("Phase 2 实现：对接 VeighNa DatabaseManager。")

    def load_portfolio_data(
        self,
        start_date: datetime,
        end_date:   datetime,
    ):
        """
        从 Portfolio Engine 加载历史组合净值数据。

        Returns
        -------
        Phase 2+: list[dict]  净值时间序列
        """
        raise NotImplementedError("Phase 2 实现：对接 Portfolio Engine。")
