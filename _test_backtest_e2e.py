# -*- coding: utf-8 -*-
"""
端到端测试：用数据库中现有数据回测"阳线"条件
模拟UI的_on_backtest方法完整流程
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval
from vnpy.strategy_condition.core.condition_tree import ConditionNode, NodeOp
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.constant import ConditionIndicator as CI, ConditionCategory
from vnpy.strategy_condition.core.strategy import Strategy, StrategyParams, StrategyMeta
from vnpy.strategy_condition.engine.scan_engine import ScanEngine
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine

# === 1. 从数据库加载真实数据 ===
db = get_database()
symbols_info = [
    ("600028", Exchange.SSE),
    ("600036", Exchange.SSE),
    ("600426", Exchange.SSE),
]

start_dt = datetime(2020, 1, 1)
end_dt = datetime(2026, 8, 10)

print("=" * 70)
print("E2E backtest test - KLINE_YANG condition")
print("=" * 70)

class BarAdapter:
    __slots__ = ("open", "high", "low", "close", "volume", "turnover", "dt", "open_interest")
    def __init__(self, bar):
        self.open = bar.open_price
        self.high = bar.high_price
        self.low = bar.low_price
        self.close = bar.close_price
        self.volume = bar.volume
        self.turnover = getattr(bar, 'turnover', 0)
        self.dt = bar.datetime
        self.open_interest = getattr(bar, 'open_interest', 0)

bars_dict = {}
for symbol, exchange in symbols_info:
    vt_symbol = f"{symbol}.{exchange.value}"
    raw = db.load_bar_data(
        symbol=symbol, exchange=exchange,
        interval=Interval.DAILY,
        start=start_dt, end=end_dt,
    )
    if raw:
        bars_dict[vt_symbol] = [BarAdapter(b) for b in raw]
        print(f"  {vt_symbol}: {len(raw)} bars (latest: {raw[-1].datetime.date()})")
    else:
        bars_dict[vt_symbol] = []
        print(f"  {vt_symbol}: NO DATA")

loaded = [s for s, b in bars_dict.items() if b]
print(f"\nLoaded {len(loaded)} symbols with data")

if not loaded:
    print("ERROR: No data loaded!")
    sys.exit(1)

# === 2. Build strategy ===
yang_cond = Condition(
    indicator=CI.KLINE_YANG,
    category=ConditionCategory.KLINE,
    params={},
    data_interval=Interval.DAILY,
)

or_node = ConditionNode(op=NodeOp.OR, children=[yang_cond])
buy_tree = ConditionNode(op=NodeOp.AND, children=[or_node])

sell_cond = Condition(
    indicator=CI.STOP_LOSS,
    category=ConditionCategory.EXIT,
    params={"pct": 8.0},
)
sell_tree = ConditionNode(op=NodeOp.OR, children=[sell_cond])

meta = StrategyMeta(name="test_yang")
strategy = Strategy(
    meta=meta,
    buy_tree=buy_tree,
    sell_tree=sell_tree,
    params=StrategyParams(
        max_hold_days=60,
        stop_loss_pct=8.0,
        take_profit_pct=15.0,
    ),
)

# === 3. Run backtest ===
print("\n" + "=" * 70)
print("Executing backtest...")
print("=" * 70)

ce = ConditionEngine()
se = ScanEngine(ce)

try:
    batch = se.backtest(
        symbols=loaded,
        strategy=strategy,
        all_bars_dict=bars_dict,
        warmup=60,
        is_intraday=False,
        execution_interval=Interval.DAILY,
    )
    
    print(f"\nResult: {batch.count} trades")
    
    if batch.count > 0:
        print("\nFirst 10 signals:")
        for i, sig in enumerate(batch.signals[:10]):
            print(f"  [{i+1}] {sig.symbol} @ {sig.dt} price={sig.price:.2f}")
        print("\n[OK] Backtest engine works correctly!")
    else:
        print("\n[FAIL] No signals produced!")
        print("Investigating why...")
        
        # Manual yang detection
        test_sym = loaded[0]
        test_bars = bars_dict[test_sym]
        yang_count = 0
        for i, bar in enumerate(test_bars[60:80]):
            if bar.close > bar.open:
                yang_count += 1
                if yang_count <= 3:
                    print(f"  Yang bar: idx={i+60} dt={bar.dt} o={bar.open:.2f} c={bar.close:.2f}")
        print(f"  Total yang bars in [60:80]: {yang_count}/20")
        
        # Direct condition eval
        print("\n  Direct condition eval test:")
        try:
            result = ce.eval_condition(yang_cond, test_sym, test_bars[:70])
            print(f"  eval_condition result: {result}")
        except Exception as e:
            print(f"  eval_condition error: {e}")
            import traceback
            traceback.print_exc()

        # Try eval_tree
        print("\n  Direct eval_tree test:")
        try:
            result = ce.eval_tree(buy_tree, test_sym, test_bars[:70])
            print(f"  eval_tree result: {result}")
        except Exception as e:
            print(f"  eval_tree error: {e}")
            import traceback
            traceback.print_exc()

except Exception as e:
    print(f"\n[ERROR] Backtest failed: {e}")
    import traceback
    traceback.print_exc()