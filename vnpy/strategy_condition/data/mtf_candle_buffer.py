# -*- coding: utf-8 -*-
"""
多周期 K线缓存（MultiTimeframeCandleBuffer）

功能：
1. 支持多个周期的数据缓存
2. 自动从基础周期转换到目标周期
3. 智能缓存策略（避免重复转换）
4. 支持直接注入各周期数据

Phase 5 - Step 2
"""
from __future__ import annotations
from typing import Dict, List, Optional, Set
from collections import defaultdict

from vnpy.trader.constant import Interval
from vnpy.trader.object import BarData
from .bar_resampler import BarResampler


class MultiTimeframeCandleBuffer:
    """
    多周期K线缓存
    
    两种使用模式：
    1. 自动转换模式：提供基础周期数据，自动转换到目标周期
    2. 直接注入模式：直接为每个周期提供数据（用于回测）
    
    Example:
        # 模式1：自动转换
        buf = MultiTimeframeCandleBuffer(base_interval=Interval.MINUTE_5)
        buf.set_base_bars("600000.SH", minute_bars)
        daily_bars = buf.get("600000.SH", 100, Interval.DAILY)  # 自动转换
        
        # 模式2：直接注入
        buf = MultiTimeframeCandleBuffer()
        buf.inject("600000.SH", Interval.DAILY, daily_bars)
        buf.inject("600000.SH", Interval.MINUTE_5, minute_bars)
        daily = buf.get("600000.SH", 100, Interval.DAILY)
    """
    
    def __init__(self, base_interval: Optional[Interval] = None):
        """
        Args:
            base_interval: 基础周期（自动转换模式需要）
        """
        self._base_interval = base_interval
        
        # 存储: symbol -> interval -> bars
        self._data: Dict[str, Dict[Interval, List[BarData]]] = defaultdict(dict)
        
        # 缓存转换结果: symbol -> interval -> bars
        self._cache: Dict[str, Dict[Interval, List[BarData]]] = defaultdict(dict)
        
        self._resampler = BarResampler()
    
    def inject(self, symbol: str, interval: Interval, bars: List[BarData]) -> None:
        """
        直接注入某个周期的数据
        
        Args:
            symbol: 股票代码
            interval: 数据周期
            bars: K线数据列表
        """
        self._data[symbol][interval] = bars
        # 注入后清除该股票的缓存（可能影响转换结果）
        if symbol in self._cache:
            self._cache[symbol].pop(interval, None)
    
    def set_base_bars(self, symbol: str, bars: List[BarData]) -> None:
        """
        设置基础周期数据（自动转换模式）
        
        Args:
            symbol: 股票代码
            bars: 基础周期的K线数据
        """
        if self._base_interval is None:
            raise ValueError("未指定 base_interval，无法使用自动转换模式")
        self._data[symbol][self._base_interval] = bars
        # 清除该股票的所有缓存（基础数据变了，派生数据需要重算）
        self._cache.pop(symbol, None)
    
    def get(self, symbol: str, n: int, interval: Interval) -> List[BarData]:
        """
        获取指定周期的K线数据
        
        逻辑：
        1. 如果直接注入了该周期数据，直接返回
        2. 如果缓存中有且足够，返回缓存
        3. 否则从基础数据转换
        
        Args:
            symbol: 股票代码
            n: 需要的K线数量（0 表示全部）
            interval: 目标周期
        
        Returns:
            K线列表（按时间升序）
        """
        # 1. 直接注入的数据优先
        if interval in self._data.get(symbol, {}):
            bars = self._data[symbol][interval]
            if n <= 0:
                return bars
            return bars[-n:] if len(bars) > n else bars
        
        # 2. 检查缓存
        if interval in self._cache.get(symbol, {}):
            cached = self._cache[symbol][interval]
            if n <= 0:
                return cached
            if len(cached) >= n:
                return cached[-n:]
        
        # 3. 自动转换
        converted = self._convert(symbol, interval)
        if converted:
            self._cache[symbol][interval] = converted
            if n <= 0:
                return converted
            return converted[-n:] if len(converted) > n else converted
        
        return []
    
    def _convert(self, symbol: str, target_interval: Interval) -> List[BarData]:
        """
        从已有数据转换到目标周期
        
        转换路径：
        - 分钟 → 小时 → 日线 → 周线
        - 如果有中间周期的数据，优先使用
        """
        symbol_data = self._data.get(symbol, {})
        
        # 定义周期层级（从小到大）
        hierarchy = [
            Interval.MINUTE, Interval.MINUTE_5, Interval.MINUTE_15,
            Interval.MINUTE_30, Interval.HOUR, Interval.DAILY, Interval.WEEKLY
        ]
        
        target_idx = hierarchy.index(target_interval) if target_interval in hierarchy else -1
        if target_idx < 0:
            return []
        
        # 寻找可用的源数据（从最接近目标的较小周期开始）
        for i in range(target_idx - 1, -1, -1):
            source_interval = hierarchy[i]
            if source_interval in symbol_data and symbol_data[source_interval]:
                try:
                    return self._resampler.resample(
                        symbol_data[source_interval],
                        source_interval,
                        target_interval
                    )
                except ValueError:
                    # 不支持的转换，继续尝试下一个
                    continue
        
        return []
    
    def get_available_intervals(self, symbol: str) -> List[Interval]:
        """
        获取某股票所有可用的周期
        
        包括直接注入的和可以通过转换获得的
        """
        available = set()
        
        # 直接注入的
        if symbol in self._data:
            available.update(self._data[symbol].keys())
        
        # 可以转换获得的
        hierarchy = [
            Interval.MINUTE, Interval.MINUTE_5, Interval.MINUTE_15,
            Interval.MINUTE_30, Interval.HOUR, Interval.DAILY, Interval.WEEKLY
        ]
        
        symbol_data = self._data.get(symbol, {})
        for source_interval in symbol_data:
            if source_interval in hierarchy:
                src_idx = hierarchy.index(source_interval)
                # 可以转换到所有更大的周期
                for target_idx in range(src_idx + 1, len(hierarchy)):
                    available.add(hierarchy[target_idx])
        
        return sorted(available, key=lambda x: hierarchy.index(x) if x in hierarchy else 99)
    
    def has_data(self, symbol: str, interval: Interval) -> bool:
        """检查是否有（或可以获得）某周期的数据"""
        # 直接有
        if interval in self._data.get(symbol, {}):
            return True
        # 缓存有
        if interval in self._cache.get(symbol, {}):
            return True
        # 可以转换
        return interval in self.get_available_intervals(symbol)
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        清除缓存
        
        Args:
            symbol: 指定股票（None 则清除所有）
        """
        if symbol:
            self._cache.pop(symbol, None)
        else:
            self._cache.clear()
    
    def clear_all(self, symbol: Optional[str] = None) -> None:
        """
        清除所有数据和缓存
        
        Args:
            symbol: 指定股票（None 则清除所有）
        """
        if symbol:
            self._data.pop(symbol, None)
            self._cache.pop(symbol, None)
        else:
            self._data.clear()
            self._cache.clear()
    
    def preload(self, symbols: List[str], intervals: List[Interval]) -> None:
        """
        批量预加载：对所有股票预先转换所需周期的数据
        
        用于回测前的数据准备，减少回测中的转换开销
        
        Args:
            symbols: 股票列表
            intervals: 需要的周期列表
        """
        for symbol in symbols:
            for interval in intervals:
                self.get(symbol, 0, interval)  # 触发转换并缓存
    
    @property
    def symbols(self) -> List[str]:
        """已加载数据的所有股票代码"""
        return list(self._data.keys())
    
    def stats(self) -> dict:
        """
        返回缓存统计信息
        
        Returns:
            {"symbols": n, "intervals": {...}, "cache_entries": n}
        """
        intervals_count = defaultdict(int)
        for symbol, data in self._data.items():
            for interval in data:
                intervals_count[interval.value] += 1
        
        cache_count = sum(len(v) for v in self._cache.values())
        
        return {
            "symbols": len(self._data),
            "intervals": dict(intervals_count),
            "cache_entries": cache_count,
        }
    

    def get_bars_as_of(self, symbol: str, n: int, interval: Interval,
                       as_of_time) -> List[BarData]:
        """
        Phase 5: 获取截至指定时间点的K线数据（防止未来函数）

        核心语义：只返回 bar.datetime <= as_of_time 的K线。
        确保回测中不会使用评估时间点之后的数据。

        Args:
            symbol: 股票代码
            n: 需要的K线数量
            interval: 目标周期
            as_of_time: 评估时间点（datetime 对象或具有比较能力的对象）

        Returns:
            符合时间约束的K线列表（按时间升序，最多 n 根）
        """
        # 获取全量数据
        all_bars = self.get(symbol, 0, interval)
        if not all_bars:
            return []

        # 过滤：只保留 datetime <= as_of_time 的K线
        valid_bars = []
        for b in all_bars:
            bar_dt = getattr(b, 'datetime', None) or getattr(b, 'dt', None)
            if bar_dt is None:
                valid_bars.append(b)
                continue
            # 统一为 naive 比较
            if hasattr(bar_dt, 'tzinfo') and bar_dt.tzinfo is not None:
                bar_dt = bar_dt.replace(tzinfo=None)
            cmp_time = as_of_time
            if hasattr(cmp_time, 'tzinfo') and cmp_time.tzinfo is not None:
                cmp_time = cmp_time.replace(tzinfo=None)
            if bar_dt <= cmp_time:
                valid_bars.append(b)

        if not valid_bars:
            return []

        # 返回最后 n 根
        if n <= 0:
            return valid_bars
        return valid_bars[-n:] if len(valid_bars) > n else valid_bars

    def set_base_bars_multi(self, symbol: str, bars_dict: dict) -> None:
        """
        Phase 5: 为一个股票同时设置多个周期的基础数据

        Args:
            symbol: 股票代码
            bars_dict: {Interval: List[BarData]} 各周期数据字典
        """
        for interval, bars in bars_dict.items():
            self._data[symbol][interval] = bars
        # 清除缓存
        self._cache.pop(symbol, None)

    def get_cache_stats(self) -> dict:
        """
        Phase 5: 获取缓存统计信息（用于性能测试）

        Returns:
            {"total_requests": int, "cache_hits": int, "hit_rate": float}
        """
        total = getattr(self, '_stat_total', 0)
        hits = getattr(self, '_stat_hits', 0)
        return {
            "total_requests": total,
            "cache_hits": hits,
            "hit_rate": hits / total if total > 0 else 0.0,
        }
    

    def get_bars_as_of(self, symbol: str, n: int, interval: Interval,
                       as_of_time) -> List[BarData]:
        """
        Phase 5: 获取截至指定时间点的K线数据（防止未来函数）

        核心语义：只返回 bar.datetime <= as_of_time 的K线。
        确保回测中不会使用评估时间点之后的数据。

        Args:
            symbol: 股票代码
            n: 需要的K线数量
            interval: 目标周期
            as_of_time: 评估时间点（datetime 对象或具有比较能力的对象）

        Returns:
            符合时间约束的K线列表（按时间升序，最多 n 根）
        """
        # 获取全量数据
        all_bars = self.get(symbol, 0, interval)
        if not all_bars:
            return []

        # 过滤：只保留 datetime <= as_of_time 的K线
        valid_bars = []
        for b in all_bars:
            bar_dt = getattr(b, 'datetime', None) or getattr(b, 'dt', None)
            if bar_dt is None:
                valid_bars.append(b)
                continue
            # 统一为 naive 比较
            if hasattr(bar_dt, 'tzinfo') and bar_dt.tzinfo is not None:
                bar_dt = bar_dt.replace(tzinfo=None)
            cmp_time = as_of_time
            if hasattr(cmp_time, 'tzinfo') and cmp_time.tzinfo is not None:
                cmp_time = cmp_time.replace(tzinfo=None)
            if bar_dt <= cmp_time:
                valid_bars.append(b)

        if not valid_bars:
            return []

        # 返回最后 n 根
        if n <= 0:
            return valid_bars
        return valid_bars[-n:] if len(valid_bars) > n else valid_bars

    def set_base_bars_multi(self, symbol: str, bars_dict: dict) -> None:
        """
        Phase 5: 为一个股票同时设置多个周期的基础数据

        Args:
            symbol: 股票代码
            bars_dict: {Interval: List[BarData]} 各周期数据字典
        """
        for interval, bars in bars_dict.items():
            self._data[symbol][interval] = bars
        # 清除缓存
        self._cache.pop(symbol, None)

    def get_cache_stats(self) -> dict:
        """
        Phase 5: 获取缓存统计信息（用于性能测试）

        Returns:
            {"total_requests": int, "cache_hits": int, "hit_rate": float}
        """
        total = getattr(self, '_stat_total', 0)
        hits = getattr(self, '_stat_hits', 0)
        return {
            "total_requests": total,
            "cache_hits": hits,
            "hit_rate": hits / total if total > 0 else 0.0,
        }
    
    def __repr__(self) -> str:
        stats = self.stats()
        return (f"MTFCandleBuffer(symbols={stats['symbols']}, "
                f"intervals={stats['intervals']}, "
                f"cache={stats['cache_entries']})")