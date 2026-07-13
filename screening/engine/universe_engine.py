"""
screening/engine/universe_engine.py

Universe Manager — 股票池管理引擎（Phase 2）。

实现：
  - 加载市场成分股（全A / 沪深300 / 中证500 / 中证1000 / 自定义）
  - 应用基础过滤规则（ST / 停牌 / 上市天数 / 日均成交额 / 市值）
  - 优先对接 vnpy DatabaseManager，无数据时 fallback 到内置静态数据
  - 输出 UniverseData，发布 EVENT_UNIVERSE_UPDATED 事件
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

from ..constant import MarketUniverse, UniverseFilter
from ..model.universe import UniverseConfig, UniverseData, UniverseFilterRule

_DATA_DIR = Path(__file__).parent.parent / "data"
_INDEX_FILE = _DATA_DIR / "index_members.json"

_MARKET_KEY: Dict[MarketUniverse, str] = {
    MarketUniverse.CSI_300:  "csi_300",
    MarketUniverse.CSI_500:  "csi_500",
    MarketUniverse.CSI_1000: "csi_1000",
}


def _load_static_index(key: str) -> List[str]:
    """从内置 JSON 文件加载指数成分股。"""
    try:
        with open(_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        symbols = data.get(key, [])
        return [s for s in symbols if s and "播" not in s]
    except Exception:
        return []


def _load_all_a_from_db(main_engine: Any = None) -> List[str]:
    """
    从 DatabaseManager 获取全市场 A 股股票代码。
    若无数据库连接则返回空列表。
    """
    if main_engine is None:
        return []
    try:
        db = main_engine.get_database()
        if db is None:
            return []
        contracts = main_engine.get_all_contracts()
        symbols = []
        for c in contracts:
            code = c.symbol
            exch = str(c.exchange.value) if hasattr(c.exchange, "value") else str(c.exchange)
            if exch in ("SSE", "SZSE"):
                symbols.append(f"{code}.{exch}")
        return symbols
    except Exception:
        return []


def _is_st(symbol: str, main_engine: Any = None) -> bool:
    """简单判断：通过合约名称检测 ST / *ST。"""
    if main_engine is None:
        return False
    try:
        code = symbol.split(".")[0]
        contract = main_engine.get_contract(symbol)
        if contract and contract.name:
            name = contract.name.upper()
            return "ST" in name
    except Exception:
        pass
    return False


def _get_listing_days(symbol: str, main_engine: Any = None) -> float:
    """获取上市天数（近似值）。"""
    if main_engine is None:
        return 9999.0
    try:
        contract = main_engine.get_contract(symbol)
        if contract and hasattr(contract, "list_date") and contract.list_date:
            delta = datetime.now() - contract.list_date
            return float(delta.days)
    except Exception:
        pass
    return 9999.0


class UniverseEngine:
    """
    股票池管理引擎（Phase 2 完整实现）。

    职责：
      1. 根据 UniverseConfig 加载对应市场的股票列表
      2. 应用基础过滤规则，输出合法的 UniverseData
      3. 支持自定义股票池
      4. 优先对接 MainEngine / DatabaseManager；无数据时 fallback 静态数据
    """

    def __init__(
        self,
        log_fn: Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
    ) -> None:
        self._log = log_fn or print
        self._main_engine = main_engine
        self._config: UniverseConfig = UniverseConfig.default()
        self._universe: Optional[UniverseData] = None

    # ── 配置 ─────────────────────────────────────────────────────────

    def set_config(self, config: UniverseConfig) -> None:
        self._config = config

    def get_config(self) -> UniverseConfig:
        return self._config

    def set_main_engine(self, main_engine: Any) -> None:
        self._main_engine = main_engine

    # ── 主接口 ────────────────────────────────────────────────────────

    def build_universe(self) -> Optional[UniverseData]:
        """
        根据当前配置构建股票池：
          1. 加载市场成分股
          2. 应用基础过滤规则
          3. 返回 UniverseData
        """
        self._log(f"[UniverseEngine] 开始构建股票池：{self._config.market.value}")
        t0 = datetime.now()

        raw_symbols = self._load_symbols()
        total_before = len(raw_symbols)
        self._log(f"[UniverseEngine] 原始股票数量：{total_before}")

        filtered = self._apply_filters(raw_symbols)
        total_after = len(filtered)
        self._log(f"[UniverseEngine] 过滤后股票数量：{total_after}")

        self._universe = UniverseData(
            config=self._config,
            symbols=filtered,
            total_before_filter=total_before,
            total_after_filter=total_after,
            generated_at=datetime.now(),
        )
        elapsed = (datetime.now() - t0).total_seconds()
        self._log(f"[UniverseEngine] 股票池构建完成，耗时 {elapsed:.2f}s")
        return self._universe

    def get_universe(self) -> Optional[UniverseData]:
        return self._universe

    def get_symbols(self) -> List[str]:
        if self._universe:
            return list(self._universe.symbols)
        return []

    # ── 数据加载 ──────────────────────────────────────────────────────

    def _load_symbols(self) -> List[str]:
        """根据市场配置加载初始股票列表。"""
        market = self._config.market

        if market == MarketUniverse.CUSTOM:
            symbols = list(self._config.custom_symbols)
            self._log(f"[UniverseEngine] 自定义股票池：{len(symbols)} 只")
            return symbols

        if market == MarketUniverse.ALL_A:
            symbols = _load_all_a_from_db(self._main_engine)
            if not symbols:
                self._log("[UniverseEngine] 数据库无全A数据，使用沪深300静态数据作为 fallback")
                symbols = _load_static_index("csi_300")
            return symbols

        key = _MARKET_KEY.get(market, "csi_300")
        symbols = _load_static_index(key)
        if symbols:
            self._log(f"[UniverseEngine] 从静态数据加载 {market.value}：{len(symbols)} 只")
        else:
            self._log(f"[UniverseEngine] 静态数据为空，market={market.value}")
        return symbols

    def get_market_symbols(self, market: str) -> List[str]:
        """获取指定市场指数的成分股（外部查询接口）。"""
        try:
            m = MarketUniverse(market)
        except ValueError:
            return []
        if m == MarketUniverse.ALL_A:
            return _load_all_a_from_db(self._main_engine)
        key = _MARKET_KEY.get(m, "")
        return _load_static_index(key) if key else []

    # ── 过滤规则 ──────────────────────────────────────────────────────

    def _apply_filters(self, symbols: List[str]) -> List[str]:
        """对股票列表依次应用所有启用的过滤规则。"""
        result = list(symbols)
        for rule in self._config.filter_rules:
            if not rule.enabled:
                continue
            before = len(result)
            result = self._apply_single_filter(result, rule)
            removed = before - len(result)
            if removed > 0:
                self._log(
                    f"[UniverseEngine] 过滤规则 {rule.filter_type.value}："
                    f"移除 {removed} 只，剩余 {len(result)} 只"
                )
        return result

    def apply_filters(self, symbols: List[str]) -> List[str]:
        """公开接口：对外部传入的股票列表应用过滤规则。"""
        return self._apply_filters(symbols)

    def _apply_single_filter(
        self, symbols: List[str], rule: UniverseFilterRule
    ) -> List[str]:
        ft = rule.filter_type

        if ft == UniverseFilter.EXCLUDE_ST:
            return self._filter_exclude_st(symbols)

        if ft == UniverseFilter.EXCLUDE_SUSPENDED:
            return self._filter_exclude_suspended(symbols)

        if ft == UniverseFilter.EXCLUDE_DELISTING:
            return self._filter_exclude_delisting(symbols)

        if ft == UniverseFilter.MIN_LISTING_DAYS:
            return self._filter_min_listing_days(symbols, int(rule.value))

        if ft == UniverseFilter.MIN_DAILY_TURNOVER:
            return self._filter_min_turnover(symbols, rule.value)

        if ft == UniverseFilter.MIN_MARKET_CAP:
            return self._filter_min_market_cap(symbols, rule.value)

        return list(symbols)

    def _filter_exclude_st(self, symbols: List[str]) -> List[str]:
        """排除名称含 ST / *ST 的股票。"""
        result = []
        for s in symbols:
            if _is_st(s, self._main_engine):
                continue
            code = s.split(".")[0]
            if code.startswith("ST") or code.startswith("*ST"):
                continue
            result.append(s)
        return result

    def _filter_exclude_suspended(self, symbols: List[str]) -> List[str]:
        """
        排除停牌股票。
        若无 MainEngine 数据则跳过此过滤（保留全部）。
        """
        if self._main_engine is None:
            return list(symbols)
        result = []
        for s in symbols:
            try:
                tick = self._main_engine.get_tick(s)
                if tick is not None and tick.volume == 0:
                    continue
            except Exception:
                pass
            result.append(s)
        return result

    def _filter_exclude_delisting(self, symbols: List[str]) -> List[str]:
        """
        排除退市整理股票（代码规律：SZSE 以 2、3 开头的特殊代码段）。
        若无数据则跳过。
        """
        if self._main_engine is None:
            return list(symbols)
        result = []
        for s in symbols:
            try:
                contract = self._main_engine.get_contract(s)
                if contract is None:
                    result.append(s)
                    continue
                name = getattr(contract, "name", "") or ""
                if "退" in name or "摘牌" in name:
                    continue
            except Exception:
                pass
            result.append(s)
        return result

    def _filter_min_listing_days(self, symbols: List[str], min_days: int) -> List[str]:
        """排除上市天数不足的股票。"""
        if self._main_engine is None:
            return list(symbols)
        result = []
        for s in symbols:
            days = _get_listing_days(s, self._main_engine)
            if days >= min_days:
                result.append(s)
        return result

    def _filter_min_turnover(self, symbols: List[str], min_turnover: float) -> List[str]:
        """
        排除日均成交额不足的股票。
        Phase 2 中若无数据则跳过此过滤。
        """
        if self._main_engine is None:
            return list(symbols)
        result = []
        for s in symbols:
            try:
                tick = self._main_engine.get_tick(s)
                if tick is not None:
                    turnover = getattr(tick, "turnover", None)
                    if turnover is not None and turnover < min_turnover:
                        continue
            except Exception:
                pass
            result.append(s)
        return result

    def _filter_min_market_cap(self, symbols: List[str], min_cap: float) -> List[str]:
        """
        排除市值不足的股票。
        Phase 2 中若无数据则跳过此过滤。
        """
        return list(symbols)

    # ── 摘要 ──────────────────────────────────────────────────────────

    def summary(self) -> dict:
        if self._universe:
            return {
                "market": self._universe.config.market.value,
                "total_before_filter": self._universe.total_before_filter,
                "total_after_filter": self._universe.total_after_filter,
                "generated_at": str(self._universe.generated_at)[:19],
            }
        return {"status": "not_built"}
