"""
batch_result.py

BatchBacktestResult  —  批量回测单股票汇总结果（强类型 dataclass）

设计约定：
- BatchBacktestResult 是 UI、导出、因子分析的统一数据源
- 不依赖 Qt，不依赖数据库，可在任何上下文中使用
- 字段按来源分层标注：L0 / L1 / L2 / L3 / L4 / LF / META
- 预留字段（L2 / L3 / LF）默认值为 None，语义明确：None = 尚未计算
- ColumnDef / COLUMN_DEFS 已迁移到 column_definition.py / column_registry.py
  本文件保留向后兼容别名，旧代码无需修改 import

字段分层说明：
  L0   直接来自 BacktestingEngine.calculate_statistics() 的官方字段
  L1   本模块派生，仅需 L0 字段的简单数学运算
  L2   预留：需要逐日净值序列（DailyResult），当前为 None
  L3   预留：需要逐笔交易记录（TradeData），当前为 None
  L4   外部元数据（Tushare / 本地文件）
  LF   因子分析层，由 FactorEngine.run() 注入
  META 任务运行元信息
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BatchBacktestResult:
    """
    批量回测单股票汇总结果。

    由 ResultEnricher.enrich(BacktestResult) 构建。
    L2 / L3 / LF 预留字段默认值为 None，表示尚未计算。
    """

    # ── [L4] 标的信息 ────────────────────────────────────────── #
    vt_symbol:     str       # "000001.SZSE"
    symbol:        str       # "000001"
    exchange:      str       # "SZSE"
    name:          str       # "平安银行"（来自 TushareNameProvider）
    industry:      str       # "银行"（来自 TushareNameProvider）

    # ── [META] 任务元信息 ─────────────────────────────────────── #
    strategy_name: str       # 策略类名
    status:        str       # "success" / "failed" / "skipped"
    error_msg:     str       # 失败时的错误描述
    task_id:       str       # 任务唯一标识
    start_date:    str       # 回测开始日期 "2020-01-01"
    end_date:      str       # 回测结束日期 "2024-12-31"
    elapsed:       float     # 单股票回测耗时（秒）

    # ── [L0] 收益指标 ─────────────────────────────────────────── #
    total_return:   float    # 总收益率（%）
    annual_return:  float    # 年化收益率（%）
    total_net_pnl:  float    # 累计净盈亏（元）
    end_balance:    float    # 期末资金（元）
    capital:        float    # 初始资金（元）
    daily_return:   float    # 日均收益率（%）

    # ── [L0] 风险指标 ─────────────────────────────────────────── #
    max_drawdown:          float   # 最大回撤金额（元）
    max_ddpercent:         float   # 最大回撤幅度（%，负数）
    max_drawdown_duration: int     # 最大回撤持续天数
    sharpe_ratio:          float   # 夏普比率
    ewm_sharpe:            float   # EWM 加权夏普比率
    return_drawdown_ratio: float   # 收益回撤比
    rgr_ratio:             float   # RGR 比率
    return_std:            float   # 日收益率标准差（%）

    # ── [L0] 交易指标 ─────────────────────────────────────────── #
    total_trade_count: int     # 总交易次数（双边）
    daily_trade_count: float   # 日均交易次数
    profit_days:       int     # 盈利天数
    loss_days:         int     # 亏损天数
    total_days:        int     # 总交易天数

    # ── [L0] 成本指标 ─────────────────────────────────────────── #
    total_commission: float   # 总手续费（元）
    total_slippage:   float   # 总滑点（元）
    total_turnover:   float   # 总成交额（元）
    daily_net_pnl:    float   # 日均净盈亏（元）

    # ── [L1] 派生指标 ─────────────────────────────────────────── #
    calmar_ratio:      float   # 年化收益 / abs(最大回撤%)
    annual_volatility: float   # 日收益率标准差 × √240（%）
    win_rate:          float   # 盈利天数 / 总交易天数 × 100
    profit_factor:     float   # 净盈亏 / abs(手续费 + 滑点)

    # ── [L2] 预留：需逐日净值序列 ────────────────────────────── #
    sortino_ratio: float | None = None   # 索提诺比率
    var_95:        float | None = None   # 95% 历史分位数 VaR（%）
    cvar_95:       float | None = None   # 95% CVaR / Expected Shortfall（%）

    # ── [L3] 预留：需逐笔交易记录 ────────────────────────────── #
    avg_holding_days:  float | None = None   # 平均每笔持仓天数
    avg_profit_trade:  float | None = None   # 平均盈利笔金额（元）
    avg_loss_trade:    float | None = None   # 平均亏损笔金额（元）
    trade_win_rate:    float | None = None   # 逐笔胜率（%，区别于日胜率）

    # ── [LF] 因子分析层（由 FactorEngine.run() 注入）─────────── #
    alpha:           float | None = None   # 相对基准超额年化收益
    beta:            float | None = None   # 相对基准系统性风险
    ic:              float | None = None   # 信息系数（Pearson IC）
    rank_ic:         float | None = None   # Spearman Rank IC
    ic_ir:           float | None = None   # IC 信息比率（mean/std）
    composite_score: float | None = None   # 多因子加权综合评分
    factor_rank:     int   | None = None   # 综合排名（None=未排名，1=最好）
    factor_scores:   dict[str, float] = field(default_factory=dict)
    selected:        bool = False          # 是否被因子模型选中

    # ── 工具方法 ────────────────────────────────────────────────── #

    def to_flat_dict(self) -> dict[str, Any]:
        """
        展开为单层字典，factor_scores 中每个因子单独展开为列。
        None 值原样保留，由调用方决定如何处理。
        """
        import dataclasses as _dc
        row = {
            f.name: getattr(self, f.name)
            for f in _dc.fields(self)
            if f.name != "factor_scores"
        }
        for k, v in self.factor_scores.items():
            row[f"factor_{k}"] = v
        return row

    def __repr__(self) -> str:
        return (
            f"BatchBacktestResult("
            f"vt_symbol={self.vt_symbol!r}, "
            f"status={self.status!r}, "
            f"total_return={self.total_return:.2f}%, "
            f"sharpe={self.sharpe_ratio:.3f})"
        )


# ── 向后兼容：保留旧 ColumnDef / COLUMN_DEFS 的 import 路径 ──────── #
# 旧代码 `from .batch_result import ColumnDef, COLUMN_DEFS` 仍可运行
# 新代码应改为从 column_definition / column_registry 导入

from .column_definition import ColumnDefinition as ColumnDef          # noqa: E402
from .column_registry import COLUMN_REGISTRY as COLUMN_DEFS           # noqa: E402
from .column_registry import get_default_visible as _get_default_visible  # noqa: E402

# UI_COLUMNS / ALL_COLUMNS 兼容别名（column_manager 接管前的过渡期使用）
UI_COLUMNS:  list[ColumnDef] = _get_default_visible()
ALL_COLUMNS: list[ColumnDef] = list(COLUMN_DEFS)
