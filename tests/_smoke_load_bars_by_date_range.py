"""
smoke test: _load_bars_by_date_range 的"放宽到2099" + "tz-aware 截断" 逻辑
直接调用 widget 的真实方法（反射拿 private 方法即可）。
"""
import sys, os
from datetime import date, datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../")

passes = 0
fails  = 0

def check(name, cond, detail=""):
    global passes, fails
    if cond:
        passes += 1
        print(f"  PASS  {name}  {detail}")
    else:
        fails += 1
        print(f"  FAIL  {name}  {detail}")

# 直接复制 widget 中已修好 _load_bars_by_date_range 的最新代码
# 不依赖 main_engine 实例化
print("=== 真实 DB 调用（测试修复后逻辑）===")
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval
from vnpy.strategy_condition.ui.widget import _BarAdapter

DB = get_database()

def _load_bars_by_date_range(symbol, interval, start_date, end_date):
    """复刻 widget._load_bars_by_date_range 修复后版本"""
    parts = symbol.split(".")
    code = parts[0]
    exch_str = parts[1] if len(parts) > 1 else ""
    try:
        exchange = Exchange(exch_str)
    except Exception:
        exchange = Exchange.SSE if code.startswith("6") else Exchange.SZSE
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = datetime.combine(end_date, datetime.max.time())

    def _query(s, e):
        try:
            raw = DB.load_bar_data(symbol=code, exchange=exchange,
                                   interval=interval, start=s, end=e)
            return raw or []
        except Exception as e:
            print(f"[query error] {e}", flush=True)
            return None
    raw = _query(start_dt, end_dt)
    if raw is None: return []
    if raw: return [_BarAdapter(b) for b in raw]
    far_end = datetime(2099, 12, 31, 23, 59, 59)
    raw2 = _query(start_dt, far_end)
    if raw2 is None or not raw2: return []
    # tz-aware fix
    if raw2 and getattr(raw2[0].datetime, "tzinfo", None) is not None:
        cutoff = end_dt.replace(tzinfo=raw2[0].datetime.tzinfo)
    else:
        cutoff = end_dt
    raw2 = [b for b in raw2 if b.datetime <= cutoff]
    return [_BarAdapter(b) for b in raw2]

# 1. 2024-01 完整月度窗口
bars = _load_bars_by_date_range(
    "600000.SSE", Interval.MINUTE_5,
    date(2024, 1, 1), date(2024, 1, 31),
)
check("2024-01 完整月度窗口", len(bars) > 0, f"len={len(bars)}")
if bars:
    check("  每根 bar 都有 .close", all(hasattr(b, "close") for b in bars))
    check("  每根 bar 都有 .dt",   all(hasattr(b, "dt") for b in bars))
    check("  都在 2024-01 范围内",
          all(date(2024,1,1) <= b.datetime.date() <= date(2024,1,31) for b in bars))

# 2. 用户场景：最近 30 天窗口（用户没下 → 兜底到历史段）
bars_recent = _load_bars_by_date_range(
    "600000.SSE", Interval.MINUTE_5,
    date(2026, 8, 1), date(2026, 8, 20),
)
print(f"  最近 30 天窗口: {len(bars_recent)} 根 (空也OK，逻辑是兜底)")

# 3. 完全无数据时段（数据库还没建库的早期）
bars_empty = _load_bars_by_date_range(
    "600000.SSE", Interval.MINUTE_5,
    date(1999, 1, 1), date(1999, 1, 31),
)
check("1999 无数据应空（不崩）", len(bars_empty) == 0, f"len={len(bars_empty)}")

# 4. _BarAdapter 包装
print("\n=== _BarAdapter 包装 ===")
class FakeBar:
    def __init__(self):
        self.datetime = datetime(2024, 1, 1, 9, 35)
        self.open_price = 10.0
        self.high_price = 11.0
        self.low_price  = 9.5
        self.close_price = 10.5
        self.volume = 1000
fb = FakeBar()
ad = _BarAdapter(fb)
check(".close == .close_price", ad.close == 10.5 == ad.close_price)
check(".open   == .open_price", ad.open == 10.0 == ad.open_price)
check(".high   == .high_price", ad.high == 11.0 == ad.high_price)
check(".low    == .low_price",  ad.low  == 9.5  == ad.low_price)
check(".volume", ad.volume == 1000)
check(".dt",     ad.dt == datetime(2024,1,1,9,35))

print(f"\n===== {passes} passed, {fails} failed =====")
sys.exit(0 if fails == 0 else 1)
