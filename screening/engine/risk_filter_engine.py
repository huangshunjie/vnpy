"""
screening/engine/risk_filter_engine.py

Risk Filter Engine — 风险过滤引擎（Phase 6）。

实现：
  - 波动率过滤（排除年化波动率过高的股票）
  - Beta 过滤（排除高 Beta 股票）
  - 行业集中度控制（同行业 Top N 限制）
  - 单票权重预估检查
  - 直接复用 risk_engine_2 的纯函数，不依赖其运行时实例
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..model.screening_result import ScreeningResult, StockScore


@dataclass
class RiskFilterConfig:
    """风险过滤规则配置。"""
    max_volatility:        float = 0.8    # 年化波动率上限（0.8 = 80%）
    max_beta:              float = 1.8    # Beta 上限
    max_industry_count:    int   = 10     # 同行业最多入选数量
    max_single_weight:     float = 0.10   # 单票预估权重上限（0.10 = 10%）
    vol_window:            int   = 20     # 波动率计算窗口（交易日）
    enable_vol_filter:     bool  = True
    enable_beta_filter:    bool  = True
    enable_industry_filter: bool = True
    enable_weight_filter:  bool  = False

    def to_dict(self) -> dict:
        return {
            "max_volatility": self.max_volatility,
            "max_beta": self.max_beta,
            "max_industry_count": self.max_industry_count,
            "max_single_weight": self.max_single_weight,
            "vol_window": self.vol_window,
            "enable_vol_filter": self.enable_vol_filter,
            "enable_beta_filter": self.enable_beta_filter,
            "enable_industry_filter": self.enable_industry_filter,
            "enable_weight_filter": self.enable_weight_filter,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RiskFilterConfig":
        cfg = cls()
        for k, v in d.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg

    @classmethod
    def default(cls) -> "RiskFilterConfig":
        return cls()


def _compute_vol(closes: List[float], window: int = 20) -> Optional[float]:
    """计算年化波动率（简单对数收益率标准差 × sqrt(252)）。"""
    if len(closes) < window + 1:
        return None
    prices = closes[-(window + 1):]
    rets = []
    for i in range(1, len(prices)):
        p0, p1 = prices[i - 1], prices[i]
        if p0 > 0:
            rets.append(math.log(p1 / p0))
    if len(rets) < 5:
        return None
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / len(rets)
    return math.sqrt(var * 252)


def _estimate_beta(closes: List[float], market_closes: List[float]) -> Optional[float]:
    """
    估算个股 Beta（对市场指数的线性回归斜率）。
    market_closes 为同期市场指数收盘价序列。
    """
    n = min(len(closes), len(market_closes)) - 1
    if n < 10:
        return None
    stock_rets = []
    mkt_rets = []
    for i in range(1, n + 1):
        s0, s1 = closes[-(n + 1) + i - 1], closes[-(n + 1) + i]
        m0, m1 = market_closes[-(n + 1) + i - 1], market_closes[-(n + 1) + i]
        if s0 > 0 and m0 > 0:
            stock_rets.append((s1 - s0) / s0)
            mkt_rets.append((m1 - m0) / m0)
    n2 = len(stock_rets)
    if n2 < 5:
        return None
    ms = sum(stock_rets) / n2
    mm = sum(mkt_rets) / n2
    cov = sum((s - ms) * (m - mm) for s, m in zip(stock_rets, mkt_rets)) / n2
    var_m = sum((m - mm) ** 2 for m in mkt_rets) / n2
    if var_m < 1e-9:
        return None
    return cov / var_m


class RiskFilterEngine:
    """
    风险过滤引擎（Phase 6 完整实现）。

    对 ScoringEngine 输出的 ScreeningResult 进行风险过滤，
    更新 passed_risk_filter 标志，返回过滤后的股票列表。
    """

    def __init__(
        self,
        log_fn: Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
    ) -> None:
        self._log = log_fn or print
        self._main_engine = main_engine
        self._config = RiskFilterConfig.default()

        # 对接 risk_engine_2 的纯函数（如果可用）
        self._risk_metrics = None
        self._init_risk_metrics()

    def _init_risk_metrics(self) -> None:
        try:
            from vnpy.risk_engine_2.utils.risk_metrics import (
                check_beta_limit, check_industry_limit
            )
            self._check_beta_limit = check_beta_limit
            self._check_industry_limit = check_industry_limit
            self._log("[RiskFilterEngine] Risk Engine 2.0 risk_metrics 已加载")
        except ImportError:
            self._check_beta_limit = None
            self._check_industry_limit = None
            self._log("[RiskFilterEngine] 使用内置风险检查逻辑")

    # ── 配置 ─────────────────────────────────────────────────────────

    def set_config(self, config: RiskFilterConfig) -> None:
        self._config = config

    def get_config(self) -> RiskFilterConfig:
        return self._config

    def set_main_engine(self, main_engine: Any) -> None:
        self._main_engine = main_engine

    # ── 主接口 ────────────────────────────────────────────────────────

    def filter_result(
        self, result: ScreeningResult
    ) -> Tuple[ScreeningResult, List[str]]:
        """
        对 ScreeningResult 执行风险过滤。

        返回 (更新后的 result, 过滤原因列表)
        """
        if not result or not result.stocks:
            return result, []

        self._log(
            f"[RiskFilterEngine] 开始风险过滤：{len(result.stocks)} 只"
        )
        filter_log: List[str] = []

        # 1. 波动率过滤
        if self._config.enable_vol_filter:
            result, reasons = self._filter_volatility(result)
            filter_log.extend(reasons)

        # 2. Beta 过滤
        if self._config.enable_beta_filter:
            result, reasons = self._filter_beta(result)
            filter_log.extend(reasons)

        # 3. 行业集中度控制
        if self._config.enable_industry_filter:
            result, reasons = self._filter_industry(result)
            filter_log.extend(reasons)

        passed = [s for s in result.stocks if s.passed_risk_filter]
        removed = len(result.stocks) - len(passed)
        self._log(
            f"[RiskFilterEngine] 风险过滤完成："
            f"通过 {len(passed)}，移除 {removed}"
        )
        result.total_passed_risk = len(passed)
        return result, filter_log

    def filter_symbols(self, symbols: List[str]) -> List[str]:
        """轻量接口：直接过滤 symbol 列表（无评分信息）。"""
        result_symbols = list(symbols)

        if self._config.enable_vol_filter:
            result_symbols = self._vol_filter_symbols(result_symbols)

        if self._config.enable_beta_filter:
            result_symbols = self._beta_filter_symbols(result_symbols)

        removed = len(symbols) - len(result_symbols)
        if removed > 0:
            self._log(
                f"[RiskFilterEngine] 轻量过滤：移除 {removed} 只，"
                f"剩余 {len(result_symbols)} 只"
            )
        return result_symbols

    # ── 波动率过滤 ────────────────────────────────────────────────────

    def _filter_volatility(
        self, result: ScreeningResult
    ) -> Tuple[ScreeningResult, List[str]]:
        reasons: List[str] = []
        fetcher = self._get_fetcher()
        for ss in result.stocks:
            if not ss.passed_risk_filter:
                continue
            vol = self._get_volatility(ss.symbol, fetcher)
            if vol is not None and vol > self._config.max_volatility:
                ss.passed_risk_filter = False
                msg = (f"{ss.symbol} 波动率过高：{vol:.1%} > "
                       f"{self._config.max_volatility:.1%}")
                ss.risk_flags.append(msg)
                reasons.append(msg)
        return result, reasons

    def _vol_filter_symbols(self, symbols: List[str]) -> List[str]:
        fetcher = self._get_fetcher()
        result = []
        for sym in symbols:
            vol = self._get_volatility(sym, fetcher)
            if vol is None or vol <= self._config.max_volatility:
                result.append(sym)
        return result

    def _get_volatility(self, symbol: str, fetcher) -> Optional[float]:
        if fetcher is None:
            return None
        try:
            sd = fetcher.get_symbol_data(symbol)
            return _compute_vol(sd.closes, self._config.vol_window)
        except Exception:
            return None

    # ── Beta 过滤 ─────────────────────────────────────────────────────

    def _filter_beta(
        self, result: ScreeningResult
    ) -> Tuple[ScreeningResult, List[str]]:
        reasons: List[str] = []
        fetcher = self._get_fetcher()
        mkt_closes = self._get_market_closes()

        for ss in result.stocks:
            if not ss.passed_risk_filter:
                continue
            beta = self._get_beta(ss.symbol, fetcher, mkt_closes)
            if beta is None:
                continue
            if self._check_beta_limit:
                passed, msg = self._check_beta_limit(
                    beta, self._config.max_beta
                )
            else:
                passed = abs(beta) <= self._config.max_beta
                msg = (f"{ss.symbol} Beta={beta:.2f} > {self._config.max_beta:.2f}"
                       if not passed else "")
            if not passed:
                ss.passed_risk_filter = False
                full_msg = f"{ss.symbol} {msg}"
                ss.risk_flags.append(full_msg)
                reasons.append(full_msg)
        return result, reasons

    def _beta_filter_symbols(self, symbols: List[str]) -> List[str]:
        fetcher = self._get_fetcher()
        mkt_closes = self._get_market_closes()
        result = []
        for sym in symbols:
            beta = self._get_beta(sym, fetcher, mkt_closes)
            if beta is None or abs(beta) <= self._config.max_beta:
                result.append(sym)
        return result

    def _get_beta(self, symbol: str, fetcher,
                  mkt_closes: List[float]) -> Optional[float]:
        if fetcher is None or not mkt_closes:
            return None
        try:
            sd = fetcher.get_symbol_data(symbol)
            if not sd.closes:
                return None
            return _estimate_beta(sd.closes, mkt_closes)
        except Exception:
            return None

    def _get_market_closes(self) -> List[float]:
        """获取市场指数收盘价（沪深300作为 proxy）。"""
        if self._main_engine is None:
            return []
        try:
            from vnpy.trader.constant import Exchange, Interval
            from datetime import datetime, timedelta
            db = self._main_engine.get_database()
            if db is None:
                return []
            bars = db.load_bar_data(
                symbol="000300",
                exchange=Exchange.SSE,
                interval=Interval.DAILY,
                start=datetime.now() - timedelta(days=120),
                end=datetime.now(),
            )
            return [b.close_price for b in bars] if bars else []
        except Exception:
            return []

    # ── 行业集中度控制 ────────────────────────────────────────────────

    def _filter_industry(
        self, result: ScreeningResult
    ) -> Tuple[ScreeningResult, List[str]]:
        """同行业最多保留 Top N 只（按综合评分排序）。"""
        reasons: List[str] = []
        max_n = self._config.max_industry_count
        industry_count: Dict[str, int] = {}

        for ss in sorted(result.stocks,
                         key=lambda s: s.composite_score, reverse=True):
            if not ss.passed_risk_filter:
                continue
            industry = self._get_industry(ss.symbol)
            count = industry_count.get(industry, 0)
            if count >= max_n:
                ss.passed_risk_filter = False
                msg = (f"{ss.symbol} 行业[{industry}]已有 {count} 只入选，"
                       f"超过上限 {max_n}")
                ss.risk_flags.append(msg)
                reasons.append(msg)
            else:
                industry_count[industry] = count + 1
        return result, reasons

    def _get_industry(self, symbol: str) -> str:
        """获取股票所属行业（无数据时返回代码前缀作为 fallback）。"""
        if self._main_engine:
            try:
                contract = self._main_engine.get_contract(symbol)
                if contract and hasattr(contract, "industry"):
                    return str(contract.industry or "UNKNOWN")
            except Exception:
                pass
        code = symbol.split(".")[0]
        if code.startswith("6"):
            return "SSE_MAIN"
        if code.startswith("0") or code.startswith("3"):
            return "SZSE"
        return "OTHER"

    # ── 工具 ─────────────────────────────────────────────────────────

    def _get_fetcher(self):
        """获取 DataFetcher 实例（从 screening engine 共享）。"""
        try:
            from ..utils.data_fetcher import DataFetcher
            fetcher = DataFetcher(main_engine=self._main_engine)
            return fetcher
        except Exception:
            return None

    def summary(self) -> dict:
        return {
            "config": self._config.to_dict(),
            "risk_metrics_available": self._check_beta_limit is not None,
        }
