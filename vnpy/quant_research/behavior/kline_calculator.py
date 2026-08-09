"""
quant_research/behavior/kline_calculator.py

K线特征计算引擎
支持向量化批量计算50+个K线特征
"""
from __future__ import annotations
from typing import Dict, List, Optional, Set
import pandas as pd
import numpy as np
from datetime import datetime

from ..model.kline_feature_model import KLineFeatureDefinition, FeatureComplexity
from ..model.kline_feature_presets import PRESET_KLINE_FEATURES
from .volume_price_calculator import VP_CALCULATOR_MAP


class KLineFeatureCalculator:
    """
    K线特征计算器
    
    核心功能：
    1. 批量计算K线特征
    2. 自动处理特征依赖
    3. 向量化计算提高性能
    4. 特征缓存机制
    """
    
    def __init__(self):
        self.feature_definitions = PRESET_KLINE_FEATURES
        self._feature_cache: Dict[str, pd.Series] = {}
        
    def calculate(
        self,
        df: pd.DataFrame,
        features: List[str],
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        计算指定的K线特征
        
        Args:
            df: K线数据，必须包含 OHLCV 列
            features: 需要计算的特征名称列表
            use_cache: 是否使用缓存
            
        Returns:
            包含原始数据和计算特征的DataFrame
        """
        # 验证输入数据
        self._validate_dataframe(df)
        
        # 清空缓存（如果不使用缓存）
        if not use_cache:
            self._feature_cache.clear()
        
        # 复制数据框
        result = df.copy()
        
        # 解析特征依赖关系
        features_to_calc = self._resolve_dependencies(features)
        
        # 按复杂度排序（简单特征先计算）
        features_sorted = self._sort_by_complexity(features_to_calc)
        
        # 逐个计算特征
        for feature_name in features_sorted:
            if feature_name in self._feature_cache:
                result[feature_name] = self._feature_cache[feature_name]
            else:
                feature_values = self._calculate_single_feature(result, feature_name)
                result[feature_name] = feature_values
                self._feature_cache[feature_name] = feature_values
        
        return result
    
    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """验证数据框包含必需的列"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"数据框缺少必需的列: {missing_cols}")
        
        if len(df) < 1:
            raise ValueError("数据框为空")
    
    def _resolve_dependencies(self, features: List[str]) -> List[str]:
        """解析特征依赖关系，返回需要计算的所有特征"""
        result = set()
        
        def add_feature_and_deps(feature_name: str):
            if feature_name in result:
                return
            
            result.add(feature_name)
            
            # 获取特征定义
            feature_def = self.feature_definitions.get(feature_name)
            if feature_def and feature_def.dependencies:
                for dep in feature_def.dependencies:
                    add_feature_and_deps(dep)
        
        for feature in features:
            add_feature_and_deps(feature)
        
        return list(result)
    
    def _sort_by_complexity(self, features: List[str]) -> List[str]:
        """按复杂度排序特征（简单特征先计算）"""
        complexity_order = {
            FeatureComplexity.SIMPLE: 1,
            FeatureComplexity.MEDIUM: 2,
            FeatureComplexity.COMPLEX: 3,
        }
        
        def get_complexity(feature_name: str) -> int:
            feature_def = self.feature_definitions.get(feature_name)
            if not feature_def:
                return 999  # 未定义的特征放最后
            return complexity_order.get(feature_def.complexity, 999)
        
        return sorted(features, key=get_complexity)
    
    def _calculate_single_feature(
        self,
        df: pd.DataFrame,
        feature_name: str
    ) -> pd.Series:
        """计算单个特征"""
        feature_def = self.feature_definitions.get(feature_name)
        
        if not feature_def:
            raise ValueError(f"未知的特征: {feature_name}")
        
        # 优先检查量价关系向量化计算函数
        vp_calc = VP_CALCULATOR_MAP.get(feature_name)
        if vp_calc:
            return vp_calc(df)
        
        # 根据特征类型选择计算方法
        calculator = getattr(self, f'_calc_{feature_name}', None)
        
        if calculator:
            # 使用专门的计算方法
            return calculator(df)
        else:
            # 使用通用的公式计算
            return self._calc_by_formula(df, feature_def)
    
    def _calc_by_formula(
        self,
        df: pd.DataFrame,
        feature_def: KLineFeatureDefinition
    ) -> pd.Series:
        """
        通过公式计算特征（简化实现）
        实际应用中需要更复杂的公式解析器
        """
        # 这里简化处理，实际需要安全的公式解析
        # 可以使用 numexpr 或自定义 DSL
        
        # 提取常用变量
        open_price = df['open']
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        
        # 构建 eval 命名空间：基础列 + 已计算的所有特征列
        eval_ns = {
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'df': df,
            'np': np,
            'pd': pd,
        }
        # 将 DataFrame 中已有的列（含已计算的依赖特征）加入命名空间
        for col in df.columns:
            if col not in eval_ns:
                eval_ns[col] = df[col]
        
        # 根据公式计算
        try:
            result = eval(feature_def.formula, eval_ns)
            return result
        except Exception as e:
            # 公式计算失败，返回NaN
            print(f"[警告] 特征 {feature_def.name} 计算失败: {e}")
            return pd.Series(np.nan, index=df.index)
    
    # ================================================================
    # 专门的特征计算方法（向量化实现，性能更好）
    # ================================================================
    
    def _calc_return_1(self, df: pd.DataFrame) -> pd.Series:
        """1日收益率"""
        return df['close'].pct_change(1)
    
    def _calc_return_3(self, df: pd.DataFrame) -> pd.Series:
        """3日收益率"""
        return df['close'].pct_change(3)
    
    def _calc_return_5(self, df: pd.DataFrame) -> pd.Series:
        """5日收益率"""
        return df['close'].pct_change(5)
    
    def _calc_return_10(self, df: pd.DataFrame) -> pd.Series:
        """10日收益率"""
        return df['close'].pct_change(10)
    
    def _calc_gap_return(self, df: pd.DataFrame) -> pd.Series:
        """跳空收益"""
        return (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    
    def _calc_intraday_return(self, df: pd.DataFrame) -> pd.Series:
        """日内收益"""
        return (df['close'] - df['open']) / df['open']
    
    def _calc_overnight_return(self, df: pd.DataFrame) -> pd.Series:
        """隔夜收益"""
        return (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    
    def _calc_body_ratio(self, df: pd.DataFrame) -> pd.Series:
        """实体比例"""
        body = np.abs(df['close'] - df['open'])
        range_val = df['high'] - df['low']
        return body / (range_val + 1e-8)
    
    def _calc_upper_shadow_ratio(self, df: pd.DataFrame) -> pd.Series:
        """上影线比例"""
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        range_val = df['high'] - df['low']
        return upper_shadow / (range_val + 1e-8)
    
    def _calc_lower_shadow_ratio(self, df: pd.DataFrame) -> pd.Series:
        """下影线比例"""
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        range_val = df['high'] - df['low']
        return lower_shadow / (range_val + 1e-8)
    
    def _calc_close_location(self, df: pd.DataFrame) -> pd.Series:
        """收盘位置"""
        return (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
    
    def _calc_body_sign(self, df: pd.DataFrame) -> pd.Series:
        """K线方向"""
        return np.sign(df['close'] - df['open'])
    
    def _calc_range_pct(self, df: pd.DataFrame) -> pd.Series:
        """振幅"""
        return (df['high'] - df['low']) / df['open']
    
    def _calc_volume_ratio(self, df: pd.DataFrame) -> pd.Series:
        """量比"""
        return df['volume'] / df['volume'].rolling(20).mean()
    
    def _calc_amount_ratio(self, df: pd.DataFrame) -> pd.Series:
        """额比"""
        if 'amount' in df.columns:
            return df['amount'] / df['amount'].rolling(20).mean()
        else:
            # 如果没有amount列，用volume近似
            return self._calc_volume_ratio(df)
    
    def _calc_ma5(self, df: pd.DataFrame) -> pd.Series:
        """MA5"""
        return df['close'].rolling(5).mean()
    
    def _calc_ma20(self, df: pd.DataFrame) -> pd.Series:
        """MA20"""
        return df['close'].rolling(20).mean()
    
    def _calc_ma60(self, df: pd.DataFrame) -> pd.Series:
        """MA60"""
        return df['close'].rolling(60).mean()
    
    def _calc_price_position(self, df: pd.DataFrame) -> pd.Series:
        """价格位置"""
        low_60 = df['low'].rolling(60).min()
        high_60 = df['high'].rolling(60).max()
        return (df['close'] - low_60) / (high_60 - low_60 + 1e-8)
    
    def _calc_ma_slope_5(self, df: pd.DataFrame) -> pd.Series:
        """MA5斜率"""
        if 'ma5' not in df.columns:
            ma5 = self._calc_ma5(df)
        else:
            ma5 = df['ma5']
        return ma5.pct_change(1)
    
    def _calc_atr_20(self, df: pd.DataFrame) -> pd.Series:
        """ATR(20)"""
        # 真实波幅 = max(high-low, abs(high-prev_close), abs(low-prev_close))
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift(1))
        lc = np.abs(df['low'] - df['close'].shift(1))
        
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = tr.rolling(20).mean()
        return atr
    
    def _calc_volatility_20(self, df: pd.DataFrame) -> pd.Series:
        """20日波动率（年化）"""
        if 'return_1' not in df.columns:
            returns = self._calc_return_1(df)
        else:
            returns = df['return_1']
        return returns.rolling(20).std() * np.sqrt(252)
    
    def _calc_rsi_14(self, df: pd.DataFrame) -> pd.Series:
        """RSI(14)"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-8)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calc_macd(self, df: pd.DataFrame) -> pd.Series:
        """MACD"""
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        return macd
    
    def _calc_reversal_5(self, df: pd.DataFrame) -> pd.Series:
        """5日反转"""
        if 'return_5' not in df.columns:
            return_5 = self._calc_return_5(df)
        else:
            return_5 = df['return_5']
        return -return_5
    
    def get_available_features(self) -> List[str]:
        """获取所有可用的特征名称"""
        return list(self.feature_definitions.keys())
    
    def get_feature_info(self, feature_name: str) -> Optional[KLineFeatureDefinition]:
        """获取特征详细信息"""
        return self.feature_definitions.get(feature_name)
    
    def clear_cache(self) -> None:
        """清空特征缓存"""
        self._feature_cache.clear()


# ================================================================
# 辅助函数
# ================================================================

def calculate_features_for_symbol(
    df: pd.DataFrame,
    features: List[str]
) -> pd.DataFrame:
    """
    为单个标的计算特征（便捷函数）
    
    Args:
        df: K线数据
        features: 特征列表
        
    Returns:
        包含特征的DataFrame
    """
    calculator = KLineFeatureCalculator()
    return calculator.calculate(df, features)


def batch_calculate_features(
    data_dict: Dict[str, pd.DataFrame],
    features: List[str]
) -> Dict[str, pd.DataFrame]:
    """
    批量为多个标的计算特征
    
    Args:
        data_dict: {symbol: DataFrame} 字典
        features: 特征列表
        
    Returns:
        {symbol: DataFrame with features} 字典
    """
    calculator = KLineFeatureCalculator()
    result = {}
    
    for symbol, df in data_dict.items():
        try:
            result[symbol] = calculator.calculate(df, features, use_cache=False)
        except Exception as e:
            print(f"[错误] {symbol} 特征计算失败: {e}")
            result[symbol] = df  # 返回原始数据
    
    return result
