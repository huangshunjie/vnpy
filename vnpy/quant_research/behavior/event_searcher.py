"""
quant_research/behavior/event_searcher.py

事件搜索引擎
基于条件在历史数据中搜索符合条件的K线事件
"""
from __future__ import annotations
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import uuid

from ..model.kline_event_model import (
    EventRecord, 
    EventSamplingRule,
    ForwardReturn
)
from .kline_calculator import KLineFeatureCalculator


class EventSearcher:
    """
    事件搜索引擎
    
    核心功能：
    1. 基于条件表达式搜索历史事件
    2. 支持多种采样规则
    3. 记录事件发生时的特征快照
    4. 计算未来收益
    """
    
    def __init__(self, research_id: str):
        self.research_id = research_id
        self.feature_calculator = KLineFeatureCalculator()
        
    def search_events(
        self,
        data: pd.DataFrame,
        condition_expression: str,
        required_features: List[str],
        sampling_rule: EventSamplingRule = EventSamplingRule.ALL,
        cooldown_days: int = 5,
        forward_periods: List[int] = None
    ) -> List[EventRecord]:
        """
        搜索历史事件
        
        Args:
            data: K线数据
            condition_expression: 条件表达式
            required_features: 需要计算的特征列表
            sampling_rule: 采样规则
            cooldown_days: 冷却期天数
            forward_periods: 未来收益周期
            
        Returns:
            EventRecord列表
        """
        if forward_periods is None:
            forward_periods = [1, 3, 5, 10, 20]
        
        # 1. 计算特征
        data_with_features = self.feature_calculator.calculate(
            data, required_features, use_cache=True
        )
        
        # 2. 评估条件
        trigger_mask = self._evaluate_condition(
            data_with_features, condition_expression, required_features
        )
        
        # 3. 采样事件
        events = self._sample_events(
            data_with_features, trigger_mask, sampling_rule, cooldown_days
        )
        
        # 4. 计算未来收益
        events_with_returns = self._calculate_forward_returns(
            events, data_with_features, forward_periods
        )
        
        return events_with_returns
    
    def search_events_multi_symbol(
        self,
        data_dict: Dict[str, pd.DataFrame],
        condition_expression: str,
        required_features: List[str],
        sampling_rule: EventSamplingRule = EventSamplingRule.ALL,
        cooldown_days: int = 5,
        forward_periods: List[int] = None
    ) -> List[EventRecord]:
        """多标的事件搜索"""
        all_events = []
        
        for symbol, df in data_dict.items():
            if 'symbol' not in df.columns:
                df = df.copy()
                df['symbol'] = symbol
            
            try:
                events = self.search_events(
                    df, condition_expression, required_features,
                    sampling_rule, cooldown_days, forward_periods
                )
                all_events.extend(events)
            except Exception as e:
                print(f"[错误] {symbol} 事件搜索失败: {e}")
        
        return all_events
    
    def _evaluate_condition(
        self, df: pd.DataFrame, condition_expression: str,
        required_features: List[str]
    ) -> pd.Series:
        """评估条件表达式"""
        try:
            namespace = {'df': df, 'np': np, 'pd': pd}
            
            for feature in required_features:
                if feature in df.columns:
                    namespace[feature] = df[feature]
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    namespace[col] = df[col]
            
            result = eval(condition_expression, namespace)
            
            if isinstance(result, pd.Series):
                return result.fillna(False).astype(bool)
            else:
                return pd.Series([result] * len(df), index=df.index).astype(bool)
                
        except Exception as e:
            print(f"[错误] 条件评估失败: {e}")
            return pd.Series([False] * len(df), index=df.index)
    
    def _sample_events(
        self, df: pd.DataFrame, trigger_mask: pd.Series,
        sampling_rule: EventSamplingRule, cooldown_days: int
    ) -> List[EventRecord]:
        """根据采样规则筛选事件"""
        trigger_indices = df.index[trigger_mask].tolist()
        
        if not trigger_indices:
            return []
        
        if sampling_rule == EventSamplingRule.ALL:
            selected_indices = trigger_indices
        elif sampling_rule == EventSamplingRule.FIRST_TRIGGER:
            selected_indices = [trigger_indices[0]]
        elif sampling_rule == EventSamplingRule.COOLDOWN:
            selected_indices = self._apply_cooldown(df, trigger_indices, cooldown_days)
        else:
            selected_indices = trigger_indices
        
        events = [self._create_event_record(df, idx) for idx in selected_indices]
        return events
    
    def _apply_cooldown(
        self, df: pd.DataFrame, trigger_indices: List, cooldown_days: int
    ) -> List:
        """应用冷却期规则"""
        selected = []
        last_idx = None
        
        for idx in trigger_indices:
            if last_idx is None or (idx - last_idx >= cooldown_days):
                selected.append(idx)
                last_idx = idx
        
        return selected
    
    def _create_event_record(self, df: pd.DataFrame, idx: int) -> EventRecord:
        """创建事件记录"""
        row = df.loc[idx]
        event_id = f"EVT-{uuid.uuid4().hex[:12]}"
        
        symbol = row.get('symbol', 'UNKNOWN')
        dt = row.get('datetime', idx)
        if not isinstance(dt, datetime):
            dt = datetime.now()
        
        feature_snapshot = {}
        for col in df.columns:
            if col not in ['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume']:
                val = row[col]
                if pd.notna(val):
                    feature_snapshot[col] = float(val)
        
        return EventRecord(
            event_id=event_id,
            research_id=self.research_id,
            symbol=symbol,
            datetime=dt,
            entry_price=float(row.get('close', 0)),
            entry_open=float(row.get('open', 0)),
            entry_high=float(row.get('high', 0)),
            entry_low=float(row.get('low', 0)),
            entry_close=float(row.get('close', 0)),
            entry_volume=float(row.get('volume', 0)),
            feature_snapshot=feature_snapshot,
        )
    
    def _calculate_forward_returns(
        self, events: List[EventRecord], df: pd.DataFrame,
        forward_periods: List[int]
    ) -> List[EventRecord]:
        """计算未来收益"""
        for event in events:
            event_idx = self._find_event_index(df, event)
            if event_idx is None:
                continue
            
            for period in forward_periods:
                forward_return = self._calculate_period_return(
                    df, event_idx, period, event.entry_close
                )
                event.forward_returns.append(forward_return)
        
        return events
    
    def _find_event_index(self, df: pd.DataFrame, event: EventRecord) -> Optional[int]:
        """找到事件对应的索引"""
        if 'symbol' in df.columns and 'datetime' in df.columns:
            mask = (df['symbol'] == event.symbol) & (df['datetime'] == event.datetime)
            matches = df.index[mask].tolist()
            return matches[0] if matches else None
        else:
            mask = df['close'] == event.entry_close
            matches = df.index[mask].tolist()
            return matches[0] if matches else None
    
    def _calculate_period_return(
        self, df: pd.DataFrame, event_idx: int, period: int, entry_price: float
    ) -> ForwardReturn:
        """计算指定周期的未来收益"""
        future_idx = event_idx + period
        
        if future_idx >= len(df):
            return ForwardReturn(period=period, return_pct=0.0, cum_return=0.0,
                                mfe=0.0, mae=0.0)
        
        future_price = df.iloc[future_idx]['close']
        return_pct = (future_price - entry_price) / entry_price
        
        period_data = df.iloc[event_idx:future_idx+1]
        if len(period_data) > 0:
            mfe = (period_data['high'].max() - entry_price) / entry_price
            mae = (period_data['low'].min() - entry_price) / entry_price
        else:
            mfe = mae = 0.0
        
        return ForwardReturn(
            period=period, return_pct=return_pct, cum_return=return_pct,
            mfe=mfe, mae=mae
        )
