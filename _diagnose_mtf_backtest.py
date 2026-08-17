"""
诊断多时间周期回测数据加载
"""
from vnpy.trader.constant import Interval
from vnpy.trader.database import get_database

# 检查数据库中的5分钟数据
db = get_database()

# 测试股票列表
test_symbols = ["600031.SSE", "688041.SSE", "000001.SZSE"]

print("=" * 80)
print("检查数据库中的分钟数据")
print("=" * 80)

for symbol in test_symbols:
    print(f"\n股票: {symbol}")
    
    # 检查日线数据
    daily_bars = db.load_bar_data(
        symbol=symbol,
        exchange=symbol.split(".")[1],
        interval=Interval.DAILY,
        start=None,
        end=None
    )
    print(f"  日线数据: {len(daily_bars)} 根")
    if daily_bars:
        print(f"    起: {daily_bars[0].datetime}")
        print(f"    止: {daily_bars[-1].datetime}")
    
    # 检查5分钟数据
    minute_5_bars = db.load_bar_data(
        symbol=symbol,
        exchange=symbol.split(".")[1],
        interval=Interval.MINUTE_5,
        start=None,
        end=None
    )
    print(f"  5分钟数据: {len(minute_5_bars)} 根")
    if minute_5_bars:
        print(f"    起: {minute_5_bars[0].datetime}")
        print(f"    止: {minute_5_bars[-1].datetime}")
    
    # 检查1分钟数据
    minute_bars = db.load_bar_data(
        symbol=symbol,
        exchange=symbol.split(".")[1],
        interval=Interval.MINUTE,
        start=None,
        end=None
    )
    print(f"  1分钟数据: {len(minute_bars)} 根")
    if minute_bars:
        print(f"    起: {minute_bars[0].datetime}")
        print(f"    止: {minute_bars[-1].datetime}")

print("\n" + "=" * 80)
print("测试多周期策略数据需求分析")
print("=" * 80)

from vnpy.strategy_condition.core.strategy import Strategy, empty_strategy
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.constant import NodeOp, ConditionIndicator
from vnpy.strategy_condition.core.mtf_auto_loader import analyze_strategy_data_requirements

# 创建测试策略：日线均线多头 + 5分钟缩量阴线
strategy = empty_strategy()
strategy.name = "测试多周期策略"

# 买入条件：AND(均线多头排列[d], 缩量阴线[5m])
buy_and = ConditionNode(op=NodeOp.AND)

# 日线均线多头排列
ma_cond = Condition(indicator=ConditionIndicator.MA_ALIGNMENT)
ma_cond.data_interval = Interval.DAILY
ma_node = ConditionNode(op=NodeOp.LEAF, condition=ma_cond)

# 5分钟缩量阴线
shrink_cond = Condition(indicator=ConditionIndicator.KLINE_SHRINK_YIN)
shrink_cond.data_interval = Interval.MINUTE_5
shrink_node = ConditionNode(op=NodeOp.LEAF, condition=shrink_cond)

buy_and.children = [ma_node, shrink_node]
strategy.buy_tree = buy_and

# 分析数据需求
print(f"\n策略: {strategy.name}")
print(f"买入条件树: {strategy.buy_tree}")

req = analyze_strategy_data_requirements(
    strategy=strategy,
    anchor_interval=Interval.DAILY,
    anchor_bar_count=300
)

print(f"\n数据需求分析结果:")
print(f"  execution_interval: {req.execution_interval}")
print(f"  strategy_execution_interval: {req.strategy_execution_interval}")
print(f"  required_intervals: {[i.value for i in req.required_intervals]}")
print(f"  intervals (set): {[i.value for i in req.intervals]}")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)

has_minute_data = False
for symbol in test_symbols:
    minute_5_bars = db.load_bar_data(
        symbol=symbol,
        exchange=symbol.split(".")[1],
        interval=Interval.MINUTE_5,
        start=None,
        end=None
    )
    if len(minute_5_bars) > 0:
        has_minute_data = True
        break

if has_minute_data:
    print("✓ 数据库中有5分钟数据")
else:
    print("✗ 数据库中没有5分钟数据 - 这是回测无法使用分钟数据的根本原因")

if len(req.required_intervals) > 1:
    print(f"✓ 策略分析正确识别了多个周期: {[i.value for i in req.required_intervals]}")
else:
    print("✗ 策略分析未能识别多个周期")

print("\n如果数据库中没有5分钟数据，需要先导入分钟数据才能进行多周期回测。")