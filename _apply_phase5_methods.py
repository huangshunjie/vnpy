# -*- coding: utf-8 -*-
"""
将 Phase 5 方法添加到 MTFCandleBuffer 和 ScanEngine
"""
import sys
import os

# 1. 更新 MTFCandleBuffer
mtf_buffer_file = "vnpy/strategy_condition/data/mtf_candle_buffer.py"

with open(mtf_buffer_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 __repr__ 之前添加新方法
new_methods = '''
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
    
'''

if '    def __repr__(self)' in content:
    content = content.replace('    def __repr__(self)', new_methods + '    def __repr__(self)')
    with open(mtf_buffer_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ 已更新 {mtf_buffer_file}")
else:
    print(f"✗ 未找到插入点 in {mtf_buffer_file}")

# 2. 更新 ScanEngine
scan_engine_file = "vnpy/strategy_condition/engine/scan_engine.py"

with open(scan_engine_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 _get_bars 方法的位置，在之前添加 _get_bars_as_of
new_scan_method = '''    def _get_bars_as_of(self, symbol: str, n: int, interval: Interval,
                        as_of_time) -> list:
        """
        Phase 5: 获取截至指定时间点的K线（防止未来函数）。

        优先级：
        1. MTFCandleBuffer.get_bars_as_of()（支持时间过滤）
        2. 传统 CandleBuffer（向后兼容，无时间过滤）

        Args:
            symbol: 股票代码
            n: K线数量
            interval: 周期
            as_of_time: 评估时间点（datetime）

        Returns:
            符合时间约束的K线列表
        """
        if as_of_time is None:
            return self._get_bars(symbol, n, interval)

        if self._mtf_buffer is not None:
            bars = self._mtf_buffer.get_bars_as_of(symbol, n, interval, as_of_time)
            if bars:
                return bars

        # 回退到传统 buffer（无时间过滤）
        return self._get_bars(symbol, n, interval)

'''

# 找到插入点
insert_idx = None
for i, line in enumerate(lines):
    if 'def _get_bars(self, symbol: str, n: int' in line:
        insert_idx = i
        break

if insert_idx:
    lines.insert(insert_idx, new_scan_method)
    with open(scan_engine_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"✓ 已更新 {scan_engine_file}")
else:
    print(f"✗ 未找到插入点 in {scan_engine_file}")

# 3. 更新 _backtest_symbol 中的多周期评估部分
with open(scan_engine_file, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''                for interval in req.intervals:
                    # 简化实现：所有周期都使用同一份数据（实际应该根据周期不同加载不同数据）
                    # TODO: 实际生产环境需要为不同周期加载相应的数据
                    ctx.set_bars(interval, bars_so_far)'''

new_code = '''                for interval in req.intervals:
                    # Phase 5: 使用 As-of Time 对齐，防止未来函数
                    interval_bars = self._get_bars_as_of(
                        symbol, len(bars_so_far), interval, eval_time
                    )
                    if interval_bars:
                        ctx.set_bars(interval, interval_bars)
                    else:
                        # 回退：无独立数据源时使用执行周期数据
                        ctx.set_bars(interval, bars_so_far)'''

if old_code in content:
    content = content.replace(old_code, new_code)
    # 同时修改 ctx 构造部分
    content = content.replace(
        'ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=bars_so_far[-1].dt if hasattr(bars_so_far[-1], \'dt\') else None)',
        'eval_time = getattr(bars_so_far[-1], \'dt\', None)\n                ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=eval_time)'
    )
    with open(scan_engine_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ 已更新 _backtest_symbol 数据对齐逻辑")
else:
    print(f"⚠ 未找到需要替换的代码块，可能已更新")

print("\nPhase 5 方法添加完成！")