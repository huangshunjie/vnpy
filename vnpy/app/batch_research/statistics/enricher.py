"""
statistics/enricher.py

ResultEnricher  —  把 BacktestResult 转换为 BatchBacktestResult
NameProvider    —  股票名称/行业元数据接口（L4 预留）
DictNameProvider —  基于字典的名称提供者（当前默认实现）

设计约定：
- ResultEnricher 是 BacktestResult → BatchBacktestResult 的唯一入口
- 按 L0→L1→L2→L3→L4 分层构建，层间依赖清晰
- 不依赖 Qt，不依赖数据库，可在任何上下文使用
- NameProvider 通过构造函数注入，便于测试替换
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..batch_result import BatchBacktestResult
from .metrics import (
    RiskMetrics,
    TradeMetrics,
)

if TYPE_CHECKING:
    from ..task import BacktestResult


# ──────────────────────────────────────────────────── #
#  NameProvider  —  L4 元数据接口
# ──────────────────────────────────────────────────── #

class NameProvider(ABC):
    """
    股票名称/行业元数据提供者抽象基类。

    当前默认实现（DictNameProvider）返回空字符串。
    后续可替换为：
    - TushareNameProvider：从 Tushare stock_basic 接口拉取
    - CSVNameProvider：从本地 stock_list.csv 文件读取
    """

    @abstractmethod
    def get_name(self, symbol: str) -> str:
        """根据股票代码返回股票名称，找不到时返回空字符串。"""
        ...

    @abstractmethod
    def get_industry(self, symbol: str) -> str:
        """根据股票代码返回所属行业，找不到时返回空字符串。"""
        ...


class DictNameProvider(NameProvider):
    """
    基于字典的名称提供者。

    可通过构造函数传入已有的名称/行业字典，
    也可调用 update() 动态追加数据。
    """

    def __init__(
        self,
        names: dict[str, str] | None = None,
        industries: dict[str, str] | None = None,
    ) -> None:
        self._names:      dict[str, str] = names or {}
        self._industries: dict[str, str] = industries or {}

    def get_name(self, symbol: str) -> str:
        return self._names.get(symbol, "")

    def get_industry(self, symbol: str) -> str:
        return self._industries.get(symbol, "")

    def update(
        self,
        names: dict[str, str] | None = None,
        industries: dict[str, str] | None = None,
    ) -> None:
        """动态追加名称/行业数据。"""
        if names:
            self._names.update(names)
        if industries:
            self._industries.update(industries)


# ──────────────────────────────────────────────────── #
#  ResultEnricher  —  核心转换类
# ──────────────────────────────────────────────────── #

class ResultEnricher:
    """
    把 BacktestResult 转换为 BatchBacktestResult。

    职责边界：
    - 只负责"转换"，不负责"回测"
    - 只读 BacktestResult，不修改它
    - 按层计算指标，层间依赖清晰
    - NameProvider 通过构造函数注入，便于测试替换

    用法::

        enricher = ResultEnricher(annual_days=240)
        bbr = enricher.enrich(backtest_result)

        # 批量
        bbr_list = enricher.enrich_batch(result_list)
    """

    def __init__(
        self,
        annual_days: int = 240,
        name_provider: NameProvider | None = None,
    ) -> None:
        self._annual_days    = annual_days
        self._name_provider  = name_provider or DictNameProvider()

    # ── 公开 API ─────────────────────────────────── #

    def enrich(self, result: "BacktestResult") -> BatchBacktestResult:
        """
        主入口：BacktestResult → BatchBacktestResult。

        FAILED / SKIPPED 结果：statistics 为空，所有指标字段填 0.0。
        """
        stats = result.statistics or {}

        # L1 指标在 _build_risk / _build_trading 内直接调用 Metrics 方法计算，不修改 stats dict

        basic   = self._build_basic(result, stats)
        returns = self._build_returns(stats)
        risk    = self._build_risk(stats)
        trading = self._build_trading(stats)
        runinfo = self._build_runinfo(result, stats)
        costs   = self._build_costs(stats)

        return BatchBacktestResult(
            **basic,
            **returns,
            **risk,
            **trading,
            **costs,
            **runinfo,
        )

    def enrich_batch(
        self,
        results: list["BacktestResult"],
    ) -> list[BatchBacktestResult]:
        """批量转换，保持原始顺序。"""
        return [self.enrich(r) for r in results]

    def set_name_provider(self, provider: NameProvider) -> None:
        """动态替换名称提供者（支持热更新）。"""
        self._name_provider = provider

    # ── 分层构建方法 ──────────────────────────────── #

    def _build_basic(
        self,
        result: "BacktestResult",
        stats: dict,
    ) -> dict:
        """
        L0 + L4：基本信息。
        vt_symbol / symbol / exchange 来自 BacktestResult。
        name / industry 来自 NameProvider（L4，当前返回空字符串）。
        """
        symbol   = result.vt_symbol.split(".")[0]
        exchange = result.vt_symbol.split(".")[1] if "." in result.vt_symbol else ""

        return {
            "vt_symbol":     result.vt_symbol,
            "symbol":        symbol,
            "exchange":      exchange,
            "name":          self._name_provider.get_name(symbol),
            "industry":      self._name_provider.get_industry(symbol),
            "strategy_name": result.strategy_name,
            "status":        result.status.value,
            "error_msg":     result.error_msg,
        }

    def _build_returns(self, stats: dict) -> dict:
        """L0：收益指标，直接从 statistics 取值。"""
        return {
            "total_return":  float(stats.get("total_return",  0.0)),
            "annual_return": float(stats.get("annual_return", 0.0)),
            "total_net_pnl": float(stats.get("total_net_pnl", 0.0)),
            "end_balance":   float(stats.get("end_balance",   0.0)),
            "daily_return":  float(stats.get("daily_return",  0.0)),
        }

    def _build_risk(self, stats: dict) -> dict:
        """
        L0 + L1：风险指标。
        官方字段直取，calmar_ratio/annual_volatility 为 L1 派生。
        sortino_ratio 为 L2 预留，当前填 0.0。
        """
        return_std    = float(stats.get("return_std",    0.0))
        annual_return = float(stats.get("annual_return", 0.0))
        max_ddpercent = float(stats.get("max_ddpercent", 0.0))

        # L1：calmar_ratio（enrich_statistics 已写入 stats，直接取）
        # L1: calmar_ratio and annual_volatility via pure functions
        calmar     = RiskMetrics.calc_calmar(annual_return, max_ddpercent)
        annual_vol = RiskMetrics.calc_annual_volatility(return_std, self._annual_days)

        return {
            "max_ddpercent":         max_ddpercent,
            "max_drawdown":          float(stats.get("max_drawdown",          0.0)),
            "max_drawdown_duration": int(stats.get("max_drawdown_duration",   0)),
            "sharpe_ratio":          float(stats.get("sharpe_ratio",          0.0)),
            "ewm_sharpe":            float(stats.get("ewm_sharpe",            0.0)),
            "return_drawdown_ratio": float(stats.get("return_drawdown_ratio", 0.0)),
            "rgr_ratio":             float(stats.get("rgr_ratio",             0.0)),
            "calmar_ratio":          round(calmar, 4),
            "annual_volatility":     round(annual_vol, 4),
            "sortino_ratio":         None,  # L2 预留
        }

    def _build_trading(self, stats: dict) -> dict:
        """
        L0 + L1：交易指标。
        win_rate / profit_factor 为 L1 派生。
        avg_holding_days 为 L3 预留，当前填 0.0。
        """
        profit_days = int(stats.get("profit_days", 0))
        total_days  = int(stats.get("total_days",  0))

        # L1: win_rate
        win_rate = TradeMetrics.calc_win_rate(profit_days, total_days)

        # L1: profit_factor 走纯函数路径
        profit_factor = TradeMetrics.calc_profit_factor(
            float(stats.get("total_net_pnl",    0.0)),
            float(stats.get("total_commission", 0.0)),
            float(stats.get("total_slippage",   0.0)),
        )

        return {
            "total_trade_count": int(stats.get("total_trade_count",  0)),
            "daily_trade_count": float(stats.get("daily_trade_count", 0.0)),
            "profit_days":       profit_days,
            "loss_days":         int(stats.get("loss_days",   0)),
            "total_days":        total_days,
            "win_rate":          round(win_rate, 4),
            "profit_factor":     round(profit_factor, 4),
            "avg_holding_days":  None,  # L3 预留
        }

    def _build_costs(self, stats: dict) -> dict:
        """L0：成本信息（export_only 列）。"""
        return {
            "total_commission": float(stats.get("total_commission", 0.0)),
            "total_slippage":   float(stats.get("total_slippage",   0.0)),
            "total_turnover":   float(stats.get("total_turnover",   0.0)),
            "capital":          float(stats.get("capital",          0.0)),
            "return_std":       float(stats.get("return_std",       0.0)),
            "daily_net_pnl":    float(stats.get("daily_net_pnl",    0.0)),
        }

    def _build_runinfo(
        self,
        result: "BacktestResult",
        stats: dict,
    ) -> dict:
        """L0：运行信息，混合来自 BacktestResult 和 statistics。"""
        start = stats.get("start_date", "")
        end   = stats.get("end_date",   "")
        return {
            "elapsed":    result.elapsed_seconds or 0.0,
            "start_date": str(start) if start else "",
            "end_date":   str(end)   if end   else "",
            "task_id":    result.task_id,
        }


# ──────────────────────────────────────────────────── #
#  TushareNameProvider  —  L4 元数据：Tushare 数据源
# ──────────────────────────────────────────────────── #

class TushareNameProvider(NameProvider):
    """
    通过 Tushare stock_basic 接口获取股票名称和行业数据。

    首次调用时拉取全量 A 股基本信息（约 5000 条），
    结果缓存在内存中，后续调用不再请求网络。

    用法::

        provider = TushareNameProvider("your_token_here")
        enricher = ResultEnricher(name_provider=provider)

    Token 获取：https://tushare.pro/register
    """

    def __init__(self, token: str) -> None:
        self._token  = token
        self._names:      dict[str, str] = {}
        self._industries: dict[str, str] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            import tushare as ts
            pro = ts.pro_api(self._token)
            df = pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name,industry",
            )
            for _, row in df.iterrows():
                ts_code = str(row.get("ts_code", ""))
                # ts_code 格式 "000001.SZ" → symbol "000001"
                symbol = ts_code.split(".")[0] if "." in ts_code else ts_code
                self._names[symbol]      = str(row.get("name", ""))
                self._industries[symbol] = str(row.get("industry", ""))
            self._loaded = True
        except Exception as e:
            # 网络失败或 token 无效时静默降级，返回空字符串
            import warnings
            warnings.warn(
                f"TushareNameProvider: 加载失败，名称/行业将显示为空。原因：{e}",
                stacklevel=2,
            )
            self._loaded = True   # 标记为已尝试，避免反复请求

    def get_name(self, symbol: str) -> str:
        self._ensure_loaded()
        return self._names.get(symbol, "")

    def get_industry(self, symbol: str) -> str:
        self._ensure_loaded()
        return self._industries.get(symbol, "")

    def reload(self) -> None:
        """强制重新拉取（Token 更新或数据过期时调用）。"""
        self._loaded = False
        self._names.clear()
        self._industries.clear()
        self._ensure_loaded()

    @staticmethod
    def from_settings() -> "TushareNameProvider | None":
        """
        从 VeighNa 标准配置文件读取 token 并构建 Provider。

        优先级：
          1. ~/.vnpy/vt_setting.json  key="tushare_token"
          2. ~/.vnpy/tushare_token.txt  （纯文本，单行）

        找不到 token 时返回 None。
        """
        import json
        from pathlib import Path

        # 路径 1：vt_setting.json
        cfg = Path.home() / ".vnpy" / "vt_setting.json"
        if cfg.exists():
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
                token = data.get("tushare_token", "").strip()
                if token:
                    return TushareNameProvider(token)
            except Exception:
                pass

        # 路径 2：独立 token 文件
        token_file = Path.home() / ".vnpy" / "tushare_token.txt"
        if token_file.exists():
            token = token_file.read_text(encoding="utf-8").strip()
            if token:
                return TushareNameProvider(token)

        return None
