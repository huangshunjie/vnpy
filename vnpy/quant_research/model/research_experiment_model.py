"""
quant_research/model/research_experiment_model.py

K线行为研究实验模型
用于管理完整的研究实验生命周期
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from .kline_event_model import EventSamplingRule, EventStatistics


class ExperimentStatus(Enum):
    """研究实验状态"""
    DRAFT = "draft"                # 草稿
    CONFIGURING = "configuring"    # 配置中
    READY = "ready"                # 就绪待执行
    RUNNING = "running"            # 执行中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"              # 执行失败
    ARCHIVED = "archived"          # 已归档


class ExperimentPriority(Enum):
    """实验优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BehaviorResearchExperiment:
    """
    K线行为研究实验记录
    记录完整的研究配置和结果
    """
    # 基本信息
    experiment_id: str = ""
    name: str = ""
    description: str = ""
    category: str = "kline_behavior"  # 实验类别
    priority: ExperimentPriority = ExperimentPriority.MEDIUM
    
    # 研究范围配置
    dataset_id: str = ""              # 数据集ID（引用dataset_registry）
    symbols: List[str] = field(default_factory=list)  # 股票列表
    stock_pool_id: str = ""           # 股票池ID（如果使用股票池）
    date_start: str = ""              # 开始日期 YYYY-MM-DD
    date_end: str = ""                # 结束日期 YYYY-MM-DD
    interval: str = "1d"              # K线周期：1d/1w/1m
    adjust_type: str = "hfq"          # 复权方式：hfq/qfq/none
    
    # 数据过滤条件
    filter_suspended: bool = True     # 过滤停牌
    filter_st: bool = True            # 过滤ST
    filter_new_stock_days: int = 60   # 过滤上市N天内的新股
    min_price: float = 0.0            # 最低价格过滤
    max_price: float = 0.0            # 最高价格过滤（0表示不限制）
    
    # 研究条件配置
    condition_id: str = ""            # 条件ID（如果引用已有条件）
    condition_expression: str = ""    # 条件表达式
    condition_name: str = ""          # 条件名称
    condition_description: str = ""   # 条件描述
    
    # 特征依赖
    required_features: List[str] = field(default_factory=list)
    # 自动从condition_expression解析，例如：
    # ["return_1", "lower_shadow_ratio", "volume_ratio", "ma20"]
    
    # 采样规则配置
    sampling_rule: EventSamplingRule = EventSamplingRule.ALL
    cooldown_days: int = 5            # 冷却期天数
    max_events_per_symbol: int = 0    # 每个标的最大事件数（0=不限制）
    
    # 未来收益分析配置
    forward_periods: List[int] = field(default_factory=lambda: [1, 3, 5, 10, 20])
    benchmark_symbol: str = ""        # 基准指数（如"000300.SH"）
    
    # 成本假设
    commission_rate: float = 0.0003   # 佣金费率
    slippage_rate: float = 0.001      # 滑点
    
    # 研究结果
    total_events: int = 0             # 总事件数
    valid_events: int = 0             # 有效事件数（排除异常值后）
    event_ids: List[str] = field(default_factory=list)  # 事件ID列表
    statistics: Optional[EventStatistics] = None  # 统计结果
    
    # 实验状态
    status: ExperimentStatus = ExperimentStatus.DRAFT
    progress: float = 0.0             # 进度 0.0-1.0
    current_step: str = ""            # 当前步骤描述
    error_message: str = ""           # 错误信息
    
    # 结论和建议
    conclusion: str = ""              # 研究结论
    key_findings: List[str] = field(default_factory=list)  # 关键发现
    recommended_actions: List[str] = field(default_factory=list)
    # 例如：
    # ["生成Alpha因子: lower_shadow_ratio",
    #  "创建条件监控: 大阴线底部反转",
    #  "生成回测策略: 反转买入策略"]
    
    # 显著性指标
    is_significant: bool = False      # 是否显著有效
    significance_score: float = 0.0   # 显著性得分 0-100
    stability_score: float = 0.0      # 稳定性得分 0-100
    profitability_score: float = 0.0  # 盈利性得分 0-100
    
    # 版本信息（用于结果可复现）
    feature_version: str = "v1.0"     # 特征计算版本
    data_version: str = ""            # 数据版本/时间戳
    condition_version: str = ""       # 条件版本哈希
    experiment_version: int = 1       # 实验版本（同一研究的多次运行）
    
    # 元数据
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 标签和分类
    tags: List[str] = field(default_factory=list)
    # 例如：["反转", "大阴线", "底部", "成交量"]
    
    # 关联
    parent_experiment_id: str = ""    # 父实验ID（如果是派生研究）
    related_experiments: List[str] = field(default_factory=list)
    related_strategies: List[str] = field(default_factory=list)
    related_factors: List[str] = field(default_factory=list)
    
    # 备注
    notes: str = ""
    
    # 执行配置
    parallel_workers: int = 4         # 并行处理数
    use_cache: bool = True            # 是否使用特征缓存
    save_event_details: bool = True   # 是否保存事件详情
    
    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "priority": self.priority.value if isinstance(self.priority, ExperimentPriority) else self.priority,
            "dataset_id": self.dataset_id,
            "symbols": self.symbols,
            "stock_pool_id": self.stock_pool_id,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "interval": self.interval,
            "adjust_type": self.adjust_type,
            "filter_suspended": self.filter_suspended,
            "filter_st": self.filter_st,
            "filter_new_stock_days": self.filter_new_stock_days,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "condition_id": self.condition_id,
            "condition_expression": self.condition_expression,
            "condition_name": self.condition_name,
            "condition_description": self.condition_description,
            "required_features": self.required_features,
            "sampling_rule": self.sampling_rule.value if isinstance(self.sampling_rule, EventSamplingRule) else self.sampling_rule,
            "cooldown_days": self.cooldown_days,
            "max_events_per_symbol": self.max_events_per_symbol,
            "forward_periods": self.forward_periods,
            "benchmark_symbol": self.benchmark_symbol,
            "commission_rate": self.commission_rate,
            "slippage_rate": self.slippage_rate,
            "total_events": self.total_events,
            "valid_events": self.valid_events,
            "event_ids": self.event_ids,
            "status": self.status.value if isinstance(self.status, ExperimentStatus) else self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "error_message": self.error_message,
            "conclusion": self.conclusion,
            "key_findings": self.key_findings,
            "recommended_actions": self.recommended_actions,
            "is_significant": self.is_significant,
            "significance_score": self.significance_score,
            "stability_score": self.stability_score,
            "profitability_score": self.profitability_score,
            "feature_version": self.feature_version,
            "data_version": self.data_version,
            "condition_version": self.condition_version,
            "experiment_version": self.experiment_version,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tags": self.tags,
            "parent_experiment_id": self.parent_experiment_id,
            "related_experiments": self.related_experiments,
            "related_strategies": self.related_strategies,
            "related_factors": self.related_factors,
            "notes": self.notes,
            "parallel_workers": self.parallel_workers,
            "use_cache": self.use_cache,
            "save_event_details": self.save_event_details,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BehaviorResearchExperiment":
        """从字典创建实例（JSON反序列化）"""
        # 转换枚举类型
        if "status" in data and isinstance(data["status"], str):
            data["status"] = ExperimentStatus(data["status"])
        if "priority" in data and isinstance(data["priority"], str):
            data["priority"] = ExperimentPriority(data["priority"])
        if "sampling_rule" in data and isinstance(data["sampling_rule"], str):
            data["sampling_rule"] = EventSamplingRule(data["sampling_rule"])
        
        # 转换日期时间
        for field_name in ["created_at", "updated_at", "started_at", "completed_at"]:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExperimentTemplate:
    """
    实验模板
    预设的常用研究模式，可快速创建实验
    """
    template_id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""
    
    # 预设配置
    condition_expression: str = ""
    required_features: List[str] = field(default_factory=list)
    sampling_rule: EventSamplingRule = EventSamplingRule.COOLDOWN
    cooldown_days: int = 5
    forward_periods: List[int] = field(default_factory=lambda: [1, 3, 5, 10, 20])
    
    # 标签
    tags: List[str] = field(default_factory=list)
    
    # 使用次数
    usage_count: int = 0
    
    # 元数据
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    is_builtin: bool = False  # 是否内置模板


# ========================================================================
# 内置实验模板
# ========================================================================

BUILTIN_EXPERIMENT_TEMPLATES = [
    ExperimentTemplate(
        template_id="reversal_big_red_candle",
        name="大阴线底部反转",
        description="大跌+长下影线+放量，寻找底部反转机会",
        category="反转",
        condition_expression="(return_1 < -0.03) & (lower_shadow_ratio > 0.4) & (volume_ratio > 1.5)",
        required_features=["return_1", "lower_shadow_ratio", "volume_ratio"],
        sampling_rule=EventSamplingRule.COOLDOWN,
        cooldown_days=5,
        tags=["反转", "大阴线", "底部", "成交量"],
        is_builtin=True,
    ),
    
    ExperimentTemplate(
        template_id="breakout_new_high",
        name="突破新高",
        description="创20日新高+放量+均线多头排列",
        category="突破",
        condition_expression="(new_high_20 == 1) & (volume_ratio > 1.2) & (ma_slope_20 > 0)",
        required_features=["new_high_20", "volume_ratio", "ma_slope_20"],
        sampling_rule=EventSamplingRule.COOLDOWN,
        cooldown_days=10,
        tags=["突破", "新高", "趋势", "成交量"],
        is_builtin=True,
    ),
    
    ExperimentTemplate(
        template_id="rsi_oversold_reversal",
        name="RSI超卖反转",
        description="RSI低于30后首次向上穿越",
        category="反转",
        condition_expression="(rsi_14 < 30) & (rsi_14 > rsi_14.shift(1))",
        required_features=["rsi_14"],
        sampling_rule=EventSamplingRule.FIRST_TRIGGER,
        tags=["RSI", "超卖", "反转"],
        is_builtin=True,
    ),
    
    ExperimentTemplate(
        template_id="pullback_to_ma20",
        name="回踩MA20支撑",
        description="上升趋势中回踩MA20获得支撑",
        category="回调买入",
        condition_expression="(ma_slope_20 > 0) & (price_to_ma20 > -0.03) & (price_to_ma20 < 0.01) & (is_hammer == 1)",
        required_features=["ma_slope_20", "price_to_ma20", "is_hammer"],
        sampling_rule=EventSamplingRule.COOLDOWN,
        cooldown_days=10,
        tags=["回调", "均线支撑", "趋势跟踪"],
        is_builtin=True,
    ),
    
    ExperimentTemplate(
        template_id="volume_spike_pattern",
        name="放量形态突破",
        description="成交量突增2倍以上+阳线",
        category="成交量",
        condition_expression="(volume_spike == 1) & (is_green == 1) & (body_ratio > 0.5)",
        required_features=["volume_spike", "is_green", "body_ratio"],
        sampling_rule=EventSamplingRule.COOLDOWN,
        cooldown_days=5,
        tags=["成交量", "放量", "突破"],
        is_builtin=True,
    ),
]


def get_template(template_id: str) -> Optional[ExperimentTemplate]:
    """获取模板"""
    for template in BUILTIN_EXPERIMENT_TEMPLATES:
        if template.template_id == template_id:
            return template
    return None


def list_templates(category: Optional[str] = None) -> List[ExperimentTemplate]:
    """列出模板"""
    if category:
        return [t for t in BUILTIN_EXPERIMENT_TEMPLATES if t.category == category]
    return BUILTIN_EXPERIMENT_TEMPLATES.copy()
