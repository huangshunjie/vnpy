"""
quant_research/behavior/statistics.py

统计引擎
提供各种统计分析工具
"""
from __future__ import annotations
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from datetime import datetime

from ..model.kline_event_model import (
    EventRecord,
    EventStatistics,
    FeatureImportance,
    FeatureRank,
)


class StatisticsEngine:
    """
    统计引擎
    
    核心功能：
    1. 特征重要性分析
    2. 稳定性分析
    3. 显著性检验
    """
    
    def __init__(self):
        pass
    
    def analyze_feature_importance(
        self,
        events: List[EventRecord],
        research_id: str = ""
    ) -> FeatureImportance:
        """
        分析特征重要性
        
        Args:
            events: 事件列表
            research_id: 研究ID
            
        Returns:
            FeatureImportance
        """
        if not events:
            return FeatureImportance(research_id=research_id)
        
        # 提取所有特征名称
        feature_names = set()
        for event in events:
            feature_names.update(event.feature_snapshot.keys())
        
        if not feature_names:
            return FeatureImportance(research_id=research_id)
        
        # 构建数据
        data = self._build_feature_dataframe(events)
        
        if data is None or len(data) == 0:
            return FeatureImportance(research_id=research_id)
        
        # 计算每个特征的重要性
        feature_rankings = []
        
        for feature_name in feature_names:
            if feature_name not in data.columns:
                continue
            
            try:
                # 计算相关性
                correlation = data[feature_name].corr(data['return_5'])
                
                # 计算IC（信息系数）
                ic = self._calculate_ic(data[feature_name], data['return_5'])
                
                # 计算RankIC
                rank_ic = self._calculate_rank_ic(data[feature_name], data['return_5'])
                
                # 预测力得分（简化：相关性的绝对值）
                predictive_power = abs(correlation) if not np.isnan(correlation) else 0.0
                
                # 稳定性（简化：固定为0.8）
                stability = 0.8
                
                feature_rank = FeatureRank(
                    feature_name=feature_name,
                    correlation=float(correlation) if not np.isnan(correlation) else 0.0,
                    information_coefficient=float(ic),
                    rank_ic=float(rank_ic),
                    predictive_power=float(predictive_power),
                    stability=stability,
                    rank=0,  # 稍后排序
                )
                
                feature_rankings.append(feature_rank)
                
            except Exception as e:
                print(f"[错误] 特征 {feature_name} 重要性计算失败: {e}")
        
        # 按预测力排序
        feature_rankings.sort(key=lambda x: x.predictive_power, reverse=True)
        for i, fr in enumerate(feature_rankings):
            fr.rank = i + 1
        
        # 计算相关性矩阵（简化）
        correlation_matrix = {}
        
        return FeatureImportance(
            research_id=research_id,
            feature_rankings=feature_rankings,
            correlation_matrix=correlation_matrix,
            created_at=datetime.now(),
        )
    
    def _build_feature_dataframe(
        self,
        events: List[EventRecord]
    ) -> Optional[pd.DataFrame]:
        """构建特征DataFrame"""
        data = []
        
        for event in events:
            # 获取5日收益
            return_5 = None
            for fr in event.forward_returns:
                if fr.period == 5:
                    return_5 = fr.return_pct
                    break
            
            if return_5 is None:
                continue
            
            # 构建行数据
            row = {'return_5': return_5}
            row.update(event.feature_snapshot)
            data.append(row)
        
        if not data:
            return None
        
        return pd.DataFrame(data)
    
    def _calculate_ic(
        self,
        feature_values: pd.Series,
        returns: pd.Series
    ) -> float:
        """
        计算IC（Information Coefficient）
        即特征值与未来收益的相关系数
        """
        try:
            # 去除NaN
            valid_mask = ~(feature_values.isna() | returns.isna())
            if valid_mask.sum() < 2:
                return 0.0
            
            feature_clean = feature_values[valid_mask]
            returns_clean = returns[valid_mask]
            
            # 计算皮尔逊相关系数
            correlation = feature_clean.corr(returns_clean)
            
            return float(correlation) if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            print(f"[错误] IC计算失败: {e}")
            return 0.0
    
    def _calculate_rank_ic(
        self,
        feature_values: pd.Series,
        returns: pd.Series
    ) -> float:
        """
        计算RankIC
        即特征排名与收益排名的相关系数（斯皮尔曼相关系数）
        """
        try:
            # 去除NaN
            valid_mask = ~(feature_values.isna() | returns.isna())
            if valid_mask.sum() < 2:
                return 0.0
            
            feature_clean = feature_values[valid_mask]
            returns_clean = returns[valid_mask]
            
            # 转换为排名
            feature_rank = feature_clean.rank()
            returns_rank = returns_clean.rank()
            
            # 计算相关系数
            rank_correlation = feature_rank.corr(returns_rank)
            
            return float(rank_correlation) if not np.isnan(rank_correlation) else 0.0
            
        except Exception as e:
            print(f"[错误] RankIC计算失败: {e}")
            return 0.0
    
    def calculate_information_ratio(
        self,
        returns: List[float],
        benchmark_returns: Optional[List[float]] = None
    ) -> float:
        """
        计算信息比率
        
        Args:
            returns: 策略收益序列
            benchmark_returns: 基准收益序列（可选）
            
        Returns:
            信息比率
        """
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        
        if benchmark_returns is None:
            # 如果没有基准，假设基准收益为0
            excess_returns = returns_array
        else:
            benchmark_array = np.array(benchmark_returns)
            excess_returns = returns_array - benchmark_array
        
        # 计算信息比率
        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns)
        
        if std_excess > 0:
            ir = mean_excess / std_excess
            return float(ir)
        else:
            return 0.0
    
    def test_significance(
        self,
        sample1: List[float],
        sample2: Optional[List[float]] = None,
        alpha: float = 0.05
    ) -> Dict[str, float]:
        """
        显著性检验
        
        Args:
            sample1: 样本1（如策略收益）
            sample2: 样本2（如基准收益），可选
            alpha: 显著性水平
            
        Returns:
            包含p值和统计量的字典
        """
        from scipy import stats
        
        if sample2 is None:
            # 单样本t检验：检验均值是否显著不为0
            t_stat, p_value = stats.ttest_1samp(sample1, 0.0)
        else:
            # 双样本t检验：检验两组均值是否有显著差异
            t_stat, p_value = stats.ttest_ind(sample1, sample2)
        
        return {
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'is_significant': bool(p_value < alpha),
            'alpha': alpha,
        }
    
    def calculate_stability_score(
        self,
        statistics: EventStatistics
    ) -> float:
        """
        计算稳定性得分
        考虑跨时间、跨行业、跨市值的表现一致性
        
        Args:
            statistics: 事件统计结果
            
        Returns:
            稳定性得分（0-1）
        """
        if not statistics:
            return 0.0
        
        scores = []
        
        # 时间稳定性：年度收益的标准差
        if statistics.by_year:
            year_returns = [s.mean_return for s in statistics.by_year.values()]
            if len(year_returns) >= 2:
                year_std = np.std(year_returns)
                year_mean = np.mean(year_returns)
                if year_mean != 0:
                    cv = year_std / abs(year_mean)  # 变异系数
                    time_stability = max(0, 1 - cv)
                    scores.append(time_stability)
        
        # 行业稳定性
        if statistics.by_industry:
            industry_returns = [s.mean_return for s in statistics.by_industry.values()]
            if len(industry_returns) >= 2:
                ind_std = np.std(industry_returns)
                ind_mean = np.mean(industry_returns)
                if ind_mean != 0:
                    cv = ind_std / abs(ind_mean)
                    industry_stability = max(0, 1 - cv)
                    scores.append(industry_stability)
        
        # 市值稳定性
        if statistics.by_market_cap:
            cap_returns = [s.mean_return for s in statistics.by_market_cap.values()]
            if len(cap_returns) >= 2:
                cap_std = np.std(cap_returns)
                cap_mean = np.mean(cap_returns)
                if cap_mean != 0:
                    cv = cap_std / abs(cap_mean)
                    cap_stability = max(0, 1 - cv)
                    scores.append(cap_stability)
        
        # 综合得分
        if scores:
            return float(np.mean(scores))
        else:
            return 0.5  # 默认中等稳定性
