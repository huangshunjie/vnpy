"""
quant_research/behavior/sampling_engine.py

事件采样引擎
提供多种采样规则，避免事件重复和过拟合
"""
from __future__ import annotations
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime

from ..model.kline_event_model import EventRecord, EventSamplingRule


class SamplingEngine:
    """事件采样引擎"""
    
    def __init__(self):
        pass
    
    def sample(
        self,
        events: List[EventRecord],
        rule: EventSamplingRule,
        cooldown_days: int = 5,
        holding_period: int = 5,
        max_events_per_symbol: int = 0
    ) -> List[EventRecord]:
        """
        对事件进行采样
        
        Args:
            events: 原始事件列表
            rule: 采样规则
            cooldown_days: 冷却期天数
            holding_period: 持有期
            max_events_per_symbol: 每个标的最大事件数
        """
        if not events:
            return []
        
        if rule == EventSamplingRule.ALL:
            sampled = events.copy()
        elif rule == EventSamplingRule.FIRST_TRIGGER:
            sampled = self._sample_first(events)
        elif rule == EventSamplingRule.COOLDOWN:
            sampled = self._sample_cooldown(events, cooldown_days)
        elif rule == EventSamplingRule.NON_OVERLAP:
            sampled = self._sample_non_overlap(events, holding_period)
        else:
            sampled = events.copy()
        
        if max_events_per_symbol > 0:
            sampled = self._limit_per_symbol(sampled, max_events_per_symbol)
        
        self._mark_first_trigger(sampled)
        return sampled
    
    def _sample_first(self, events: List[EventRecord]) -> List[EventRecord]:
        """每个标的只保留首次触发"""
        grouped = self._group_by_symbol(events)
        sampled = []
        for symbol, symbol_events in grouped.items():
            sorted_events = sorted(symbol_events, key=lambda e: e.datetime)
            sampled.append(sorted_events[0])
        return sampled
    
    def _sample_cooldown(self, events: List[EventRecord], cooldown_days: int) -> List[EventRecord]:
        """冷却期采样"""
        grouped = self._group_by_symbol(events)
        sampled = []
        
        for symbol, symbol_events in grouped.items():
            sorted_events = sorted(symbol_events, key=lambda e: e.datetime)
            last_selected = None
            
            for event in sorted_events:
                if last_selected is None:
                    sampled.append(event)
                    last_selected = event
                else:
                    days_diff = (event.datetime - last_selected.datetime).days
                    if days_diff >= cooldown_days:
                        sampled.append(event)
                        last_selected = event
                        event.days_since_last = days_diff
        
        return sampled
    
    def _sample_non_overlap(self, events: List[EventRecord], holding_period: int) -> List[EventRecord]:
        """非重叠采样"""
        grouped = self._group_by_symbol(events)
        sampled = []
        
        for symbol, symbol_events in grouped.items():
            sorted_events = sorted(symbol_events, key=lambda e: e.datetime)
            last_selected = None
            
            for event in sorted_events:
                if last_selected is None:
                    sampled.append(event)
                    last_selected = event
                else:
                    days_diff = (event.datetime - last_selected.datetime).days
                    if days_diff >= holding_period:
                        sampled.append(event)
                        last_selected = event
        
        return sampled
    
    def _limit_per_symbol(self, events: List[EventRecord], max_events: int) -> List[EventRecord]:
        """限制每个标的的事件数"""
        grouped = self._group_by_symbol(events)
        limited = []
        for symbol, symbol_events in grouped.items():
            sorted_events = sorted(symbol_events, key=lambda e: e.datetime)
            limited.extend(sorted_events[:max_events])
        return limited
    
    def _group_by_symbol(self, events: List[EventRecord]) -> Dict[str, List[EventRecord]]:
        """按标的分组"""
        grouped = {}
        for event in events:
            if event.symbol not in grouped:
                grouped[event.symbol] = []
            grouped[event.symbol].append(event)
        return grouped
    
    def _mark_first_trigger(self, events: List[EventRecord]) -> None:
        """标记首次触发"""
        grouped = self._group_by_symbol(events)
        for symbol, symbol_events in grouped.items():
            sorted_events = sorted(symbol_events, key=lambda e: e.datetime)
            if sorted_events:
                sorted_events[0].is_first_trigger = True
    
    def balance_by_year(self, events: List[EventRecord], events_per_year: Optional[int] = None) -> List[EventRecord]:
        """按年度平衡样本"""
        year_groups = {}
        for event in events:
            if isinstance(event.datetime, datetime):
                year = event.datetime.year
                if year not in year_groups:
                    year_groups[year] = []
                year_groups[year].append(event)
        
        if not year_groups:
            return events
        
        if events_per_year is None:
            events_per_year = min(len(v) for v in year_groups.values())
        
        balanced = []
        for year, year_events in year_groups.items():
            if len(year_events) <= events_per_year:
                balanced.extend(year_events)
            else:
                indices = np.random.choice(len(year_events), events_per_year, replace=False)
                balanced.extend([year_events[i] for i in indices])
        
        return balanced
    
    def remove_outliers(self, events: List[EventRecord], period: int = 5, std_threshold: float = 3.0) -> List[EventRecord]:
        """移除异常值"""
        returns = []
        for event in events:
            for fr in event.forward_returns:
                if fr.period == period:
                    returns.append(fr.return_pct)
                    break
        
        if not returns:
            return events
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        lower = mean_return - std_threshold * std_return
        upper = mean_return + std_threshold * std_return
        
        filtered = []
        for event in events:
            for fr in event.forward_returns:
                if fr.period == period:
                    if lower <= fr.return_pct <= upper:
                        filtered.append(event)
                    else:
                        event.is_outlier = True
                    break
        
        return filtered
