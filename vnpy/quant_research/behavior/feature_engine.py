"""
quant_research/behavior/feature_engine.py

K线特征计算引擎（增强版）
基于原kline_calculator.py，增强功能
"""
from __future__ import annotations
from typing import Dict, List, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .feature_registry import FeatureRegistry, get_global_registry
from ..model.kline_feature_model import KLineFeatureDefinition, FeatureComplexity


class FeatureEngine:
    """K线特征计算引擎"""
    
    def __init__(self, registry: Optional[FeatureRegistry] = None):
        self.registry = registry or get_global_registry()
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_metadata: Dict[str, Dict] = {}
        self._stats = {
            "total_calculations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time": 0.0,
        }
        self._custom_calculators: Dict[str, Callable] = {}
    
    def calculate(
        self,
        df: pd.DataFrame,
        features: List[str],
        use_cache: bool = True,
        validate: bool = True
    ) -> pd.DataFrame:
        """计算K线特征"""
        start_time = time.time()
        
        if validate:
            self._validate_dataframe(df)
            valid, invalid = self.registry.validate_features(features)
            if not valid:
                raise ValueError(f"未知特征: {invalid}")
        
        cache_key = self._generate_cache_key(df, features)
        
        if use_cache and cache_key in self._cache:
            self._stats["cache_hits"] += 1
            return self._cache[cache_key].copy()
        
        self._stats["cache_misses"] += 1
        result = df.copy()
        
        features_to_calc = self.registry.resolve_dependencies(features)
        features_sorted = self._sort_by_complexity(features_to_calc)
        
        for feature_name in features_sorted:
            if feature_name not in result.columns:
                result[feature_name] = self._calculate_single_feature(result, feature_name)
        
        if use_cache:
            self._cache[cache_key] = result.copy()
            self._cache_metadata[cache_key] = {
                "features": features,
                "created_at": datetime.now(),
            }
        
        self._stats["total_calculations"] += 1
        self._stats["total_time"] += time.time() - start_time
        
        return result
    
    def batch_calculate(
        self,
        data_dict: Dict[str, pd.DataFrame],
        features: List[str],
        parallel: bool = True,
        max_workers: int = 4
    ) -> Dict[str, pd.DataFrame]:
        """批量计算"""
        result = {}
        
        if parallel and len(data_dict) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.calculate, df, features, False): symbol
                    for symbol, df in data_dict.items()
                }
                
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        result[symbol] = future.result()
                    except Exception as e:
                        print(f"[错误] {symbol}: {e}")
                        result[symbol] = data_dict[symbol]
        else:
            for symbol, df in data_dict.items():
                try:
                    result[symbol] = self.calculate(df, features, False)
                except Exception as e:
                    print(f"[错误] {symbol}: {e}")
                    result[symbol] = df
        
        return result
    
    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"缺少列: {missing}")
        if len(df) < 1:
            raise ValueError("数据为空")
    
    def _generate_cache_key(self, df: pd.DataFrame, features: List[str]) -> str:
        return f"{len(df)}_{hash(tuple(sorted(features)))}"
    
    def _sort_by_complexity(self, features: List[str]) -> List[str]:
        order = {FeatureComplexity.SIMPLE: 1, FeatureComplexity.MEDIUM: 2, FeatureComplexity.COMPLEX: 3}
        
        def key(name):
            f = self.registry.get_feature(name)
            return order.get(f.complexity, 999) if f else 999
        
        return sorted(features, key=key)
    
    def _calculate_single_feature(self, df: pd.DataFrame, name: str) -> pd.Series:
        if name in self._custom_calculators:
            return self._custom_calculators[name](df)
        
        method = getattr(self, f'_calc_{name}', None)
        if method:
            return method(df)
        
        feature_def = self.registry.get_feature(name)
        if feature_def:
            return self._calc_by_formula(df, feature_def)
        
        return pd.Series(np.nan, index=df.index)
    
    def _calc_by_formula(self, df: pd.DataFrame, feature_def: KLineFeatureDefinition) -> pd.Series:
        try:
            env = {
                'open': df['open'], 'high': df['high'], 'low': df['low'],
                'close': df['close'], 'volume': df['volume'],
                'df': df, 'np': np, 'pd': pd,
            }
            
            if feature_def.dependencies:
                for dep in feature_def.dependencies:
                    if dep in df.columns:
                        env[dep] = df[dep]
            
            result = eval(feature_def.formula, {"__builtins__": {}}, env)
            return result if isinstance(result, pd.Series) else pd.Series(result, index=df.index)
        except Exception as e:
            print(f"[错误] {feature_def.name}: {e}")
            return pd.Series(np.nan, index=df.index)
    
    def register_calculator(self, name: str, calc: Callable) -> None:
        self._custom_calculators[name] = calc
    
    def get_statistics(self) -> Dict:
        stats = self._stats.copy()
        total = stats["cache_hits"] + stats["cache_misses"]
        stats["cache_hit_rate"] = stats["cache_hits"] / total if total > 0 else 0
        stats["avg_time"] = stats["total_time"] / stats["total_calculations"] if stats["total_calculations"] > 0 else 0
        return stats
    
    def clear_cache(self) -> None:
        self._cache.clear()
        self._cache_metadata.clear()
    
    # 内置计算器
    def _calc_return_1(self, df): return df['close'].pct_change(1)
    def _calc_return_3(self, df): return df['close'].pct_change(3)
    def _calc_return_5(self, df): return df['close'].pct_change(5)
    def _calc_return_10(self, df): return df['close'].pct_change(10)
    def _calc_return_20(self, df): return df['close'].pct_change(20)
    
    def _calc_body_ratio(self, df):
        return np.abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-8)
    
    def _calc_upper_shadow_ratio(self, df):
        return (df['high'] - df[['open', 'close']].max(axis=1)) / (df['high'] - df['low'] + 1e-8)
    
    def _calc_lower_shadow_ratio(self, df):
        return (df[['open', 'close']].min(axis=1) - df['low']) / (df['high'] - df['low'] + 1e-8)
    
    def _calc_volume_ratio(self, df):
        return df['volume'] / df['volume'].rolling(20).mean()
    
    def _calc_ma5(self, df): return df['close'].rolling(5).mean()
    def _calc_ma10(self, df): return df['close'].rolling(10).mean()
    def _calc_ma20(self, df): return df['close'].rolling(20).mean()
    def _calc_ma60(self, df): return df['close'].rolling(60).mean()
    
    def _calc_rsi_14(self, df):
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / (loss + 1e-8)
        return 100 - (100 / (1 + rs))
    
    def _calc_atr_20(self, df):
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift(1))
        lc = np.abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.rolling(20).mean()
    
    def _calc_new_high_20(self, df):
        return (df['close'] >= df['close'].rolling(20).max()).astype(int)
    
    def _calc_new_low_20(self, df):
        return (df['close'] <= df['close'].rolling(20).min()).astype(int)
