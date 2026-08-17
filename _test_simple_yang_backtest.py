"""
测试简单阳线条件的回测
验证回测引擎是否正常工作
"""

from datetime import datetime, timedelta
from vnpy.trader.constant import Interval
from vnpy.strategy_condition.core.strategy import Strategy, StrategyParams
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionTree
from vnpy.strategy_condition.constant import ConditionIndicator
from vnpy.strategy_condition.engine.scan_engine import ScanEngine
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.trader.object import BarData

# 创建简单的测试数据
def create_test_bars(symbol: str, n_bars: int = 100) -> list:
    """创建测试K线数据，交替阳线阴线"""
    bars = []
    base_price = 100.0
    base_dt = datetime(2024, 1, 1)
    
    for i in range(n_bars):
        is_yang = (i % 2 == 0)  # 偶数日为阳线
        
        if is_yang:
            open_price = base_price
            close_price = base_price + 1.0
        else:
            open_price = base_price + 1.0
            close_price = base_price
        
        bar = BarData(
            symbol=symbol,
            exchange=None,
            datetime=base_dt + timedelta(days=i),
            interval=Interval.DAILY,
            volume=1000000,
            turnover=base_price * 1000000,
            open_price=open_price,
            high_price=max(open_price, close_price) + 0.5,
            low_price=min(open_price, close_price) - 0.5,
            close_price=close_price,
            open_interest=0,
            gateway_name="test"
        )
        bars.append(bar)
        base_price = close_price
    
    return bars

# 创建只有"阳线"条件的策略
yang_cond = Condition(
    indicator=ConditionIndicator.KLINE_YANG,
    params={}
)

buy_tree = ConditionTree()
buy_tree.add_condition(yang_cond)

strategy = Strategy(
    name="测试阳线策略",
    buy_tree=buy_tree,
    sell_tree=ConditionTree(),  # 空的卖出条件
    params=StrategyParams()
)

# 准备数据
symbols = ["test001.TEST", "test002.TEST"]
bars_dict = {sym: create_test_bars(sym, 100) for sym in symbols}

# 执行回测
print("=" * 70)
print("测试简单阳线条件回测")
print("=" * 70)
print(f"股票数量: {len(symbols)}")
print(f"K线数量: {len(bars_dict[symbols[0]])}")
print(f"预期阳线数量: ~50 (交替阳阴线)")
print()

ce = ConditionEngine()
se = ScanEngine(ce)

batch = se.backtest(
    symbols=symbols,
    strategy=strategy,
    all_bars_dict=bars_dict,
    warmup=10,
    is_intraday=False,
    execution_interval=Interval.DAILY
)

print(f"实际信号数量: {batch.count}")
print(f"信号详情:")
for sig in batch.signals[:10]:  # 只显示前10个
    print(f"  {sig.symbol} @ {sig.dt} 买入价:{sig.price:.2f}")

if batch.count > 0:
    print("\n✓ 回测引擎工作正常！")
else:
    print("\n✗ 回测引擎异常：应该产生信号但实际为0")