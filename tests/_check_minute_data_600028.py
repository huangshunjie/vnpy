# -*- coding: utf-8 -*-
"""检查600028.SSE的5分钟数据是否存在"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime

print("=" * 60)
print("检查 600028.SSE 的5分钟数据")
print("=" * 60)

db = get_database()

symbol = "600028"
exchange = Exchange.SSE
start = datetime(2020, 1, 1)  # 从更早时间开始查
end = datetime(2026, 8, 22)

print(f"\n查询参数:")
print(f"  股票代码: {symbol}.{exchange.value}")
print(f"  周期: 5分钟")
print(f"  时间范围: {start.date()} 至 {end.date()}")
print()

# 检查5分钟数据
minute_bars = db.load_bar_data(
    symbol=symbol,
    exchange=exchange,
    interval=Interval.MINUTE_5,
    start=start,
    end=end
)

print(f"5分钟数据量: {len(minute_bars)}")

if not minute_bars:
    print("\n❌ 数据库中没有该股票的5分钟数据！")
    print("\n这就是为什么界面显示'5分钟 0 根'的原因。")
    print("\n解决方案:")
    print("1. 使用vnpy的数据下载功能下载600028.SSE的5分钟历史数据")
    print("2. 或者使用其他已有5分钟数据的股票进行测试")
    print()
    
    # 检查是否有日线数据作为对比
    daily_bars = db.load_bar_data(
        symbol=symbol,
        exchange=exchange,
        interval=Interval.DAILY,
        start=start,
        end=end
    )
    print(f"对比：日线数据量 = {len(daily_bars)}")
    if daily_bars:
        print(f"  日线时间范围: {daily_bars[0].datetime.date()} 至 {daily_bars[-1].datetime.date()}")
        print("\n说明：数据库中有日线数据，但缺少5分钟数据")
else:
    print(f"\n✓ 有 {len(minute_bars)} 根5分钟K线")
    print(f"  时间范围: {minute_bars[0].datetime} 至 {minute_bars[-1].datetime}")
    print("\n如果代码显示'5分钟 0 根'，说明是代码逻辑问题，不是数据问题")

print("\n" + "=" * 60)