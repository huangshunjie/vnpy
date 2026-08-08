"""
quant_research/behavior/forward_analyzer.py

未来收益分析引擎
对事件的未来收益进行深度分析
"""
from __future__ import annotations
from typing import List, Dict
import numpy as np
import pandas as pd
from datetime import datetime

from ..model.kline_event_model import (
    EventRecord,
    ForwardReturn,
    EventStatistics,
    PeriodStatistics,
    GroupStatistics,
)


class ForwardReturnAnalyzer:
    """
    未来收益分析器
    
    核心功能：
    1. 分析事件的未来收益分布
    2. 计算风险收益指标
    3. 多维度切片分析
    """
    
    def __init__(self):
        pass
    
    def analyze(
        self,
        events: List[EventRecord],
        research_id: str = ""
    ) -> EventStatistics:
        """
        分析事件统计
        
        Args:
            events: 事件列表
            research_id: 研究ID
            
        Returns:
            EventStatistics
        """
        if not events:
            return EventStatistics(research_id=research_id)
        
        # 基本统计
        total_events = len(events)
        unique_symbols = len(set(e.symbol for e in events))
        
        # 日期范围
        dates = [e.datetime for e in events if isinstance(e.datetime, datetime)]
        if dates:
            date_range_start = min(dates).strftime("%Y-%m-%d")
            date_range_end = max(dates).strftime("%Y-%m-%d")
            years_covered = (max(dates) - min(dates)).days / 365.25
        else:
            date_range_start = ""
            date_range_end = ""
            years_covered = 0.0
        
        # 按持有期统计
        period_stats = self._analyze_by_period(events)
        
        # 分组统计
        by_year = self._analyze_by_year(events)
        by_industry = self._analyze_by_industry(events)
        by_market_cap = self._analyze_by_market_cap(events)
        
        # 特征相关性
        feature_correlation = self._analyze_feature_correlation(events)
        
        return EventStatistics(
            research_id=research_id,
            total_events=total_events,
            unique_symbols=unique_symbols,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            years_covered=years_covered,
            period_stats=period_stats,
            by_year=by_year,
            by_industry=by_industry,
            by_market_cap=by_market_cap,
            feature_correlation=feature_correlation,
            created_at=datetime.now(),
        )
    
    def _analyze_by_period(
        self,
        events: List[EventRecord]
    ) -> Dict[int, PeriodStatistics]:
        """按持有期分析"""
        result = {}
        
        # 获取所有持有期
        periods = set()
        for event in events:
            for fr in event.forward_returns:
                periods.add(fr.period)
        
        # 对每个持有期进行统计
        for period in sorted(periods):
            returns = []
            mfes = []
            maes = []
            
            for event in events:
                for fr in event.forward_returns:
                    if fr.period == period:
                        returns.append(fr.return_pct)
                        mfes.append(fr.mfe)
                        maes.append(fr.mae)
            
            if returns:
                stats = self._calculate_period_statistics(
                    period, returns, mfes, maes
                )
                result[period] = stats
        
        return result
    
    def _calculate_period_statistics(
        self,
        period: int,
        returns: List[float],
        mfes: List[float],
        maes: List[float]
    ) -> PeriodStatistics:
        """计算单个持有期的统计指标"""
        returns_array = np.array(returns)
        
        # 收益统计
        mean_return = float(np.mean(returns_array))
        median_return = float(np.median(returns_array))
        std_return = float(np.std(returns_array))
        min_return = float(np.min(returns_array))
        max_return = float(np.max(returns_array))
        
        # 百分位数
        percentile_5 = float(np.percentile(returns_array, 5))
        percentile_25 = float(np.percentile(returns_array, 25))
        percentile_75 = float(np.percentile(returns_array, 75))
        percentile_95 = float(np.percentile(returns_array, 95))
        
        # 概率统计
        win_rate = float(np.sum(returns_array > 0) / len(returns_array))
        
        # 盈亏比
        winning_returns = returns_array[returns_array > 0]
        losing_returns = returns_array[returns_array < 0]
        
        if len(winning_returns) > 0 and len(losing_returns) > 0:
            avg_win = np.mean(winning_returns)
            avg_loss = np.abs(np.mean(losing_returns))
            profit_loss_ratio = float(avg_win / avg_loss) if avg_loss > 0 else 0.0
        else:
            profit_loss_ratio = 0.0
        
        # 风险指标
        var_95 = percentile_5
        cvar_95 = float(np.mean(returns_array[returns_array <= var_95])) if any(returns_array <= var_95) else 0.0
        
        mean_mfe = float(np.mean(mfes)) if mfes else 0.0
        mean_mae = float(np.mean(maes)) if maes else 0.0
        
        # 夏普比率（简化：假设无风险利率为0）
        sharpe_ratio = float(mean_return / std_return * np.sqrt(252 / period)) if std_return > 0 else 0.0
        
        # 卡玛比率（简化）
        max_drawdown = abs(min_return)
        calmar_ratio = float(mean_return * 252 / period / max_drawdown) if max_drawdown > 0 else 0.0
        
        return PeriodStatistics(
            period=period,
            mean_return=mean_return,
            median_return=median_return,
            std_return=std_return,
            min_return=min_return,
            max_return=max_return,
            percentile_5=percentile_5,
            percentile_25=percentile_25,
            percentile_75=percentile_75,
            percentile_95=percentile_95,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
            mean_mfe=mean_mfe,
            mean_mae=mean_mae,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
        )
    
    def _analyze_by_year(
        self,
        events: List[EventRecord]
    ) -> Dict[str, GroupStatistics]:
        """按年度分析"""
        year_groups = {}
        
        for event in events:
            if not isinstance(event.datetime, datetime):
                continue
            
            year = str(event.datetime.year)
            
            if year not in year_groups:
                year_groups[year] = []
            
            # 使用5日收益
            for fr in event.forward_returns:
                if fr.period == 5:
                    year_groups[year].append(fr.return_pct)
                    break
        
        # 计算每年的统计
        result = {}
        for year, returns in year_groups.items():
            if returns:
                result[year] = GroupStatistics(
                    group_name=year,
                    event_count=len(returns),
                    mean_return=float(np.mean(returns)),
                    win_rate=float(np.sum(np.array(returns) > 0) / len(returns)),
                    sharpe=0.0,  # 简化
                )
        
        return result
    
    def _analyze_by_industry(
        self,
        events: List[EventRecord]
    ) -> Dict[str, GroupStatistics]:
        """按行业分析"""
        industry_groups = {}
        
        for event in events:
            industry = event.industry or "未知"
            
            if industry not in industry_groups:
                industry_groups[industry] = []
            
            for fr in event.forward_returns:
                if fr.period == 5:
                    industry_groups[industry].append(fr.return_pct)
                    break
        
        result = {}
        for industry, returns in industry_groups.items():
            if returns and len(returns) >= 3:  # 至少3个样本
                result[industry] = GroupStatistics(
                    group_name=industry,
                    event_count=len(returns),
                    mean_return=float(np.mean(returns)),
                    win_rate=float(np.sum(np.array(returns) > 0) / len(returns)),
                    sharpe=0.0,
                )
        
        return result
    
    def _analyze_by_market_cap(
        self,
        events: List[EventRecord]
    ) -> Dict[str, GroupStatistics]:
        """按市值分组分析"""
        # 简单分为大中小盘
        large_cap = []
        mid_cap = []
        small_cap = []
        
        for event in events:
            if event.market_cap == 0:
                continue
            
            # 获取5日收益
            return_5 = None
            for fr in event.forward_returns:
                if fr.period == 5:
                    return_5 = fr.return_pct
                    break
            
            if return_5 is None:
                continue
            
            # 简化分类（实际应该用行业中位数）
            if event.market_cap > 100:  # 100亿以上
                large_cap.append(return_5)
            elif event.market_cap > 50:  # 50-100亿
                mid_cap.append(return_5)
            else:
                small_cap.append(return_5)
        
        result = {}
        
        for name, returns in [("大盘", large_cap), ("中盘", mid_cap), ("小盘", small_cap)]:
            if returns and len(returns) >= 3:
                result[name] = GroupStatistics(
                    group_name=name,
                    event_count=len(returns),
                    mean_return=float(np.mean(returns)),
                    win_rate=float(np.sum(np.array(returns) > 0) / len(returns)),
                    sharpe=0.0,
                )
        
        return result
    
    def _analyze_feature_correlation(
        self,
        events: List[EventRecord]
    ) -> Dict[str, float]:
        """分析特征与未来收益的相关性"""
        if not events:
            return {}
        
        # 收集特征和收益
        feature_names = set()
        for event in events:
            feature_names.update(event.feature_snapshot.keys())
        
        if not feature_names:
            return {}
        
        # 构建DataFrame
        data = []
        for event in events:
            # 使用5日收益
            return_5 = None
            for fr in event.forward_returns:
                if fr.period == 5:
                    return_5 = fr.return_pct
                    break
            
            if return_5 is None:
                continue
            
            row = {'return_5': return_5}
            row.update(event.feature_snapshot)
            data.append(row)
        
        if not data:
            return {}
        
        df = pd.DataFrame(data)
        
        # 计算相关性
        result = {}
        for feature in feature_names:
            if feature in df.columns:
                try:
                    corr = df[feature].corr(df['return_5'])
                    if not np.isnan(corr):
                        result[feature] = float(corr)
                except:
                    pass
        
        return result
