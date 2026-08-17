# -*- coding: utf-8 -*-
"""
K线周期转换器

支持从小周期聚合到大周期：
- 分钟 → 小时/日线
- 小时 → 日线
- 日线 → 周线/月线

Phase 5 - Step 1
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional
from collections import defaultdict

from vnpy.trader.constant import Interval
from vnpy.trader.object import BarData


class BarResampler:
    """
    K线周期转换器
    
    核心算法：
    1. 按目标周期分组（小时/日/周/月）
    2. 每组内聚合 OHLCV
    3. 生成新的 BarData
    """
    
    @staticmethod
    def resample(bars: List[BarData], from_interval: Interval,
                 to_interval: Interval) -> List[BarData]:
        """
        通用周期转换接口
        
        Args:
            bars: 源K线列表
            from_interval: 源周期
            to_interval: 目标周期
        
        Returns:
            转换后的K线列表
        
        Raises:
            ValueError: 不支持的转换类型
        """
        if not bars:
            return []
        
        # 直接调用对应的转换方法
        if from_interval in (Interval.MINUTE, Interval.MINUTE_5, 
                             Interval.MINUTE_15, Interval.MINUTE_30):
            if to_interval == Interval.HOUR:
                return BarResampler._minute_to_hour(bars)
            elif to_interval == Interval.DAILY:
                return BarResampler._minute_to_daily(bars)
        
        if from_interval == Interval.HOUR:
            if to_interval == Interval.DAILY:
                return BarResampler._hour_to_daily(bars)
        
        if from_interval == Interval.DAILY:
            if to_interval == Interval.WEEKLY:
                return BarResampler._daily_to_weekly(bars)
        
        raise ValueError(
            f"不支持的转换: {from_interval.value} → {to_interval.value}"
        )
    
    @staticmethod
    def _minute_to_hour(bars: List[BarData]) -> List[BarData]:
        """
        分钟线 → 小时线
        
        分组规则：按小时分组（按 datetime.hour 划分）
        """
        if not bars:
            return []
        
        # 按小时分组
        groups = defaultdict(list)
        for bar in bars:
            dt = bar.datetime
            # 使用日期 + 小时作为键
            key = (dt.date(), dt.hour)
            groups[key].append(bar)
        
        # 聚合每组
        result = []
        for (date, hour), group_bars in sorted(groups.items()):
            if not group_bars:
                continue
            
            agg_bar = BarResampler._aggregate_bars(
                group_bars,
                # 使用该小时的结束时间（下一个小时的开始）
                datetime(date.year, date.month, date.day, hour, 59, 59)
            )
            result.append(agg_bar)
        
        return result
    
    @staticmethod
    def _minute_to_daily(bars: List[BarData]) -> List[BarData]:
        """
        分钟线 → 日线
        
        分组规则：按交易日分组
        """
        if not bars:
            return []
        
        # 按日期分组
        groups = defaultdict(list)
        for bar in bars:
            date = bar.datetime.date()
            groups[date].append(bar)
        
        # 聚合每组
        result = []
        for date, group_bars in sorted(groups.items()):
            if not group_bars:
                continue
            
            # 日线使用当天 15:00 作为时间戳
            agg_bar = BarResampler._aggregate_bars(
                group_bars,
                datetime(date.year, date.month, date.day, 15, 0, 0)
            )
            result.append(agg_bar)
        
        return result
    
    @staticmethod
    def _hour_to_daily(bars: List[BarData]) -> List[BarData]:
        """
        小时线 → 日线
        
        分组规则：按交易日分组
        """
        # 逻辑与 minute_to_daily 相同
        return BarResampler._minute_to_daily(bars)
    
    @staticmethod
    def _daily_to_weekly(bars: List[BarData]) -> List[BarData]:
        """
        日线 → 周线
        
        分组规则：按自然周分组（周一到周日）
        Python: Monday=0, Sunday=6
        """
        if not bars:
            return []
        
        # 按周分组（使用 ISO 日历的年份和周数）
        groups = defaultdict(list)
        for bar in bars:
            dt = bar.datetime
            # ISO 周：(年, 周数, 星期)
            iso_year, iso_week, _ = dt.isocalendar()
            key = (iso_year, iso_week)
            groups[key].append(bar)
        
        # 聚合每组
        result = []
        for (year, week), group_bars in sorted(groups.items()):
            if not group_bars:
                continue
            
            # 周线使用该周最后一个交易日的时间
            last_bar = max(group_bars, key=lambda b: b.datetime)
            agg_bar = BarResampler._aggregate_bars(group_bars, last_bar.datetime)
            result.append(agg_bar)
        
        return result
    
    @staticmethod
    def daily_to_monthly(bars: List[BarData]) -> List[BarData]:
        """
        日线 → 月线
        
        分组规则：按自然月分组
        注意：Interval 枚举中没有 MONTHLY，此方法作为辅助工具提供
        """
        if not bars:
            return []
        
        # 按月分组
        groups = defaultdict(list)
        for bar in bars:
            dt = bar.datetime
            key = (dt.year, dt.month)
            groups[key].append(bar)
        
        # 聚合每组
        result = []
        for (year, month), group_bars in sorted(groups.items()):
            if not group_bars:
                continue
            
            # 月线使用该月最后一个交易日的时间
            last_bar = max(group_bars, key=lambda b: b.datetime)
            agg_bar = BarResampler._aggregate_bars(group_bars, last_bar.datetime)
            result.append(agg_bar)
        
        return result
    
    @staticmethod
    def _aggregate_bars(bars: List[BarData], target_datetime: datetime) -> BarData:
        """
        聚合一组K线为单根K线
        
        规则：
        - open: 第一根的 open
        - high: 所有 high 的最大值
        - low: 所有 low 的最小值
        - close: 最后一根的 close
        - volume: 所有 volume 的总和
        - datetime: 使用 target_datetime
        
        Args:
            bars: 要聚合的K线列表
            target_datetime: 目标时间戳
        
        Returns:
            聚合后的 BarData
        """
        if not bars:
            raise ValueError("无法聚合空的K线列表")
        
        # 按时间排序确保正确的 open/close
        sorted_bars = sorted(bars, key=lambda b: b.datetime)
        
        first_bar = sorted_bars[0]
        last_bar = sorted_bars[-1]
        
        # 聚合数据
        open_price = first_bar.open_price
        high_price = max(b.high_price for b in bars)
        low_price = min(b.low_price for b in bars)
        close_price = last_bar.close_price
        volume = sum(b.volume for b in bars)
        turnover = sum(b.turnover for b in bars) if hasattr(first_bar, 'turnover') else 0
        open_interest = last_bar.open_interest if hasattr(last_bar, 'open_interest') else 0
        
        # 创建新的 BarData
        agg_bar = BarData(
            symbol=first_bar.symbol,
            exchange=first_bar.exchange,
            datetime=target_datetime,
            interval=first_bar.interval,  # 保持原始周期标记（可以后续修改）
            volume=volume,
            turnover=turnover,
            open_interest=open_interest,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            gateway_name=first_bar.gateway_name if hasattr(first_bar, 'gateway_name') else "",
        )
        
        return agg_bar
    
    @staticmethod
    def estimate_required_bars(target_bars: int, from_interval: Interval,
                                to_interval: Interval) -> int:
        """
        估算为了得到 target_bars 根目标周期K线，需要多少根源周期K线
        
        用于数据加载优化：避免加载过多或过少的基础数据
        
        Args:
            target_bars: 目标K线数量
            from_interval: 源周期
            to_interval: 目标周期
        
        Returns:
            估算的源K线数量
        
        Example:
            要获得 100 根日线，5分钟线大约需要：
            100 天 × 240 分钟/天 ÷ 5 分钟 = 4800 根
        """
        # 定义周期的分钟数（交易时间）
        minutes_per_bar = {
            Interval.MINUTE: 1,
            Interval.MINUTE_5: 5,
            Interval.MINUTE_15: 15,
            Interval.MINUTE_30: 30,
            Interval.HOUR: 60,
            Interval.DAILY: 240,  # 4小时交易时间
            Interval.WEEKLY: 240 * 5,  # 约5个交易日
        }
        
        from_mins = minutes_per_bar.get(from_interval, 1)
        to_mins = minutes_per_bar.get(to_interval, 240)
        
        if from_mins >= to_mins:
            # 源周期 >= 目标周期，1:1 或更少
            return target_bars
        
        # 计算比例，加 20% 缓冲
        ratio = to_mins / from_mins
        return int(target_bars * ratio * 1.2)


# 便捷函数
def minute_to_hour(bars: List[BarData]) -> List[BarData]:
    """分钟线 → 小时线"""
    return BarResampler._minute_to_hour(bars)


def minute_to_daily(bars: List[BarData]) -> List[BarData]:
    """分钟线 → 日线"""
    return BarResampler._minute_to_daily(bars)


def daily_to_weekly(bars: List[BarData]) -> List[BarData]:
    """日线 → 周线"""
    return BarResampler._daily_to_weekly(bars)


def daily_to_monthly(bars: List[BarData]) -> List[BarData]:
    """日线 → 月线"""
    return BarResampler.daily_to_monthly(bars)
