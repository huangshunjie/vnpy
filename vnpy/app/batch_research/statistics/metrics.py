"""
statistics/metrics.py

纯函数指标库，按职责分为 5 个 Metrics 类。

设计约定：
- 所有函数无状态、无副作用、无外部依赖
- 不修改任何传入对象（原始 statistics dict 保持不变）
- 返回新值，由调用方（ResultEnricher）组装到 BatchBacktestResult
- 可在任意上下文使用（测试、Jupyter、生产）

类职责：
  BasicMetrics    L0 字段直取：标的信息 + 元信息
  ReturnMetrics   L0 字段直取：收益相关
  RiskMetrics     L0 直取 + L1 派生 + L2 预留骨架
  TradeMetrics    L0 直取 + L1 派生 + L3 预留骨架
  CapitalMetrics  L0 字段直取：成本 / 资金
"""

from __future__ import annotations

import math


class BasicMetrics:
    """从 BacktestResult 和 statistics dict 直取基本信息，无任何计算。"""

    @staticmethod
    def extract(result: object, stats: dict) -> dict:
        vt_symbol = result.vt_symbol  # type: ignore[attr-defined]
        parts     = vt_symbol.split(".")
        symbol    = parts[0]
        exchange  = parts[1] if len(parts) > 1 else ""

        start = stats.get("start_date", "")
        end   = stats.get("end_date",   "")

        status_raw = getattr(result, "status", "")
        status_str = (
            status_raw.value
            if hasattr(status_raw, "value")
            else str(status_raw)
        )

        return {
            "vt_symbol":     vt_symbol,
            "symbol":        symbol,
            "exchange":      exchange,
            "strategy_name": getattr(result, "strategy_name", ""),
            "status":        status_str,
            "error_msg":     getattr(result, "error_msg", ""),
            "task_id":       getattr(result, "task_id", ""),
            "start_date":    str(start) if start else "",
            "end_date":      str(end)   if end   else "",
            "elapsed":       getattr(result, "elapsed_seconds", None) or 0.0,
        }


class ReturnMetrics:
    """从 statistics dict 直取收益相关字段，无计算。"""

    @staticmethod
    def extract(stats: dict) -> dict:
        return {
            "total_return":  float(stats.get("total_return",  0.0)),
            "annual_return": float(stats.get("annual_return", 0.0)),
            "total_net_pnl": float(stats.get("total_net_pnl", 0.0)),
            "end_balance":   float(stats.get("end_balance",   0.0)),
            "capital":       float(stats.get("capital",       0.0)),
            "daily_return":  float(stats.get("daily_return",  0.0)),
        }


class RiskMetrics:
    """风险指标：L0 官方字段直取，L1 派生计算，L2 预留接口。"""

    @staticmethod
    def extract_l0(stats: dict) -> dict:
        return {
            "max_drawdown":          float(stats.get("max_drawdown",          0.0)),
            "max_ddpercent":         float(stats.get("max_ddpercent",         0.0)),
            "max_drawdown_duration": int(  stats.get("max_drawdown_duration", 0)),
            "sharpe_ratio":          float(stats.get("sharpe_ratio",          0.0)),
            "ewm_sharpe":            float(stats.get("ewm_sharpe",            0.0)),
            "return_drawdown_ratio": float(stats.get("return_drawdown_ratio", 0.0)),
            "rgr_ratio":             float(stats.get("rgr_ratio",             0.0)),
            "return_std":            float(stats.get("return_std",            0.0)),
        }

    @staticmethod
    def calc_calmar(annual_return: float, max_ddpercent: float) -> float:
        import math
        if not max_ddpercent or math.isnan(max_ddpercent):
            return 0.0
        result = annual_return / abs(max_ddpercent)
        if math.isnan(result) or math.isinf(result):
            return 0.0
        return round(result, 4)

    @staticmethod
    def calc_annual_volatility(return_std: float, annual_days: int = 240) -> float:
        import math
        return round(return_std * math.sqrt(annual_days), 4)

    @staticmethod
    def extract_l1(stats: dict, annual_days: int = 240) -> dict:
        return {
            "calmar_ratio": RiskMetrics.calc_calmar(
                float(stats.get("annual_return", 0.0)),
                float(stats.get("max_ddpercent", 0.0)),
            ),
            "annual_volatility": RiskMetrics.calc_annual_volatility(
                float(stats.get("return_std", 0.0)), annual_days
            ),
        }

    @staticmethod
    def calc_sortino(daily_returns, annual_days: int = 240):
        import math
        if daily_returns is None:
            return None
        downside = [r for r in daily_returns if r < 0]
        if len(downside) < 2:
            return None
        n = len(downside)
        mean = sum(downside) / n
        var  = sum((r - mean) ** 2 for r in downside) / (n - 1)
        std  = math.sqrt(var) * math.sqrt(annual_days)
        if std == 0:
            return None
        return round(sum(daily_returns) / len(daily_returns) * annual_days / std, 4)

    @staticmethod
    def calc_var(daily_returns, confidence: float = 0.95):
        if daily_returns is None or len(daily_returns) < 10:
            return None
        sorted_r = sorted(daily_returns)
        idx = int(len(sorted_r) * (1 - confidence))
        return round(sorted_r[max(idx, 0)], 4)

    @staticmethod
    def calc_cvar(daily_returns, confidence: float = 0.95):
        if daily_returns is None or len(daily_returns) < 10:
            return None
        var = RiskMetrics.calc_var(daily_returns, confidence)
        if var is None:
            return None
        tail = [r for r in daily_returns if r <= var]
        return round(sum(tail) / len(tail), 4) if tail else None

    @staticmethod
    def calc_alpha_beta(portfolio_returns, benchmark_returns,
                        risk_free_rate: float = 0.0, annual_days: int = 240):
        if portfolio_returns is None or benchmark_returns is None:
            return None, None
        n = min(len(portfolio_returns), len(benchmark_returns))
        if n < 10:
            return None, None
        p, b = portfolio_returns[:n], benchmark_returns[:n]
        mean_b = sum(b) / n
        var_b  = sum((r - mean_b) ** 2 for r in b) / n
        if var_b == 0:
            return None, None
        mean_p = sum(p) / n
        cov    = sum((p[i] - mean_p) * (b[i] - mean_b) for i in range(n)) / n
        beta   = cov / var_b
        rf_d   = risk_free_rate / annual_days
        alpha  = (mean_p - rf_d) * annual_days - beta * (mean_b - rf_d) * annual_days
        return round(alpha, 4), round(beta, 4)


class TradeMetrics:
    """交易指标：L0 直取，L1 派生，L3 预留接口。"""

    @staticmethod
    def extract_l0(stats: dict) -> dict:
        return {
            "total_trade_count": int(  stats.get("total_trade_count",  0)),
            "daily_trade_count": float(stats.get("daily_trade_count",  0.0)),
            "profit_days":       int(  stats.get("profit_days",        0)),
            "loss_days":         int(  stats.get("loss_days",          0)),
            "total_days":        int(  stats.get("total_days",         0)),
        }

    @staticmethod
    def calc_win_rate(profit_days: int, total_days: int) -> float:
        if total_days <= 0:
            return 0.0
        return round(profit_days / total_days * 100.0, 4)

    @staticmethod
    def calc_profit_factor(total_net_pnl: float,
                           total_commission: float,
                           total_slippage: float) -> float:
        import math
        costs = abs(total_commission) + abs(total_slippage)
        if costs <= 0:
            return 0.0
        result = total_net_pnl / costs
        if math.isnan(result) or math.isinf(result):
            return 0.0
        return round(result, 4)

    @staticmethod
    def extract_l1(stats: dict) -> dict:
        return {
            "win_rate": TradeMetrics.calc_win_rate(
                int(stats.get("profit_days", 0)),
                int(stats.get("total_days",  0)),
            ),
            "profit_factor": TradeMetrics.calc_profit_factor(
                float(stats.get("total_net_pnl",    0.0)),
                float(stats.get("total_commission", 0.0)),
                float(stats.get("total_slippage",   0.0)),
            ),
        }

    @staticmethod
    def calc_avg_holding(trades) -> float | None:
        return None  # TODO: L3

    @staticmethod
    def calc_trade_win_rate(trades) -> float | None:
        return None  # TODO: L3

    @staticmethod
    def calc_avg_profit_trade(trades) -> float | None:
        return None  # TODO: L3

    @staticmethod
    def calc_avg_loss_trade(trades) -> float | None:
        return None  # TODO: L3


class CapitalMetrics:
    """从 statistics dict 直取资金和成本字段，无任何计算。"""

    @staticmethod
    def extract(stats: dict) -> dict:
        return {
            "total_commission": float(stats.get("total_commission", 0.0)),
            "total_slippage":   float(stats.get("total_slippage",   0.0)),
            "total_turnover":   float(stats.get("total_turnover",   0.0)),
            "daily_net_pnl":    float(stats.get("daily_net_pnl",    0.0)),
        }


# ── 向后兼容函数 ──────────────────────────────────────────────────── #

def calc_annual_volatility(return_std: float, annual_days: int = 240) -> float:
    return RiskMetrics.calc_annual_volatility(return_std, annual_days)


def calc_win_rate(profit_days: int, total_days: int) -> float:
    return TradeMetrics.calc_win_rate(profit_days, total_days)


def enrich_statistics(stats: dict) -> dict:
    """
    向后兼容函数（已去除副作用）。

    旧版本直接修改 stats dict；新版本只返回派生指标 dict，不修改传入对象。
    """
    return {
        "calmar_ratio":      RiskMetrics.calc_calmar(
                                 float(stats.get("annual_return", 0.0)),
                                 float(stats.get("max_ddpercent", 0.0))),
        "annual_volatility": RiskMetrics.calc_annual_volatility(
                                 float(stats.get("return_std", 0.0))),
        "profit_factor":     TradeMetrics.calc_profit_factor(
                                 float(stats.get("total_net_pnl",    0.0)),
                                 float(stats.get("total_commission", 0.0)),
                                 float(stats.get("total_slippage",   0.0))),
        "win_rate":          TradeMetrics.calc_win_rate(
                                 int(stats.get("profit_days", 0)),
                                 int(stats.get("total_days",  0))),
    }


def build_aggregate_summary(results: list) -> dict:
    """构建批量回测聚合摘要，兼容 BacktestResult 和 BatchBacktestResult。"""

    def _get(r, key, default=0.0):
        if hasattr(r, key):
            val = getattr(r, key)
            return val if val is not None else default
        if hasattr(r, "statistics"):
            return r.statistics.get(key, default)
        return default

    valid = [r for r in results if _get(r, "total_return", None) is not None]
    total = len(results)
    n     = len(valid)

    def avg(key):
        return sum(_get(r, key, 0.0) for r in valid) / n if n else 0.0

    return {
        "agg_total_symbols":     total,
        "agg_success_symbols":   n,
        "agg_failed_symbols":    sum(1 for r in results
                                     if _get(r, "total_return", None) is None
                                     and _get(r, "error_msg",   "")),
        "agg_skipped_symbols":   sum(1 for r in results
                                     if _get(r, "total_return", None) is None
                                     and not _get(r, "error_msg", "")),
        "agg_avg_total_return":  round(avg("total_return"),  4),
        "agg_avg_annual_return": round(avg("annual_return"), 4),
        "agg_avg_sharpe":        round(avg("sharpe_ratio"),  4),
        "agg_avg_max_ddpercent": round(avg("max_ddpercent"), 4),
        "agg_avg_calmar":        round(avg("calmar_ratio"),  4),
        "agg_win_rate":          round(
            sum(1 for r in valid if _get(r, "total_return", 0.0) > 0)
            / n * 100 if n else 0.0, 2),
        "agg_total_trades":      sum(int(_get(r, "total_trade_count", 0)) for r in valid),
        "agg_avg_trades":        round(
            sum(int(_get(r, "total_trade_count", 0)) for r in valid)
            / n if n else 0.0, 1),
    }
