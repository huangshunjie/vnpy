"""
Multi-Timeframe Auto Loader
自动分析策略需要的数据周期并加载对应数据
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, timedelta
from vnpy.trader.constant import Interval

if TYPE_CHECKING:
    from .strategy import Strategy
    from .mtf_context import DataRequirement


def analyze_strategy_data_requirements(
    strategy: "Strategy",
    anchor_interval: Interval,
    anchor_bar_count: int
) -> "DataRequirement":
    """
    分析策略需要的所有数据周期
    
    Args:
        strategy: 策略对象
        anchor_interval: 锚点周期（UI设置的K线周期，用于确定数据范围）
        anchor_bar_count: 锚点周期需要的K线数量
        
    Returns:
        DataRequirement 对象，包含所有需要的周期
        
    核心逻辑：
        - 如果策略只用单一周期：execution_interval = anchor_interval
        - 如果策略混合多周期：execution_interval = 最小周期（最高粒度）
        
    示例：
        - 买入条件=日线，卖出条件=日线 → execution_interval = 日线
        - 买入条件=日线，卖出条件=5分钟 → execution_interval = 5分钟
          （主循环遍历5分钟K线，日线条件用分钟close合成虚拟日线评估）
    """
    from .mtf_context import DataRequirement, analyze_data_requirements
    
    # 分析买入条件需要的周期
    buy_req = analyze_data_requirements(
        strategy.buy_tree,
        anchor_interval
    )
    
    # 分析卖出条件需要的周期
    sell_req = analyze_data_requirements(
        strategy.sell_tree,
        anchor_interval
    )
    
    # 合并所有需要的周期
    combined_req = DataRequirement(strategy_execution_interval=anchor_interval)
    for interval in buy_req.intervals:
        combined_req.add_interval(interval)
    for interval in sell_req.intervals:
        combined_req.add_interval(interval)
    
    # 添加锚点周期本身（用于数据范围确定）
    combined_req.add_interval(anchor_interval)
    
    # ═══════════════════════════════════════════════════════════
    # 核心改动：确定 execution_interval（主循环步长）
    # ═══════════════════════════════════════════════════════════
    all_intervals = list(combined_req.intervals)
    
    if len(all_intervals) == 1:
        # 单周期策略：execution_interval = 该周期
        execution_interval = all_intervals[0]
    else:
        # 多周期策略：execution_interval = 最小周期（最高粒度）
        # 周期优先级：分钟 > 5分钟 > 15分钟 > 30分钟 > 60分钟 > 日线
        interval_priority = {
            Interval.MINUTE: 1,
            Interval.MINUTE_5: 5,
            Interval.MINUTE_15: 15,
            Interval.MINUTE_30: 30,
            Interval.HOUR: 60,
            Interval.DAILY: 1440,  # 一天 = 1440分钟
            Interval.WEEKLY: 10080,  # 一周
        }
        
        # 找到数值最小的周期（粒度最细）
        min_interval = min(
            all_intervals,
            key=lambda i: interval_priority.get(i, 999999)
        )
        execution_interval = min_interval
    
    # 设置执行周期
    combined_req.strategy_execution_interval = execution_interval
    
    # 添加兼容属性
    combined_req.required_intervals = list(combined_req.intervals)
    combined_req.anchor_interval = anchor_interval
    combined_req.anchor_bar_count = anchor_bar_count
    combined_req.execution_interval = execution_interval  # 使用计算出的执行周期
    
    return combined_req


def get_date_range_from_anchor_bars(bars: list) -> tuple[datetime, datetime]:
    """
    从锚点周期的K线列表中提取日期范围
    
    Args:
        bars: K线列表
        
    Returns:
        (start_date, end_date) 元组
    """
    if not bars:
        # 默认返回最近30天
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        return start_date, end_date
    
    # 从K线中提取起止日期
    start_date = bars[0].datetime
    end_date = bars[-1].datetime
    
    return start_date, end_date