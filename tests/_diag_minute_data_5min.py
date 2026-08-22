"""诊断 600028.SSE 的 5min 数据是否能加载到"""
import sys
sys.path.insert(0, '.')

from datetime import datetime
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval

db = get_database()

# 日线数据
print("=== 日线 ===")
raw_d = db.load_bar_data(
    symbol='600028', exchange=Exchange.SSE,
    interval=Interval.DAILY,
    start=datetime(2000, 1, 1), end=datetime(2099, 12, 31),
)
print(f"日线数量: {len(raw_d) if raw_d else 0}")
if raw_d:
    print(f"首: {raw_d[0].datetime}")
    print(f"末: {raw_d[-1].datetime}")

# 5分钟数据
print("\n=== 5分钟 ===")
raw_5m = db.load_bar_data(
    symbol='600028', exchange=Exchange.SSE,
    interval=Interval.MINUTE_5,
    start=datetime(2000, 1, 1), end=datetime(2099, 12, 31),
)
print(f"5min 数量: {len(raw_5m) if raw_5m else 0}")
if raw_5m:
    print(f"首: {raw_5m[0].datetime}  tz={raw_5m[0].datetime.tzinfo}")
    print(f"末: {raw_5m[-1].datetime}  tz={raw_5m[-1].datetime.tzinfo}")

# 用日线范围(2026-01-30 .. 2026-05-08)查 5min
print("\n=== 5min (用户日线范围 2026-01-30..2026-05-08) ===")
raw_5m2 = db.load_bar_data(
    symbol='600028', exchange=Exchange.SSE,
    interval=Interval.MINUTE_5,
    start=datetime(2026, 1, 30, 0, 0, 0),
    end=datetime(2026, 5, 8, 23, 59, 59),
)
print(f"5min 数量: {len(raw_5m2) if raw_5m2 else 0}")
if raw_5m2:
    print(f"首: {raw_5m2[0].datetime}")
    print(f"末: {raw_5m2[-1].datetime}")
