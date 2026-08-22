# -*- coding: utf-8 -*-
"""检查600028.SSE所有周期数据的时间范围，找出重叠区域"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime

print("=" * 80)
print("检查 600028.SSE 各周期数据时间范围")
print("=" * 80)

db = get_database()
symbol = "600028"
exchange = Exchange.SSE

# 检查各周期
intervals = [
    (Interval.DAILY, "日线"),
    (Interval.MINUTE_5, "5分钟"),
    (Interval.MINUTE_15, "15分钟"),
    (Interval.MINUTE_30, "30分钟"),
    (Interval.MINUTE, "1分钟"),
]

data_ranges = {}

for interval, name in intervals:
    bars = db.load_bar_data(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        start=datetime(2008, 1, 1),
        end=datetime(2027, 1, 1),
    )
    
    if bars:
        start_time = bars[0].datetime
        end_time = bars[-1].datetime
        count = len(bars)
        data_ranges[interval] = (start_time, end_time, count)
        
        print(f"\n{name}:")
        print(f"  数据量: {count:,} 根")
        print(f"  起始: {start_time}")
        print(f"  结束: {end_time}")
    else:
        print(f"\n{name}: 无数据")

# 找出时间重叠区域
print("\n" + "=" * 80)
print("时间范围重叠分析")
print("=" * 80)

if data_ranges:
    # 找出最晚的起始时间和最早的结束时间
    all_starts = [dr[0] for dr in data_ranges.values()]
    all_ends = [dr[1] for dr in data_ranges.values()]
    
    latest_start = max(all_starts)
    earliest_end = min(all_ends)
    
    print(f"\n所有周期数据的重叠区间:")
    print(f"  建议回测起始日期: {latest_start.date()}")
    print(f"  建议回测结束日期: {earliest_end.date()}")
    
    # 检查每个周期是否覆盖
    print(f"\n各周期覆盖情况:")
    for interval, name in intervals:
        if interval in data_ranges:
            start, end, count = data_ranges[interval]
            covers = start <= latest_start and end >= earliest_end
            status = "✓ 完全覆盖" if covers else "✗ 不完全覆盖"
            print(f"  {name}: {status}")
            if not covers:
                if start > latest_start:
                    print(f"    注意: 起始晚了 {(start - latest_start).days} 天")
                if end < earliest_end:
                    print(f"    注意: 结束早了 {(earliest_end - end).days} 天")
    
    # 给出具体建议
    print(f"\n" + "=" * 80)
    print("回测参数建议")
    print("=" * 80)
    print(f"\n在回测对话框中设置:")
    print(f"  起始日期: {latest_start.date()}")
    print(f"  结束日期: {earliest_end.date()}")
    print(f"\n使用这个时间范围，所有周期(日线和分钟线)的数据都完整可用,")
    print(f"Monitor面板的日线-分钟联动功能可以正常工作。")

print("\n" + "=" * 80)