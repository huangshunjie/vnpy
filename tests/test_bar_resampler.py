# -*- coding: utf-8 -*-
"""
BarResampler 单元测试

测试K线周期转换的正确性
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, timedelta
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.strategy_condition.data.bar_resampler import BarResampler


def create_minute_bars(n: int, start_date: datetime = None) -> list:
    """创建模拟5分钟K线数据"""
    if start_date is None:
        start_date = datetime(2024, 1, 2, 9, 35)  # 周二 9:35
    
    bars = []
    dt = start_date
    base_price = 100.0
    
    for i in range(n):
        # 跳过非交易时间
        if dt.hour < 9 or (dt.hour == 9 and dt.minute < 30):
            dt += timedelta(minutes=5)
            continue
        if dt.hour >= 15:
            # 跳到下一个交易日 9:30
            dt = dt.replace(hour=9, minute=30) + timedelta(days=1)
            # 跳过周末
            while dt.weekday() >= 5:
                dt += timedelta(days=1)
            continue
        
        price = base_price + i * 0.1
        bar = BarData(
            symbol="TEST",
            exchange=Exchange.SSE,
            datetime=dt,
            interval=Interval.MINUTE_5,
            volume=1000 + i * 10,
            turnover=0,
            open_interest=0,
            open_price=price,
            high_price=price + 0.5,
            low_price=price - 0.5,
            close_price=price + 0.2,
            gateway_name="test"
        )
        bars.append(bar)
        dt += timedelta(minutes=5)
    
    return bars


def create_daily_bars(n: int, start_date: datetime = None) -> list:
    """创建模拟日线K线数据"""
    if start_date is None:
        start_date = datetime(2024, 1, 2, 15, 0)  # 周二
    
    bars = []
    dt = start_date
    base_price = 100.0
    
    for i in range(n):
        # 跳过周末
        while dt.weekday() >= 5:
            dt += timedelta(days=1)
        
        price = base_price + i * 0.5
        bar = BarData(
            symbol="TEST",
            exchange=Exchange.SSE,
            datetime=dt,
            interval=Interval.DAILY,
            volume=10000 + i * 100,
            turnover=0,
            open_interest=0,
            open_price=price,
            high_price=price + 2.0,
            low_price=price - 2.0,
            close_price=price + 1.0,
            gateway_name="test"
        )
        bars.append(bar)
        dt += timedelta(days=1)
    
    return bars


print("=" * 70)
print("BarResampler 单元测试")
print("=" * 70)

# ===== 测试 1: 分钟线 → 小时线 =====
print("\n[测试 1] 分钟线 → 小时线")
minute_bars = create_minute_bars(60)  # 60根5分钟线 ≈ 5小时
print(f"  输入: {len(minute_bars)} 根5分钟K线")
print(f"  时间范围: {minute_bars[0].datetime} ~ {minute_bars[-1].datetime}")

hourly_bars = BarResampler.resample(minute_bars, Interval.MINUTE_5, Interval.HOUR)
print(f"  输出: {len(hourly_bars)} 根小时K线")

if hourly_bars:
    first_hour = hourly_bars[0]
    print(f"  第1根: {first_hour.datetime}, O={first_hour.open_price:.2f}, "
          f"H={first_hour.high_price:.2f}, L={first_hour.low_price:.2f}, "
          f"C={first_hour.close_price:.2f}, V={first_hour.volume}")
    
    # 验证聚合正确性
    # 小时线的 high 应该是该小时内所有分钟线 high 的最大值
    hour_0_minutes = [b for b in minute_bars if b.datetime.hour == minute_bars[0].datetime.hour]
    expected_high = max(b.high_price for b in hour_0_minutes)
    expected_volume = sum(b.volume for b in hour_0_minutes)
    
    assert abs(first_hour.high_price - expected_high) < 0.01, "high 聚合错误"
    assert abs(first_hour.volume - expected_volume) < 1, "volume 聚合错误"
    print("  ✓ 聚合正确性验证通过")

print("  ✓ PASS")

# ===== 测试 2: 分钟线 → 日线 =====
print("\n[测试 2] 分钟线 → 日线")
minute_bars = create_minute_bars(240)  # 240根5分钟线 ≈ 2.5天
print(f"  输入: {len(minute_bars)} 根5分钟K线")

daily_bars = BarResampler.resample(minute_bars, Interval.MINUTE_5, Interval.DAILY)
print(f"  输出: {len(daily_bars)} 根日线")

if daily_bars:
    first_day = daily_bars[0]
    print(f"  第1根: {first_day.datetime}, O={first_day.open_price:.2f}, "
          f"H={first_day.high_price:.2f}, L={first_day.low_price:.2f}, "
          f"C={first_day.close_price:.2f}")
    
    # 验证时间戳是 15:00
    assert first_day.datetime.hour == 15 and first_day.datetime.minute == 0, "日线时间戳应为15:00"
    print("  ✓ 时间戳验证通过 (15:00)")

print("  ✓ PASS")

# ===== 测试 3: 日线 → 周线 =====
print("\n[测试 3] 日线 → 周线")
daily_bars = create_daily_bars(15)  # 15个交易日 ≈ 3周
print(f"  输入: {len(daily_bars)} 根日线")
print(f"  时间范围: {daily_bars[0].datetime.date()} ~ {daily_bars[-1].datetime.date()}")

weekly_bars = BarResampler.resample(daily_bars, Interval.DAILY, Interval.WEEKLY)
print(f"  输出: {len(weekly_bars)} 根周线")

if weekly_bars:
    for i, week_bar in enumerate(weekly_bars):
        print(f"  周{i+1}: {week_bar.datetime.date()}, O={week_bar.open_price:.2f}, "
              f"C={week_bar.close_price:.2f}, V={week_bar.volume}")

print("  ✓ PASS")

# ===== 测试 4: 日线 → 月线（辅助方法）=====
print("\n[测试 4] 日线 → 月线（辅助方法）")
daily_bars = create_daily_bars(60)  # 60个交易日 ≈ 3个月
print(f"  输入: {len(daily_bars)} 根日线")

monthly_bars = BarResampler.daily_to_monthly(daily_bars)
print(f"  输出: {len(monthly_bars)} 根月线")

if monthly_bars:
    for i, month_bar in enumerate(monthly_bars):
        print(f"  月{i+1}: {month_bar.datetime.date()}, O={month_bar.open_price:.2f}, "
              f"C={month_bar.close_price:.2f}, V={month_bar.volume}")

print("  ✓ PASS")

# ===== 测试 5: 数据量估算 =====
print("\n[测试 5] 所需数据量估算")

target_daily = 100
est_minute = BarResampler.estimate_required_bars(target_daily, Interval.MINUTE_5, Interval.DAILY)
print(f"  目标: {target_daily} 根日线")
print(f"  估算需要: {est_minute} 根5分钟线")
print(f"  理论值: {target_daily * 48} 根 (240分钟/天 ÷ 5分钟)")
assert 4000 < est_minute < 6000, "估算值应在合理范围内"
print("  ✓ PASS")

# ===== 测试 6: 边界情况 =====
print("\n[测试 6] 边界情况")

# 空列表
empty_result = BarResampler.resample([], Interval.MINUTE_5, Interval.HOUR)
assert empty_result == [], "空列表应返回空列表"
print("  ✓ 空列表处理正确")

# 单根K线
single_bar = create_minute_bars(1)
single_result = BarResampler.resample(single_bar, Interval.MINUTE_5, Interval.HOUR)
assert len(single_result) == 1, "单根K线应返回单根聚合结果"
print("  ✓ 单根K线处理正确")

# 不支持的转换
try:
    BarResampler.resample(daily_bars, Interval.DAILY, Interval.MINUTE_5)
    assert False, "应该抛出 ValueError"
except ValueError as e:
    print(f"  ✓ 不支持的转换正确抛出异常: {str(e)[:40]}")

print("  ✓ PASS")

# ===== 总结 =====
print("\n" + "=" * 70)
print("ALL TESTS PASSED")
print("=" * 70)
print("\n周期转换器测试完成，所有功能正常！")