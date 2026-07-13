"""
StockPool

A 股股票池管理模块。

支持模式：
  - ALL_A       全部A股（沪深京三所）
  - HS300       沪深300成分股
  - ZZ500       中证500成分股
  - CYB         创业板（SZSE 30xxxx）
  - STAR        科创板（SSE  68xxxx）
  - CUSTOM      用户自定义列表

过滤器（可叠加）：
  - exclude_st          过滤 ST / *ST
  - exclude_suspended   过滤停牌（需外部提供停牌集合）
  - min_listed_days     过滤上市不足 N 天的次新股
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Sequence


class PoolType(Enum):
    """预设股票池类型。"""
    ALL_A   = "all_a"
    HS300   = "hs300"
    ZZ500   = "zz500"
    CYB     = "cyb"
    STAR    = "star"
    CUSTOM  = "custom"


# ---------- 内置板块前缀规则 ----------
# 沪市：SSE  — 60xxxx 主板, 68xxxx 科创板, 000xxx 指数
# 深市：SZSE — 000xxx/001xxx 主板, 002xxx/003xxx 中小板, 300xxx/301xxx 创业板
# 京市：BSE  — 8xxxxx / 4xxxxx

_CYB_PREFIXES  = ("300", "301")          # 创业板
_STAR_PREFIXES = ("688", "689")          # 科创板
_SSE_PREFIXES  = ("60",)                 # 沪市主板
_SZSE_MAIN     = ("000", "001", "002", "003")  # 深市主板+中小板
_BSE_PREFIXES  = ("8", "4")             # 北交所


def _exchange_of(symbol: str) -> str:
    """根据股票代码前缀推断交易所（SSE / SZSE / BSE）。"""
    if symbol.startswith(("60", "68", "689")):
        return "SSE"
    if symbol.startswith(("00", "002", "003", "300", "301")):
        return "SZSE"
    if symbol.startswith(("8", "4")):
        return "BSE"
    return "SSE"


def _to_vt_symbol(symbol: str) -> str:
    """将纯代码转换为 vt_symbol，例如 '000001' → '000001.SZSE'。"""
    return f"{symbol}.{_exchange_of(symbol)}"


@dataclass
class StockMeta:
    """单只股票的元信息，用于过滤决策。"""
    vt_symbol: str
    name: str = ""
    listed_date: date | None = None
    is_st: bool = False
    is_suspended: bool = False

    @property
    def symbol(self) -> str:
        return self.vt_symbol.split(".")[0]

    @property
    def exchange(self) -> str:
        return self.vt_symbol.split(".")[1]


@dataclass
class StockPool:
    """
    股票池管理器。

    典型用法::

        # 内置预设池
        pool = StockPool(pool_type=PoolType.CYB)
        symbols = pool.get_symbols()

        # 自定义列表（直接传纯代码，自动补交易所）
        pool = StockPool(
            pool_type=PoolType.CUSTOM,
            custom_symbols=["000001", "600519", "300750"],
        )

        # 带过滤器
        pool = StockPool(
            pool_type=PoolType.ALL_A,
            exclude_st=True,
            min_listed_days=365,
            meta_list=[...],   # 提供元信息时才能做 ST / 上市天数过滤
        )
        symbols = pool.get_symbols(as_of=date(2023, 12, 31))
    """

    pool_type: PoolType = PoolType.CUSTOM

    # CUSTOM 模式下的原始代码列表（纯代码或 vt_symbol 均可）
    custom_symbols: list[str] = field(default_factory=list)

    # HS300 / ZZ500 成分股列表（外部注入，例如从 CSV 读取）
    hs300_symbols: list[str] = field(default_factory=list)
    zz500_symbols: list[str] = field(default_factory=list)

    # 可选元信息列表，用于 ST / 停牌 / 上市天数过滤
    meta_list: list[StockMeta] = field(default_factory=list)

    # ---------- 过滤开关 ----------
    exclude_st: bool = False
    exclude_suspended: bool = False
    min_listed_days: int = 0          # 0 = 不过滤

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def get_symbols(self, as_of: date | None = None) -> list[str]:
        """
        返回过滤后的 vt_symbol 列表。

        :param as_of: 参考日期，用于计算上市天数（None 时使用今天）。
        :return: 去重、排序后的 vt_symbol 列表。
        """
        raw = self._get_raw_symbols()
        normalized = [self._normalize(s) for s in raw]

        if not self.meta_list:
            return sorted(set(normalized))

        meta_index = {m.vt_symbol: m for m in self.meta_list}
        ref_date = as_of or date.today()
        result: list[str] = []

        for vt_symbol in normalized:
            meta = meta_index.get(vt_symbol)
            if meta is None:
                result.append(vt_symbol)
                continue
            if not self._passes_filters(meta, ref_date):
                continue
            result.append(vt_symbol)

        return sorted(set(result))

    def size(self, as_of: date | None = None) -> int:
        """返回过滤后股票池大小。"""
        return len(self.get_symbols(as_of))

    def add_symbols(self, symbols: Sequence[str]) -> None:
        """向自定义列表追加股票（仅 CUSTOM 模式有效）。"""
        self.custom_symbols.extend(symbols)

    def remove_symbol(self, symbol: str) -> None:
        """从自定义列表移除一只股票（支持纯代码或 vt_symbol）。"""
        vt = self._normalize(symbol)
        self.custom_symbols = [
            s for s in self.custom_symbols
            if self._normalize(s) != vt
        ]

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _get_raw_symbols(self) -> list[str]:
        """根据 pool_type 获取未过滤的原始代码列表。"""
        if self.pool_type == PoolType.CUSTOM:
            return list(self.custom_symbols)

        if self.pool_type == PoolType.HS300:
            return list(self.hs300_symbols)

        if self.pool_type == PoolType.ZZ500:
            return list(self.zz500_symbols)

        if self.pool_type == PoolType.CYB:
            return self._cyb_symbols()

        if self.pool_type == PoolType.STAR:
            return self._star_symbols()

        if self.pool_type == PoolType.ALL_A:
            return self._all_a_symbols()

        return []

    def _cyb_symbols(self) -> list[str]:
        """
        创业板：从 meta_list 中筛选前缀符合的股票。
        若未提供 meta_list，返回空列表并给出提示。
        """
        if not self.meta_list:
            return []
        return [
            m.vt_symbol for m in self.meta_list
            if m.symbol.startswith(_CYB_PREFIXES)
        ]

    def _star_symbols(self) -> list[str]:
        """科创板：从 meta_list 中筛选。"""
        if not self.meta_list:
            return []
        return [
            m.vt_symbol for m in self.meta_list
            if m.symbol.startswith(_STAR_PREFIXES)
        ]

    def _all_a_symbols(self) -> list[str]:
        """全部A股：从 meta_list 中取所有条目。"""
        if not self.meta_list:
            return []
        return [m.vt_symbol for m in self.meta_list]

    def _passes_filters(self, meta: StockMeta, ref_date: date) -> bool:
        """判断单只股票是否通过所有过滤条件。"""
        if self.exclude_st and meta.is_st:
            return False
        if self.exclude_suspended and meta.is_suspended:
            return False
        if self.min_listed_days > 0 and meta.listed_date is not None:
            listed_days = (ref_date - meta.listed_date).days
            if listed_days < self.min_listed_days:
                return False
        return True

    @staticmethod
    def _normalize(symbol: str) -> str:
        """
        将纯代码或 vt_symbol 统一转换为 'symbol.EXCHANGE' 格式。
        已包含 '.' 的视为 vt_symbol，直接返回。
        """
        if "." in symbol:
            return symbol
        return _to_vt_symbol(symbol)

    # ------------------------------------------------------------------ #
    #  工厂方法
    # ------------------------------------------------------------------ #

    @classmethod
    def from_symbols(cls, symbols: Sequence[str], **kwargs) -> "StockPool":
        """从代码列表快速创建自定义股票池。"""
        return cls(
            pool_type=PoolType.CUSTOM,
            custom_symbols=list(symbols),
            **kwargs,
        )

    @classmethod
    def from_hs300(cls, symbols: Sequence[str], **kwargs) -> "StockPool":
        """从沪深300成分股列表创建股票池。"""
        return cls(
            pool_type=PoolType.HS300,
            hs300_symbols=list(symbols),
            **kwargs,
        )

    @classmethod
    def from_zz500(cls, symbols: Sequence[str], **kwargs) -> "StockPool":
        """从中证500成分股列表创建股票池。"""
        return cls(
            pool_type=PoolType.ZZ500,
            zz500_symbols=list(symbols),
            **kwargs,
        )

    def __repr__(self) -> str:
        return (
            f"StockPool(type={self.pool_type.value}, "
            f"exclude_st={self.exclude_st}, "
            f"min_listed_days={self.min_listed_days})"
        )
