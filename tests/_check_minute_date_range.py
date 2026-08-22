# -*- coding: utf-8 -*-
"""检查600028.SSE的5分钟数据时间范围"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime

print("=" * 70)
print("检查 600028.SSE 的5分钟数据时间范围")
print("=" * 70)

db = get_database()

minute_bars = db.load_bar_data(
    symbol="600028",
    exchange=Exchange.SSE,
    interval=Interval.MINUTE_5,
    start=datetime(2010, 1, 1),
    end=datetime(2027, 1, 1),
)

if not minute_bars:
    print("\n数据库中没有5分钟数据！")
else:
    print(f"\n5分钟数据总量: {len(minute_bars)} 根")
    print(f"数据起始时间: {minute_bars[0].datetime}")
    print(f"数据结束时间: {minute_bars[-1].datetime}")
    
    # 检查与回测日期的关系
    backtest_start = datetime(2011, 11, 9)  # 从截图中看到的预估起始日期
    
    print(f"\n回测起始日期: {backtest_start}")
    print(f"5分钟数据起始: {minute_bars[0].datetime}")
    
    if minute_bars[0].datetime > backtest_start:
        gap_days = (minute_bars[0].datetime - backtest_start).days
        print(f"\n*** 发现问题 ***")
        print(f"5分钟数据比回测起始时间晚 {gap_days} 天")
        print(f"\n这就是为什么Monitor面板显示'暂无5分钟数据'的原因：")
        print(f"Monitor面板查询时使用回测的起始日期({backtest_start.date()}),")
        print(f"但数据库中的5分钟数据从{minute_bars[0].datetime.date()}才开始,")
        print(f"导致查询范围不匹配，返回0根数据。")
        print(f"\n解决方案:")
        print(f"1. 下载更早期的5分钟数据(从{backtest_start.date()}开始)")
        print(f"2. 或调整回测起始日期至{minute_bars[0].datetime.date()}之后")
    else:
        print(f"\n数据时间范围正常,5分钟数据覆盖了回测期间")
        print(f"问题可能在其他地方,需要进一步调试代码逻辑")

print("\n" + "=" * 70)