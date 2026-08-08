"""
quant_research/model/kline_event_model.py

K线事件研究数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime as dt
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class EventSamplingRule(Enum):
    """事件采样规则"""
    ALL = "all"                    # 所有事件
    FIRST_TRIGGER = "first"        # 每个标的首次触发
    COOLDOWN = "cooldown"          # 冷却期（N日内同标的只计一次）
    NON_OVERLAP = "non_overlap"    # 完全不重叠（考虑holding period）


@dataclass
class ForwardReturn:
    """未来收益记录"""
    period: int                    # 持有期（天数）
    return_pct: float             # 收益率
    cum_return: float             # 累积收益
    mfe: float                    # 最大有利变动
    mae: float                    # 最大不利变动
    hit_stop_loss: bool = False   # 是否触及止损
    hit_take_profit: bool = False # 是否触及止盈


@dataclass
class EventRecord:
    """
    K线事件记录
    每次条件触发都会生成一个EventRecord
    """
    event_id: str = ""
    research_id: str = ""          # 所属研究ID
    
    # 事件基本信息
    symbol: str = ""
    datetime: dt = field(default_factory=dt.now)
    condition_id: str = ""         # 触发条件ID
    condition_name: str = ""       # 条件名称
    
    # 事件时的快照数据
    entry_price: float = 0.0
    entry_open: float = 0.0
    entry_high: float = 0.0
    entry_low: float = 0.0
    entry_close: float = 0.0
    entry_volume: float = 0.0
    entry_amount: float = 0.0
    
    # K线特征快照（事件发生时的所有特征值）
    feature_snapshot: Dict[str, float] = field(default_factory=dict)
    # 例如：
    # {
    #     "return_1": -0.05,
    #     "body_ratio": 0.8,
    #     "lower_shadow_ratio": 0.4,
    #     "volume_ratio": 2.5,
    #     "ma5": 10.5,
    #     "atr20": 0.8
    # }
    
    # 市场环境信息
    market_state: str = ""         # 市场状态：bull/bear/sideways
    industry: str = ""             # 行业
    market_cap: float = 0.0        # 市值
    
    # 未来收益（多个持有期）
    forward_returns: List[ForwardReturn] = field(default_factory=list)
    # 例如：[1日收益, 3日收益, 5日收益, 10日收益, 20日收益]
    
    # 事件标记
    is_outlier: bool = False       # 是否异常值
    is_first_trigger: bool = False # 是否该标的首次触发
    days_since_last: int = 999     # 距离上次触发天数
    
    # 元数据
    created_at: dt = field(default_factory=dt.now)
    notes: str = ""


@dataclass
class EventStatistics:
    """
    事件统计结果
    对一组EventRecord进行统计分析的结果
    """
    research_id: str = ""
    
    # 样本信息
    total_events: int = 0          # 总事件数
    unique_symbols: int = 0        # 不重复标的数
    date_range_start: str = ""     # 开始日期
    date_range_end: str = ""       # 结束日期
    years_covered: float = 0.0     # 覆盖年数
    
    # 按持有期的统计（key=持有期天数）
    period_stats: Dict[int, 'PeriodStatistics'] = field(default_factory=dict)
    # 例如：
    # {
    #     1: PeriodStatistics(mean_return=0.015, ...),
    #     3: PeriodStatistics(mean_return=0.032, ...),
    #     5: PeriodStatistics(mean_return=0.048, ...)
    # }
    
    # 分组统计
    by_year: Dict[str, 'GroupStatistics'] = field(default_factory=dict)
    by_industry: Dict[str, 'GroupStatistics'] = field(default_factory=dict)
    by_market_cap: Dict[str, 'GroupStatistics'] = field(default_factory=dict)
    by_market_state: Dict[str, 'GroupStatistics'] = field(default_factory=dict)
    
    # 特征相关性分析
    feature_correlation: Dict[str, float] = field(default_factory=dict)
    # key=特征名, value=与未来收益的相关系数
    
    created_at: dt = field(default_factory=dt.now)


@dataclass
class PeriodStatistics:
    """单个持有期的统计数据"""
    period: int = 0                # 持有期（天数）
    
    # 收益统计
    mean_return: float = 0.0
    median_return: float = 0.0
    std_return: float = 0.0
    min_return: float = 0.0
    max_return: float = 0.0
    
    # 百分位数
    percentile_5: float = 0.0
    percentile_25: float = 0.0
    percentile_75: float = 0.0
    percentile_95: float = 0.0
    
    # 概率统计
    win_rate: float = 0.0          # 盈利概率
    profit_loss_ratio: float = 0.0 # 盈亏比
    
    # 风险指标
    var_95: float = 0.0            # VaR 95%
    cvar_95: float = 0.0           # CVaR 95%
    mean_mfe: float = 0.0          # 平均最大有利变动
    mean_mae: float = 0.0          # 平均最大不利变动
    
    # 相对基准
    benchmark_return: float = 0.0  # 基准收益
    excess_return: float = 0.0     # 超额收益
    information_ratio: float = 0.0 # 信息比率
    
    # 夏普和卡玛
    sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0


@dataclass
class GroupStatistics:
    """分组统计结果"""
    group_name: str = ""           # 组名（如"2024"、"金融"、"大盘"）
    event_count: int = 0           # 该组事件数
    mean_return: float = 0.0       # 平均收益
    win_rate: float = 0.0          # 胜率
    sharpe: float = 0.0            # 夏普比率


@dataclass
class BehaviorResearch:
    """
    K线行为研究记录
    整个研究任务的完整记录
    """
    research_id: str = ""
    name: str = ""
    description: str = ""
    
    # 研究范围
    dataset_id: str = ""           # 数据集ID
    symbols: List[str] = field(default_factory=list)
    date_start: str = ""
    date_end: str = ""
    
    # 研究条件
    condition_id: str = ""
    condition_expression: str = "" # 条件表达式
    condition_name: str = ""
    
    # 特征依赖
    required_features: List[str] = field(default_factory=list)
    
    # 采样规则
    sampling_rule: EventSamplingRule = EventSamplingRule.ALL
    cooldown_days: int = 5
    
    # 未来收益周期
    forward_periods: List[int] = field(default_factory=lambda: [1, 3, 5, 10, 20])
    
    # 研究结果
    total_events: int = 0
    event_ids: List[str] = field(default_factory=list)
    statistics: Optional[EventStatistics] = None
    
    # 研究状态
    status: str = "draft"          # draft/running/completed/failed
    progress: float = 0.0          # 进度 0.0-1.0
    
    # 结论和建议
    conclusion: str = ""
    recommended_actions: List[str] = field(default_factory=list)
    # 例如：
    # ["生成Alpha因子: lower_shadow_ratio",
    #  "创建条件监控: 大阴线底部反转",
    #  "生成回测策略"]
    
    # 版本信息
    feature_version: str = ""      # 特征版本（用于复现）
    data_version: str = ""         # 数据版本
    
    # 元数据
    created_by: str = ""
    created_at: dt = field(default_factory=dt.now)
    updated_at: dt = field(default_factory=dt.now)
    completed_at: Optional[dt] = None
    
    # 标签
    tags: List[str] = field(default_factory=list)
    
    # 关联
    related_experiments: List[str] = field(default_factory=list)
    related_strategies: List[str] = field(default_factory=list)


@dataclass
class FeatureImportance:
    """
    特征重要性分析
    用于识别哪些K线特征对未来收益最有预测力
    """
    research_id: str = ""
    
    # 特征排名
    feature_rankings: List['FeatureRank'] = field(default_factory=list)
    
    # 相关性矩阵
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # 主成分分析
    pca_explained_variance: List[float] = field(default_factory=list)
    
    created_at: dt = field(default_factory=dt.now)


@dataclass
class FeatureRank:
    """单个特征的排名信息"""
    feature_name: str = ""
    correlation: float = 0.0       # 与未来收益的相关性
    information_coefficient: float = 0.0  # IC
    rank_ic: float = 0.0
    predictive_power: float = 0.0  # 预测力得分
    stability: float = 0.0         # 稳定性（跨时间、跨行业）
    rank: int = 0                  # 排名
