"""
alpha_factory_2/datasource/factor_loader.py

FactorLoader — 因子数据加载器（Phase 2 升级）。

Phase 2 提供：
  - 内置模拟因子列表（用于开发/测试，不连接外部数据源）
  - 批量加载接口
  - 从 VeighNa DatabaseManager 加载的接口骨架（Phase 3 实际接入）

❌ 不连接外部数据源
✔  使用模拟数据 + DatabaseManager 接口占位
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
#  内置模拟因子库（Phase 2 开发用）
# ─────────────────────────────────────────────────────────────────────────────

BUILTIN_FACTORS: list[str] = [
    # 价格动量类
    "MOM_1D", "MOM_5D", "MOM_10D", "MOM_20D", "MOM_60D",
    # 反转类
    "REV_1D", "REV_5D", "REV_10D",
    # 波动率类
    "VOL_5D", "VOL_10D", "VOL_20D", "VOL_60D",
    # 成交量类
    "TVOL_5D", "TVOL_10D", "TVOL_20D",
    # 技术指标类
    "RSI_14", "RSI_28", "MACD_SIGNAL", "MACD_HIST",
    "BB_WIDTH", "BB_POSITION",
    # 基本面代理（模拟）
    "PE_RANK", "PB_RANK", "ROE_RANK", "EPS_SURPRISE",
    # 资金流类
    "NETFLOW_5D", "NETFLOW_10D", "LARGE_ORDER_RATIO",
    # 市场微结构
    "ILLIQ_5D", "BID_ASK_SPREAD", "AMIHUD_5D",
]


@dataclass
class FactorData:
    """因子数据容器。"""
    factor_name: str
    symbol:      str         = ""
    values:      list[float] = field(default_factory=list)
    dates:       list[str]   = field(default_factory=list)
    loaded_at:   datetime    = field(default_factory=datetime.now)

    @property
    def length(self) -> int:
        return len(self.values)

    def to_dict(self) -> dict:
        return {
            "factor_name": self.factor_name,
            "symbol":      self.symbol,
            "length":      self.length,
            "loaded_at":   str(self.loaded_at)[:19],
        }


class FactorLoader:
    """
    因子数据加载器（Phase 2）。

    Phase 2: 提供内置模拟数据，支持 list / load / batch_load。
    Phase 3: 实际接入 vnpy.trader.database.get_database()。
    """

    def __init__(
        self,
        use_builtin: bool = True,
        n_bars:      int  = 240,   # 模拟数据长度（交易日数）
        seed:        int  = 42,
    ) -> None:
        self._use_builtin = use_builtin
        self._n_bars      = n_bars
        self._seed        = seed
        self._cache: dict[str, FactorData] = {}

    # ------------------------------------------------------------------ #
    #  因子列表
    # ------------------------------------------------------------------ #

    def list_available_factors(self) -> list[str]:
        """列出可用因子名称。"""
        if self._use_builtin:
            return list(BUILTIN_FACTORS)
        # Phase 3: 从 DatabaseManager 查询
        return []

    # ------------------------------------------------------------------ #
    #  单因子加载
    # ------------------------------------------------------------------ #

    def load_factor(
        self,
        factor_name: str,
        symbol:      str = "",
    ) -> FactorData:
        """
        加载指定因子数据。

        Phase 2: 使用正态随机模拟数据（可复现）。
        Phase 3: 从 DatabaseManager 读取真实数据。
        """
        cache_key = f"{factor_name}:{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._use_builtin:
            data = self._simulate(factor_name, symbol)
        else:
            data = FactorData(factor_name=factor_name, symbol=symbol)

        self._cache[cache_key] = data
        return data

    # ------------------------------------------------------------------ #
    #  批量加载
    # ------------------------------------------------------------------ #

    def batch_load(
        self,
        factor_names: list[str],
        symbol:       str = "",
    ) -> dict[str, FactorData]:
        """
        批量加载多个因子数据。

        Returns
        -------
        dict[factor_name, FactorData]
        """
        return {
            name: self.load_factor(name, symbol)
            for name in factor_names
        }

    def clear_cache(self) -> None:
        self._cache.clear()

    # ------------------------------------------------------------------ #
    #  模拟数据生成
    # ------------------------------------------------------------------ #

    def _simulate(self, factor_name: str, symbol: str) -> FactorData:
        """
        生成可复现的正态模拟因子序列。

        使用因子名称和 symbol 作为种子偏移，
        保证同名因子每次加载结果相同。
        """
        name_hash = sum(ord(c) for c in factor_name + symbol)
        rng       = random.Random(self._seed + name_hash)

        values = [rng.gauss(0.0, 1.0) for _ in range(self._n_bars)]
        # 归一化至 [-3, 3] 区间
        mu  = sum(values) / len(values)
        std = (sum((v - mu) ** 2 for v in values) / len(values)) ** 0.5
        if std > 0:
            values = [(v - mu) / std for v in values]

        from datetime import date, timedelta
        base = date(2023, 1, 3)
        dates = [str(base + timedelta(days=i)) for i in range(self._n_bars)]

        return FactorData(
            factor_name = factor_name,
            symbol      = symbol,
            values      = values,
            dates       = dates,
        )
