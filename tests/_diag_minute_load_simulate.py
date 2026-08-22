"""完全模拟 _load_minute_bars_for_monitor 真实流程"""
import sys
sys.path.insert(0, '.')

from datetime import datetime
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval

db = get_database()
symbol = '600028.SSE'

# 模拟 daily_bars(取数据库里的日线)
parts = symbol.split(".")
code = parts[0]
exch_str = parts[1] if len(parts) > 1 else ""
exchange = Exchange(exch_str)

raw_d = db.load_bar_data(
    symbol=code, exchange=exchange,
    interval=Interval.DAILY,
    start=datetime(2000, 1, 1), end=datetime(2099, 12, 31),
)
print(f"日线 raw: {len(raw_d)}")

# 模拟 daily_bars 是 list[BarData],用 raw_d 直接模拟(因为 BarAdapter 暴露 .datetime)
class BarAdapter:
    def __init__(self, b): self._b = b
    @property
    def datetime(self): return self._b.datetime
    @property
    def open(self): return self._b.open_price
    @property
    def close(self): return self._b.close_price
    @property
    def high(self): return self._b.high_price
    @property
    def low(self): return self._b.low_price
    @property
    def volume(self): return self._b.volume

daily_bars = [BarAdapter(b) for b in raw_d]
print(f"daily_bars: {len(daily_bars)}")

# _load_minute_bars_for_monitor 的实际逻辑
first_dt = getattr(daily_bars[0], "datetime", None)
last_dt = getattr(daily_bars[-1], "datetime", None)
print(f"first_dt: {first_dt}  tz={first_dt.tzinfo}")
print(f"last_dt:  {last_dt}  tz={last_dt.tzinfo}")

start_d = first_dt.date() if hasattr(first_dt, "date") else first_dt
end_d = last_dt.date() if hasattr(last_dt, "date") else last_dt
print(f"start_d: {start_d}")
print(f"end_d:   {end_d}")

minute_interval = Interval.MINUTE_5

# === 模拟 _load_bars_by_date_range ===
start_dt = datetime.combine(start_d, datetime.min.time())
end_dt   = datetime.combine(end_d, datetime.max.time())
print(f"\nstart_dt = {start_dt} (tz={start_dt.tzinfo})")
print(f"end_dt   = {end_dt} (tz={end_dt.tzinfo})")

# 第一次
raw = db.load_bar_data(
    symbol=code, exchange=exchange,
    interval=minute_interval,
    start=start_dt, end=end_dt,
)
print(f"\n[第一次] raw count: {len(raw) if raw else 0}")
if raw:
    print(f"  first: {raw[0].datetime}  tz={raw[0].datetime.tzinfo}")
    print(f"  last:  {raw[-1].datetime}  tz={raw[-1].datetime.tzinfo}")
else:
    print("  ← raw 为空!会进入 widened 分支")
    # 第二次 widened
    far_end = datetime(2099, 12, 31, 23, 59, 59)
    raw2 = db.load_bar_data(
        symbol=code, exchange=exchange,
        interval=minute_interval,
        start=start_dt, end=far_end,
    )
    print(f"\n[第二次 widened] raw2 count: {len(raw2) if raw2 else 0}")
    if raw2:
        print(f"  first: {raw2[0].datetime}  tz={raw2[0].datetime.tzinfo}")
        print(f"  last:  {raw2[-1].datetime}  tz={raw2[-1].datetime.tzinfo}")
        if getattr(raw2[0].datetime, "tzinfo", None) is not None:
            cutoff = end_dt.replace(tzinfo=raw2[0].datetime.tzinfo)
        else:
            cutoff = end_dt
        print(f"  cutoff: {cutoff}  tz={cutoff.tzinfo}")
        raw2 = [b for b in raw2 if b.datetime <= cutoff]
        print(f"  after cutoff: {len(raw2)}")
        if raw2:
            print(f"  first: {raw2[0].datetime}")
            print(f"  last:  {raw2[-1].datetime}")
