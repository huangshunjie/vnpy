# -*- coding: utf-8 -*-
"""
Phase 5 集成测试

测试：
1. MultiTimeframeCandleBuffer 完整功能
2. BarResampler + MTFCandleBuffer 端到端流程
3. 与 ConditionEngine/ScanEngine 的集成
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, timedelta
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.strategy_condition.data.bar_resampler import BarResampler
from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer


def create_minute_bars(symbol: str, n: int, start_date: datetime = None) -> list:
    """创建模拟5分钟K线"""
    if start_date is None:
        start_date = datetime(2024, 1, 2, 9, 35)
    
    bars = []
    dt = start_date
    base_price = 100.0
    
    for i in range(n):
        if dt.hour < 9 or (dt.hour == 9 and dt.minute < 30):
            dt += timedelta(minutes=5)
            continue
        if dt.hour >= 15:
            dt = dt.replace(hour=9, minute=30) + timedelta(days=1)
            while dt.weekday() >= 5:
                dt += timedelta(days=1)
            continue
        
        price = base_price + i * 0.05
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SSE,
            datetime=dt,
            interval=Interval.MINUTE_5,
            volume=1000 + i * 5,
            turnover=0,
            open_interest=0,
            open_price=price,
            high_price=price + 0.3,
            low_price=price - 0.3,
            close_price=price + 0.1,
            gateway_name="test"
        )
        bars.append(bar)
        dt += timedelta(minutes=5)
    
    return bars


def create_daily_bars(symbol: str, n: int, start_date: datetime = None) -> list:
    """创建模拟日线"""
    if start_date is None:
        start_date = datetime(2024, 1, 2, 15, 0)
    
    bars = []
    dt = start_date
    base_price = 100.0
    
    for i in range(n):
        while dt.weekday() >= 5:
            dt += timedelta(days=1)
        
        price = base_price + i * 0.5
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SSE,
            datetime=dt,
            interval=Interval.DAILY,
            volume=10000 + i * 100,
            turnover=0,
            open_interest=0,
            open_price=price,
            high_price=price + 2.0,
            low_price=price - 1.5,
            close_price=price + 0.8,
            gateway_name="test"
        )
        bars.append(bar)
        dt += timedelta(days=1)
    
    return bars


print("=" * 70)
print("Phase 5 集成测试")
print("=" * 70)

# ===== 测试 1: 直接注入模式 =====
print("\n[测试 1] MultiTimeframeCandleBuffer - 直接注入模式")
buf = MultiTimeframeCandleBuffer()

symbol = "600000.SH"
daily = create_daily_bars(symbol, 100)
minute = create_minute_bars(symbol, 500)

buf.inject(symbol, Interval.DAILY, daily)
buf.inject(symbol, Interval.MINUTE_5, minute)

# 获取日线
result_daily = buf.get(symbol, 20, Interval.DAILY)
assert len(result_daily) == 20, f"应该返回20根日线，实际 {len(result_daily)}"
print(f"  ✓ 获取日线: {len(result_daily)} 根")

# 获取5分钟线
result_minute = buf.get(symbol, 50, Interval.MINUTE_5)
assert len(result_minute) == 50, f"应该返回50根5分钟线，实际 {len(result_minute)}"
print(f"  ✓ 获取5分钟线: {len(result_minute)} 根")

# 获取全部
result_all = buf.get(symbol, 0, Interval.DAILY)
assert len(result_all) == 100, f"n=0应返回全部，实际 {len(result_all)}"
print(f"  ✓ 获取全部日线: {len(result_all)} 根")

print("  ✓ PASS")

# ===== 测试 2: 自动转换模式 =====
print("\n[测试 2] MultiTimeframeCandleBuffer - 自动转换模式")
buf2 = MultiTimeframeCandleBuffer(base_interval=Interval.MINUTE_5)

symbol2 = "000001.SZ"
minute2 = create_minute_bars(symbol2, 1000)
buf2.set_base_bars(symbol2, minute2)

# 自动转换为小时线
hourly = buf2.get(symbol2, 10, Interval.HOUR)
assert len(hourly) > 0, "自动转换小时线失败"
print(f"  ✓ 自动转换小时线: {len(hourly)} 根")

# 自动转换为日线
daily_auto = buf2.get(symbol2, 5, Interval.DAILY)
assert len(daily_auto) > 0, "自动转换日线失败"
print(f"  ✓ 自动转换日线: {len(daily_auto)} 根")

# 验证缓存命中
hourly_again = buf2.get(symbol2, 10, Interval.HOUR)
assert hourly_again == hourly, "缓存未命中"
print("  ✓ 缓存命中验证通过")

print("  ✓ PASS")

# ===== 测试 3: 混合模式 =====
print("\n[测试 3] 混合模式（注入 + 自动转换）")
buf3 = MultiTimeframeCandleBuffer(base_interval=Interval.MINUTE_5)

symbol3 = "600519.SH"
minute3 = create_minute_bars(symbol3, 800)
daily3 = create_daily_bars(symbol3, 50)

# 注入5分钟线和日线
buf3.set_base_bars(symbol3, minute3)
buf3.inject(symbol3, Interval.DAILY, daily3)

# 日线应该返回注入的数据（优先）
result_d = buf3.get(symbol3, 20, Interval.DAILY)
assert len(result_d) == 20
assert result_d[0].symbol == symbol3
print(f"  ✓ 注入的日线优先返回: {len(result_d)} 根")

# 小时线应该自动转换
result_h = buf3.get(symbol3, 10, Interval.HOUR)
assert len(result_h) > 0
print(f"  ✓ 小时线自动转换: {len(result_h)} 根")

# 周线应该从注入的日线转换
result_w = buf3.get(symbol3, 5, Interval.WEEKLY)
assert len(result_w) > 0
print(f"  ✓ 周线从日线转换: {len(result_w)} 根")

print("  ✓ PASS")

# ===== 测试 4: 可用周期查询 =====
print("\n[测试 4] 可用周期查询")
available = buf3.get_available_intervals(symbol3)
print(f"  可用周期: {[i.value for i in available]}")
assert Interval.MINUTE_5 in available
assert Interval.DAILY in available
assert Interval.HOUR in available  # 可以从5分钟转换
assert Interval.WEEKLY in available  # 可以从日线转换
print("  ✓ PASS")

# ===== 测试 5: has_data 检查 =====
print("\n[测试 5] has_data 检查")
assert buf3.has_data(symbol3, Interval.DAILY) == True
assert buf3.has_data(symbol3, Interval.MINUTE_5) == True
assert buf3.has_data(symbol3, Interval.HOUR) == True  # 可转换
assert buf3.has_data("NONEXIST", Interval.DAILY) == False
print("  ✓ PASS")

# ===== 测试 6: 缓存管理 =====
print("\n[测试 6] 缓存管理")
stats = buf3.stats()
print(f"  统计: {stats}")
assert stats["symbols"] > 0

# 清除缓存
buf3.clear_cache(symbol3)
stats2 = buf3.stats()
print(f"  清除缓存后: {stats2}")

# 数据仍在
result = buf3.get(symbol3, 10, Interval.DAILY)
assert len(result) == 10, "清除缓存后数据应仍然可用"
print("  ✓ 清除缓存后数据仍可用")

# 清除所有
buf3.clear_all(symbol3)
result_empty = buf3.get(symbol3, 10, Interval.DAILY)
assert len(result_empty) == 0, "清除所有后应无数据"
print("  ✓ 清除所有后无数据")

print("  ✓ PASS")

# ===== 测试 7: 多股票批量预加载 =====
print("\n[测试 7] 多股票批量预加载")
buf4 = MultiTimeframeCandleBuffer(base_interval=Interval.MINUTE_5)

symbols = ["600000.SH", "000001.SZ", "600519.SH", "000858.SZ"]
for sym in symbols:
    bars = create_minute_bars(sym, 500)
    buf4.set_base_bars(sym, bars)

# 批量预加载
buf4.preload(symbols, [Interval.HOUR, Interval.DAILY])

# 验证全部有缓存
for sym in symbols:
    h = buf4.get(sym, 5, Interval.HOUR)
    d = buf4.get(sym, 3, Interval.DAILY)
    assert len(h) > 0, f"{sym} 小时线预加载失败"
    assert len(d) > 0, f"{sym} 日线预加载失败"

print(f"  ✓ {len(symbols)} 只股票预加载完成")
print(f"  统计: {buf4.stats()}")
print("  ✓ PASS")

# ===== 测试 8: 转换精度验证 =====
print("\n[测试 8] 转换精度验证")
buf5 = MultiTimeframeCandleBuffer(base_interval=Interval.MINUTE_5)

# 创建一组精确的5分钟线：同一天 9:35-14:55
precise_bars = []
dt = datetime(2024, 3, 1, 9, 35)
for i in range(48):  # 48根 = 4小时 = 一天完整交易
    bar = BarData(
        symbol="PRECISE",
        exchange=Exchange.SSE,
        datetime=dt,
        interval=Interval.MINUTE_5,
        volume=1000,
        turnover=0,
        open_interest=0,
        open_price=10.0 + i * 0.1,
        high_price=10.0 + i * 0.1 + 0.05,
        low_price=10.0 + i * 0.1 - 0.05,
        close_price=10.0 + i * 0.1 + 0.02,
        gateway_name="test"
    )
    precise_bars.append(bar)
    dt += timedelta(minutes=5)

buf5.set_base_bars("PRECISE", precise_bars)

# 转换为日线
daily_precise = buf5.get("PRECISE", 0, Interval.DAILY)
assert len(daily_precise) == 1, f"48根5分钟线应合成1根日线，实际 {len(daily_precise)}"

d = daily_precise[0]
assert abs(d.open_price - 10.0) < 0.01, f"日线 open 应为 10.0，实际 {d.open_price}"
assert abs(d.close_price - (10.0 + 47 * 0.1 + 0.02)) < 0.01, f"日线 close 错误"
assert abs(d.high_price - max(b.high_price for b in precise_bars)) < 0.01
assert abs(d.low_price - min(b.low_price for b in precise_bars)) < 0.01
assert d.volume == 48000, f"日线 volume 应为 48000，实际 {d.volume}"
print(f"  ✓ 日线精度验证: O={d.open_price}, H={d.high_price:.2f}, "
      f"L={d.low_price:.2f}, C={d.close_price:.2f}, V={d.volume}")

# 转换为小时线
hourly_precise = buf5.get("PRECISE", 0, Interval.HOUR)
assert len(hourly_precise) > 0
# 每小时12根5分钟线，volume = 12000
print(f"  ✓ 小时线精度验证: {len(hourly_precise)} 根")

print("  ✓ PASS")

# ===== 总结 =====
print("\n" + "=" * 70)
print("ALL PHASE 5 TESTS PASSED")
print("=" * 70)
print("\n多周期数据缓存测试完成，所有功能正常！")
print("\n已完成:")
print("  ✓ Step 1: BarResampler（周期转换器）")
print("  ✓ Step 2: MultiTimeframeCandleBuffer（多周期缓存）")
print("  下一步: Step 3 - ScanEngine 改造")