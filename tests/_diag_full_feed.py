"""完全模拟 _feed_monitor 流程,捕获所有异常"""
import sys
sys.path.insert(0, '.')

import traceback
from datetime import datetime
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval

db = get_database()
symbol = '600028.SSE'

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

raw_5m = db.load_bar_data(
    symbol=code, exchange=exchange,
    interval=Interval.MINUTE_5,
    start=datetime(2026, 1, 1), end=datetime(2099, 12, 31),
)
print(f"5min raw: {len(raw_5m)}")

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

# 测试 generate_snapshots
print("\n--- 测试 minute generate_snapshots ---")
try:
    from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.core.strategy import Strategy

    ce = ConditionEngine()
    eng = ConditionMonitorEngine(ce)
    strategy = Strategy(name='test')
    print(f"strategy.buy_tree = {strategy.buy_tree}")
    print(f"strategy.sell_tree = {strategy.sell_tree}")

    # 给一个简单的买入/卖出条件(避免空 strategy)
    from vnpy.strategy_condition.core.condition import Condition, ConditionNode, ConditionOp
    print(f"添加买入条件: MA斜率向上...")
    # 用 cond_tree 是更简单的
    print("尝试不传 strategy.buy_tree 评估...")
    snaps = eng.generate_snapshots(
        symbol=symbol,
        bars=minute_bars[:200],  # 取小点,避免太慢
        strategy=strategy,
        warmup=10,
        buy_dates=[],
        sell_dates=[],
    )
    print(f"minute snapshots: {len(snaps)}")
except Exception as e:
    traceback.print_exc()
    print(f"\n*** 生成失败: {type(e).__name__}: {e} ***")
