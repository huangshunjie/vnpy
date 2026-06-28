"""
column_registry.py

COLUMN_REGISTRY  —  全局列注册表（唯一真相来源）

设计约定：
- 所有列的元数据在此统一声明，其他模块只读不写
- 新增一列：只在此文件加一行 ColumnDefinition，其余文件无需修改
- 列按 group 分组，组内按逻辑顺序排列
- default_visible=True  → 默认显示（目标控制在 15~18 列）
- default_visible=False → 默认隐藏，用户可通过列管理显示
- pinned=True           → 固定列，用户不可隐藏
- export_always=True    → 始终写入导出文件（meta 组）

分组及默认可见列数：
    basic   (4列，全可见)     股票代码/名称/行业/状态
    return  (9列，3可见)      总收益/年化/净盈亏 + 6隐藏
    risk    (12列，6可见)     回撤/夏普/卡玛/波动率/索提诺/盈亏比 + 6隐藏
    trade   (10列，4可见)     交易次数/日胜率/盈利因子/平均持仓 + 6隐藏
    capital (6列，全隐藏)     成本/资金相关
    factor  (8列，全隐藏)     因子分析相关
    meta    (4列，仅导出)     任务元信息

默认可见合计：4+3+6+4 = 17 列，含耗时共 18 列（与现有版本一致）
"""

from __future__ import annotations

from .column_definition import ColumnDefinition

# 简写构造函数，减少重复代码
def _c(
    key: str,
    header: str,
    group: str,
    width: int,
    fmt: str,
    align: str,
    sortable: bool,
    color_rule: str | None,
    tooltip: str,
    cn_header: str = "",
    default_visible: bool = True,
    pinned: bool = False,
    ui_only: bool = False,
    export_always: bool = False,
) -> ColumnDefinition:
    return ColumnDefinition(
        key=key, header=header, group=group, width=width,
        fmt=fmt, align=align, sortable=sortable,
        color_rule=color_rule, tooltip=tooltip,
        cn_header=cn_header, default_visible=default_visible,
        pinned=pinned, ui_only=ui_only, export_always=export_always,
    )


COLUMN_REGISTRY: list[ColumnDefinition] = [

    # ── basic：基本信息（4列，全默认可见）─────────────────────────── #
    _c("vt_symbol", "股票代码", "basic", 110, "str", "left",   True,  "status",
       "股票代码，格式：代码.交易所",
       cn_header="股票代码", default_visible=True, pinned=True),

    _c("name",      "名称",     "basic",  80, "str", "left",   True,  "status",
       "股票名称",
       cn_header="股票名称"),

    _c("industry",  "行业",     "basic",  80, "str", "left",   True,  "status",
       "所属行业",
       cn_header="所属行业"),

    _c("status",    "状态",     "basic",  70, "str", "center", True,  "status",
       "回测状态：success / failed / skipped",
       cn_header="状态", pinned=True),

    # ── return：收益指标（9列，3默认可见）─────────────────────────── #
    _c("total_return",  "总收益%",    "return",  90, "pct",    "right", True, "pnl",
       "策略期间累计收益率（%）",
       cn_header="总收益率(%)"),

    _c("annual_return", "年化收益%",  "return",  90, "pct",    "right", True, "pnl",
       "折算为年化的收益率（%）",
       cn_header="年化收益率(%)"),

    _c("total_net_pnl", "累计净盈亏", "return", 110, "money",  "right", True, "pnl",
       "扣除手续费和滑点后的累计净盈亏（元）",
       cn_header="累计净盈亏(元)"),

    _c("daily_return",  "日均收益%",  "return",  90, "pct",    "right", True, "pnl",
       "日均收益率（%）",
       cn_header="日均收益率(%)", default_visible=False),

    _c("end_balance",   "期末资金",   "return", 110, "money",  "right", True, "pnl",
       "回测结束时账户余额（元）",
       cn_header="期末资金(元)", default_visible=False),

    _c("alpha",  "Alpha", "return",  80, "float3", "right", True, "pnl",
       "相对基准超额年化收益（LF层，需因子分析后填充）",
       cn_header="Alpha", default_visible=False),

    _c("beta",   "Beta",  "return",  80, "float3", "right", True, None,
       "相对基准系统性风险（LF层，需因子分析后填充）",
       cn_header="Beta", default_visible=False),

    _c("ic",     "IC",    "return",  80, "float3", "right", True, "pnl",
       "信息系数 Pearson IC（LF层，需因子分析后填充）",
       cn_header="IC", default_visible=False),

    _c("rank_ic", "Rank IC", "return", 80, "float3", "right", True, "pnl",
       "Spearman Rank IC（LF层，需因子分析后填充）",
       cn_header="Rank IC", default_visible=False),

    # ── risk：风险指标（12列，6默认可见）──────────────────────────── #
    _c("max_ddpercent",        "最大回撤%",      "risk",  90, "pct",    "right", True, "neg_bad",
       "回测期间最大回撤幅度（%，负数）",
       cn_header="最大回撤(%)"),

    _c("sharpe_ratio",         "夏普比率",       "risk",  90, "float3", "right", True, "pnl",
       "风险调整后收益，>1 较好，>2 优秀",
       cn_header="夏普比率"),

    _c("calmar_ratio",         "卡玛比率",       "risk",  90, "float3", "right", True, "pnl",
       "年化收益 / abs(最大回撤%)，>1 较好",
       cn_header="卡玛比率"),

    _c("annual_volatility",    "年化波动率%",    "risk",  95, "pct",    "right", True, "neg_bad",
       "日收益率标准差 × √240（%）",
       cn_header="年化波动率(%)"),

    _c("sortino_ratio",        "索提诺比率",     "risk",  90, "float3", "right", True, "pnl",
       "只考虑下行风险的夏普比率（L2层，当前版本预留）",
       cn_header="索提诺比率"),

    _c("return_drawdown_ratio","收益回撤比",     "risk",  90, "float3", "right", True, "pnl",
       "VeighNa 官方收益回撤比指标",
       cn_header="收益回撤比"),

    _c("ewm_sharpe",           "EWM夏普",        "risk",  90, "float3", "right", True, "pnl",
       "指数加权夏普比率",
       cn_header="EWM夏普比率", default_visible=False),

    _c("rgr_ratio",            "RGR比率",        "risk",  80, "float3", "right", True, "pnl",
       "VeighNa 官方 RGR 比率",
       cn_header="RGR比率", default_visible=False),

    _c("max_drawdown",         "最大回撤额",     "risk", 110, "money",  "right", True, None,
       "最大回撤金额（元）",
       cn_header="最大回撤额(元)", default_visible=False),

    _c("max_drawdown_duration","最大回撤持续天", "risk", 120, "int",    "right", True, None,
       "最大回撤持续天数",
       cn_header="最大回撤持续天数", default_visible=False),

    _c("var_95",  "VaR(95%)",  "risk",  90, "pct", "right", True, "neg_bad",
       "95% 历史分位数 VaR（L2层，当前版本预留）",
       cn_header="VaR(95%)", default_visible=False),

    _c("cvar_95", "CVaR(95%)", "risk",  90, "pct", "right", True, "neg_bad",
       "条件 VaR / Expected Shortfall（L2层，当前版本预留）",
       cn_header="CVaR(95%)", default_visible=False),

    # ── trade：交易指标（10列，4默认可见）─────────────────────────── #
    _c("total_trade_count", "交易次数",   "trade",  80, "int",    "right", True, None,
       "总交易次数（双边计）",
       cn_header="总交易次数"),

    _c("win_rate",          "日胜率%",    "trade",  80, "pct",    "right", True, "pnl",
       "盈利天数 / 总交易天数 × 100（日级别胜率）",
       cn_header="日胜率(%)"),

    _c("profit_factor",     "盈利因子",   "trade",  80, "float2", "right", True, "pnl",
       "净盈亏 / abs(手续费+滑点)，>1 表示盈利",
       cn_header="盈利因子"),

    _c("avg_holding_days",  "平均持仓天", "trade",  90, "float1", "right", True, None,
       "平均每笔持仓天数（L3层，当前版本预留）",
       cn_header="平均持仓天数"),

    _c("trade_win_rate",    "逐笔胜率%",  "trade",  80, "pct",    "right", True, "pnl",
       "盈利笔数 / 总笔数（逐笔胜率，区别于日胜率，L3层预留）",
       cn_header="逐笔胜率(%)", default_visible=False),

    _c("avg_profit_trade",  "平均盈利",   "trade", 100, "money",  "right", True, "pnl",
       "平均每笔盈利金额（元，L3层预留）",
       cn_header="平均盈利(元)", default_visible=False),

    _c("avg_loss_trade",    "平均亏损",   "trade", 100, "money",  "right", True, "neg_bad",
       "平均每笔亏损金额（元，L3层预留）",
       cn_header="平均亏损(元)", default_visible=False),

    _c("total_days",        "总交易天数", "trade",  90, "int",    "right", True, None,
       "回测期间总交易天数",
       cn_header="总交易天数", default_visible=False),

    _c("profit_days",       "盈利天数",   "trade",  80, "int",    "right", True, None,
       "净盈亏为正的交易天数",
       cn_header="盈利天数", default_visible=False),

    _c("loss_days",         "亏损天数",   "trade",  80, "int",    "right", True, None,
       "净盈亏为负的交易天数",
       cn_header="亏损天数", default_visible=False),

    # ── capital：资金/成本（6列，全默认隐藏）──────────────────────── #
    _c("capital",           "初始资金",   "capital", 110, "money", "right", True, None,
       "回测初始资金（元）",
       cn_header="初始资金(元)", default_visible=False),

    _c("total_commission",  "总手续费",   "capital", 100, "money", "right", True, None,
       "回测期间总手续费（元）",
       cn_header="总手续费(元)", default_visible=False),

    _c("total_slippage",    "总滑点",     "capital",  90, "money", "right", True, None,
       "回测期间总滑点（元）",
       cn_header="总滑点(元)", default_visible=False),

    _c("total_turnover",    "总成交额",   "capital", 110, "money", "right", True, None,
       "回测期间总成交额（元）",
       cn_header="总成交额(元)", default_visible=False),

    _c("daily_net_pnl",     "日均净盈亏", "capital", 100, "money", "right", True, "pnl",
       "日均净盈亏（元）",
       cn_header="日均净盈亏(元)", default_visible=False),

    _c("return_std",        "日收益标准差%", "capital", 100, "pct", "right", True, None,
       "日收益率标准差（%）",
       cn_header="日收益率标准差(%)", default_visible=False),

    # ── run：运行信息（1列，默认可见）─────────────────────────────── #
    _c("elapsed", "耗时(s)", "trade", 75, "float2", "right", True, None,
       "单股票回测耗时（秒）",
       cn_header="耗时(秒)"),

    # ── factor：因子分析（8列，全默认隐藏）────────────────────────── #
    _c("ic_ir",           "IC IR",    "factor",  80, "float3", "right", True, "pnl",
       "IC 信息比率 = mean(IC) / std(IC)（LF层，需多期数据）",
       cn_header="IC IR", default_visible=False),

    _c("composite_score", "综合评分", "factor",  90, "float3", "right", True, "pnl",
       "多因子加权综合评分（LF层，需运行因子分析）",
       cn_header="综合评分", default_visible=False),

    _c("factor_rank",     "综合排名", "factor",  80, "int",    "right", True, None,
       "综合评分全池排名，1=最好（LF层，需运行因子分析）",
       cn_header="综合排名", default_visible=False),

    # ── meta：元信息（4列，仅导出，不在 UI 显示）──────────────────── #
    _c("start_date", "开始日期", "meta", 100, "str", "center", False, None,
       "回测开始日期",
       cn_header="回测开始日期", default_visible=False,
       export_always=True),

    _c("end_date",   "结束日期", "meta", 100, "str", "center", False, None,
       "回测结束日期",
       cn_header="回测结束日期", default_visible=False,
       export_always=True),

    _c("task_id",    "任务ID",   "meta", 100, "str", "left",   False, None,
       "任务唯一标识",
       cn_header="任务ID", default_visible=False,
       export_always=True),

    _c("error_msg",  "错误信息", "meta", 200, "str", "left",   False, None,
       "失败时的错误信息",
       cn_header="错误信息", default_visible=False,
       export_always=True),
]

# ── 便捷视图 ─────────────────────────────────────────────────────── #

def get_default_visible() -> list[ColumnDefinition]:
    """返回默认可见列（default_visible=True 且 group != 'meta'）。"""
    return [c for c in COLUMN_REGISTRY if c.default_visible and c.group != "meta"]


def get_by_key(key: str) -> ColumnDefinition | None:
    """按 key 查找列定义，找不到返回 None。"""
    for c in COLUMN_REGISTRY:
        if c.key == key:
            return c
    return None


def get_by_group(group: str) -> list[ColumnDefinition]:
    """返回指定分组的所有列定义。"""
    return [c for c in COLUMN_REGISTRY if c.group == group]


# 注册表中的 key 集合（用于快速校验字段是否已注册）
REGISTERED_KEYS: frozenset[str] = frozenset(c.key for c in COLUMN_REGISTRY)
