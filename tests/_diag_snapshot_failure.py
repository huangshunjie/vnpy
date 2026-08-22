"""模拟 _feed_monitor 完整流程,验证 minute_snapshots 是否生成成功"""
import sys
sys.path.insert(0, '.')

from datetime import datetime
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval

db = get_database()
symbol = '600028.SSE'

# 拿日线
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

# 拿 5min
raw_5m = db.load_bar_data(
    symbol=code, exchange=exchange,
    interval=Interval.MINUTE_5,
    start=datetime(2026, 1, 1), end=datetime(2099, 12, 31),
)
print(f"5min raw: {len(raw_5m)}")

# 用 _BarAdapter 包装
class _BarAdapter:
    def __init__(self, b): self._b = b
    @property
    def open(self): return self._b.open_price
    @property
    def close(self): return self._b.close_price
    @property
    def high(self): return self._b.high_price
    @property
    def low(self): return self._b.low_price
    @property
    def volume(self): return float(self._b.volume)
    @property
    def dt(self): return self._b.datetime
    @property
    def datetime(self): return self._b.datetime

daily_bars = [_BarAdapter(b) for b in raw_d]
minute_bars = [_BarAdapter(b) for b in raw_5m]

# 尝试生成 minute snapshots
print("\n--- 尝试 generate_snapshots ---")
try:
    from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.core.strategy import Strategy, StrategyNode

    ce = ConditionEngine()
    eng = ConditionMonitorEngine(ce)
    # 创建一个空的 strategy(用户场景中可能也有)
    strategy = Strategy(name='test')
    print(f"strategy: {strategy}, buy_tree={strategy.buy_tree}, sell_tree={strategy.sell_tree}")

    snaps = eng.generate_snapshots(
        symbol=symbol,
        bars=minute_bars,
        strategy=strategy,
        warmup=100,
        buy_dates=[],
        sell_dates=[],
    )
    print(f"minute snapshots: {len(snaps)}")
except Exception as e:
    import traceback
    print(f"生成失败: {type(e).__name__}: {e}")
    traceback.print_exc()
