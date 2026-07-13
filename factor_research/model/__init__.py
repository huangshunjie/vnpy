"""
factor_research/model/__init__.py

Factor Research 数据模型定义。

所有模型均为纯数据容器（dataclass），不含业务逻辑。
上层引擎和 Widget 通过这些模型传递数据，避免直接依赖 VeighNa 内部对象。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

# DataFrame 类型别名：index=datetime, columns=[open,high,low,close,volume]
# 仅用于类型注解，运行时不 import pandas
BarDataFrame = "pd.DataFrame"


@dataclass
class LoadParams:
    """
    数据加载请求参数。

    由 LeftPanel._collect_params() 产生，经 dispatcher 传递给 DataEngine。
    """
    vt_symbol: str          # 合约代码，格式 "symbol.exchange"
    start: date             # 开始日期
    end: date               # 结束日期
    interval: str = "d"     # K线周期，对应 vnpy Interval.value


@dataclass
class LoadResult:
    """
    数据加载结果。

    DataEngine.load_bars() 的返回值，供子引擎消费。
    """
    vt_symbol: str
    interval: str
    start: date
    end: date
    count: int = 0
    success: bool = False
    error: str = ""
    # 实际数据存放在 DataEngine 的缓存中，通过 cache_key 取用
    cache_key: str = ""

    def __str__(self) -> str:
        if self.success:
            return f"LoadResult OK: {self.vt_symbol} {self.interval} {self.count} bars"
        return f"LoadResult FAIL: {self.vt_symbol} {self.error}"


@dataclass
class BarOverviewItem:
    """
    数据库中某合约 K 线数据概览（对 VeighNa BarOverview 的轻量封装）。
    供 LeftPanel 未来做股票池选择时展示可用数据。
    """
    vt_symbol: str
    interval: str
    count: int
    start: date | None
    end: date | None


@dataclass
class FactorParams:
    """
    因子计算参数，由 LeftPanel 配置区收集，贯穿整个计算链路。
    """
    factor_type: str = ""           # FactorType.value
    factor_name: str = ""
    frequency: str = "daily"        # FrequencyType.value
    start: date | None = None
    end: date | None = None
    normalization: str = "zscore"   # NormalizationMethod.value
    neutralization: str | None = None  # NeutralizeMethod.value | None
    symbols: list[str] = field(default_factory=list)  # vt_symbol 列表

    # 计算参数（可由 LeftPanel 配置，有合理默认值）
    lag:          int = 5    # 远期收益持有期（天）
    n_quantiles:  int = 5    # 分层档数
    max_lag:      int = 20   # IC Decay 最大持有期


    @classmethod
    def from_dict(cls, d: dict) -> "FactorParams":
        """从 LeftPanel._collect_params() 产生的字典构造实例。"""
        ft = d.get("factor_type")
        freq = d.get("frequency")
        norm = d.get("normalization")
        neutral = d.get("neutralization")
        return cls(
            factor_type=ft.value if ft is not None else "",
            factor_name=d.get("factor_name", ""),
            frequency=freq.value if freq is not None else "daily",
            start=d.get("start"),
            end=d.get("end"),
            normalization=norm.value if norm is not None else "zscore",
            neutralization=neutral.value if neutral is not None else None,
            symbols=d.get("symbols", []),
            lag=int(d.get("lag", 5)),
            n_quantiles=int(d.get("n_quantiles", 5)),
            max_lag=int(d.get("max_lag", 20)),
        )


@dataclass
class ColumnStat:
    """单列的统计摘要。"""
    name: str
    mean: float
    std: float
    min_val: float
    max_val: float
    missing_count: int
    missing_pct: float      # 0.0 ~ 1.0


@dataclass
class OverviewSummary:
    """
    因子概览 Tab 的数据容器。

    由 DataEngine.compute_overview(df) 计算，经 EVENT_FACTOR_PLOT_READY
    {"tab": "overview", "payload": OverviewSummary} 传递给 OverviewTab。
    """
    vt_symbol: str
    interval: str
    data_start: date | None
    data_end: date | None
    total_bars: int
    column_stats: list[ColumnStat] = field(default_factory=list)

    @property
    def date_range_days(self) -> int:
        """数据时间跨度（自然日数）。"""
        if self.data_start and self.data_end:
            return (self.data_end - self.data_start).days
        return 0


@dataclass
class IcStats:
    """
    IC / RankIC 统计结果容器。

    由 IcEngine.compute() 计算，经 EVENT_FACTOR_PLOT_READY
    {"tab": "ic", "payload": IcStats} 传递给 IcTab。
    """
    vt_symbol: str
    factor_name: str
    lag: int                        # 远期收益持有期（天）

    # IC（Pearson）
    ic_mean: float = float("nan")
    ic_std: float = float("nan")
    icir: float = float("nan")
    ic_positive_rate: float = float("nan")   # IC > 0 的比例

    # RankIC（Spearman）
    rank_ic_mean: float = float("nan")
    rank_ic_std: float = float("nan")
    rank_icir: float = float("nan")
    rank_ic_positive_rate: float = float("nan")

    # 样本信息
    sample_size: int = 0            # 用于计算的有效时序点数
    ic_series_len: int = 0          # IC 序列长度（单合约等于 sample_size）

    def is_valid(self) -> bool:
        """是否有有效计算结果。"""
        import math
        return self.sample_size > 0 and not math.isnan(self.ic_mean)

    # 参与计算的合约数（多合约截面均值时 > 1）
    n_symbols: int = 1

    # IC / RankIC 时序序列（用于 IcSeriesTab 绘图）
    # index = datetime, values = float；默认 None 表示未计算
    ic_series: "pd.Series | None" = field(default=None)
    rank_ic_series: "pd.Series | None" = field(default=None)


@dataclass
class DecayPoint:
    """单个 lag 的 IC Decay 数据点。"""
    lag: int
    ic_mean: float = float("nan")
    rank_ic_mean: float = float("nan")
    icir: float = float("nan")
    rank_icir: float = float("nan")
    sample_size: int = 0


@dataclass
class DecayResult:
    """
    IC Decay 计算结果容器。

    由 DecayEngine.compute() 生成，经 EVENT_FACTOR_PLOT_READY
    {"tab": "decay", "payload": DecayResult} 传递给 DecayTab。
    """
    vt_symbol: str
    factor_name: str
    max_lag: int
    points: list[DecayPoint] = field(default_factory=list)

    @property
    def lags(self) -> list[int]:
        return [p.lag for p in self.points]

    @property
    def ic_means(self) -> list[float]:
        return [p.ic_mean for p in self.points]

    @property
    def rank_ic_means(self) -> list[float]:
        return [p.rank_ic_mean for p in self.points]

    @property
    def icirs(self) -> list[float]:
        return [p.icir for p in self.points]

    @property
    def best_lag(self) -> int:
        """IC 绝对值最大处的 lag（最优持有期）。"""
        import math
        valid = [(p.lag, abs(p.ic_mean)) for p in self.points
                 if not math.isnan(p.ic_mean)]
        if not valid:
            return 1
        return max(valid, key=lambda t: t[1])[0]

    n_symbols: int = 1   # 参与计算的合约数

    def is_valid(self) -> bool:
        return len(self.points) > 0


@dataclass
class QuantileResult:
    """
    分层收益计算结果容器。

    由 QuantileEngine.compute() 生成，经 EVENT_FACTOR_PLOT_READY
    {"tab": "quantile", "payload": QuantileResult} 传递给 QuantileTab。
    """
    vt_symbol: str
    factor_name: str
    lag: int
    n_quantiles: int

    # 各档位标签列表，如 ["Q1","Q2","Q3","Q4","Q5"]
    quantile_labels: list[str] = field(default_factory=list)

    # 各档位平均远期收益序列（时序），index=datetime，key=档位标签
    # 用 dict[str, pd.Series] 存储；TYPE_CHECKING 下声明类型
    quantile_returns: "dict[str, pd.Series]" = field(default_factory=dict)

    # 各档位累计收益序列（时序），index=datetime，key=档位标签
    cumulative_returns: "dict[str, pd.Series]" = field(default_factory=dict)

    # Long-Short 累计收益（Q_last - Q_first）
    long_short_series: "pd.Series | None" = field(default=None)

    # 各档位年化收益（标量），key=档位标签
    annualized_returns: "dict[str, float]" = field(default_factory=dict)

    # 单调性评分（Spearman(档位编号, 年化收益)），范围 [-1,1]
    monotonicity_score: float = float("nan")

    # Long-Short 年化收益
    long_short_annualized: float = float("nan")

    # 样本量（有效时序点数）
    sample_size: int = 0

    # 参与计算的合约数（多合约截面均值时 > 1）
    n_symbols: int = 1

    def is_valid(self) -> bool:
        return self.sample_size > 0 and len(self.cumulative_returns) > 0


@dataclass
class IcDistStats:
    """
    IC 序列分布统计结果容器。

    由 IcDistributionTab._compute_stats() 在 UI 线程直接计算，
    不经过独立引擎（复用 IcStats.ic_series，无额外 IO）。
    """
    vt_symbol: str
    factor_name: str

    # 基础统计
    count: int = 0
    mean: float = float("nan")
    std: float = float("nan")

    # 分布形状
    skewness: float = float("nan")      # 偏度
    kurtosis: float = float("nan")      # 超额峰度（Fisher，正态=0）

    # JB 正态性检验
    jb_stat: float = float("nan")       # Jarque-Bera 统计量
    jb_pvalue: float = float("nan")     # p 值
    is_normal: bool = False             # p > 0.05 则视为正态

    def is_valid(self) -> bool:
        import math
        return self.count > 0 and not math.isnan(self.mean)


@dataclass
class PerfStats:
    """单条曲线的绩效统计（多头/空头/Long-Short 各持有一个）。"""
    label: str
    ann_return: float = float("nan")    # 年化收益
    max_drawdown: float = float("nan")  # 最大回撤（负值，如 -0.15 = -15%）
    sharpe: float = float("nan")        # Sharpe 比率（无风险利率=0）
    calmar: float = float("nan")        # Calmar = ann_return / |mdd|


@dataclass
class LongShortStats:
    """
    Long-Short 绩效结果容器。

    由 LongShortTab._compute_perf() 在 UI 线程直接计算，
    复用 QuantileResult 中已有的累计收益序列。
    """
    vt_symbol: str
    factor_name: str
    lag: int

    long_stats:       PerfStats | None = None   # Q_last（多头）
    short_stats:      PerfStats | None = None   # Q_first（空头）
    ls_stats:         PerfStats | None = None   # Long-Short

    def is_valid(self) -> bool:
        return self.ls_stats is not None


@dataclass
class ScoreDimension:
    """单个评分维度的结果。"""
    name: str                       # 维度名称（显示用）
    raw_value: float = float("nan") # 原始指标值
    score: float = float("nan")     # 归一化得分 [0, 100]
    weight: float = 1.0             # 权重
    description: str = ""           # 简短说明


@dataclass
class FactorScore:
    """
    因子综合评分结果容器。

    由 ScoreTab._compute_score() 在 UI 线程计算，
    汇总 IcStats + QuantileResult 两个来源的指标。
    """
    vt_symbol: str
    factor_name: str

    dimensions: list[ScoreDimension] = field(default_factory=list)

    # 加权综合得分 [0, 100]
    total_score: float = float("nan")

    # 等级：S / A / B / C / D
    grade: str = "—"

    def is_valid(self) -> bool:
        import math
        return len(self.dimensions) > 0 and not math.isnan(self.total_score)

    @staticmethod
    def grade_from_score(score: float) -> str:
        if score >= 85:
            return "S"
        if score >= 70:
            return "A"
        if score >= 55:
            return "B"
        if score >= 40:
            return "C"
        return "D"
