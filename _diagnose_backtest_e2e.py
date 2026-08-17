"""
端到端诊断：从策略定义到回测执行的完整流程
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from types import SimpleNamespace
from vnpy.strategy_condition.constant import ConditionIndicator, ConditionCategory
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.strategy import Strategy, StrategyParams, StrategyMeta
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.engine.scan_engine import ScanEngine
from vnpy.trader.constant import Interval

print("=" * 70)
print("端到端回测诊断：模拟用户的「阳线」策略")
print("=" * 70)

# 1. 构造策略
print("\n[1] 构造策略...")
yang_cond = Condition(
    category=ConditionCategory.KLINE,
    indicator=ConditionIndicator.KLINE_YANG,
    params={}
)

# 模拟界面中的嵌套：[AND] -> [AND] -> [OR] -> 阳线
leaf = ConditionNode.leaf(yang_cond)
or_node = ConditionNode.or_node(leaf)
inner_and = ConditionNode.and_node(or_node)
outer_and = ConditionNode.and_node(inner_and)

meta = StrategyMeta(name="test_yang", description="test")
strategy = Strategy(
    meta=meta,
    buy_tree=outer_and,
    sell_tree=ConditionNode.or_node(),
    params=StrategyParams(stop_loss_pct=10.0, max_hold_days=60)
)

print(f"  策略名称: {strategy.meta.name}")
print(f"  买入树: AND -> AND -> OR -> LEAF(KLINE_YANG)")

# 2. 创建测试数据
print("\n[2] 创建测试数据...")
bars = []
for i in range(100):
    dt = datetime(2024, 1, 1) + timedelta(days=i)
    if i < 50:
        # 阴线
        bars.append(SimpleNamespace(dt=dt, open=100.0, high=105.0, low=95.0, close=98.0, volume=1e6))
    else:
        # 阳线
        bars.append(SimpleNamespace(dt=dt, open=100.0, high=107.0, low=99.0, close=105.0, volume=1.2e6))

print(f"  100根K线: 前50阴线, 后50阳线")

# 3. 单条件测试
print("\n[3] 单条件评估测试...")
ce = ConditionEngine()

# 阳线区域
test_bars_yang = bars[50:70]
passed, score = ce.eval_condition(yang_cond, "TEST001", test_bars_yang)
print(f"  阳线区域 bars[50:70]: passed={passed}, score={score:.2f}")

# 阴线区域
test_bars_yin = bars[20:40]
passed2, score2 = ce.eval_condition(yang_cond, "TEST001", test_bars_yin)
print(f"  阴线区域 bars[20:40]: passed={passed2}, score={score2:.2f}")

# 4. 条件树评估测试
print("\n[4] 条件树评估测试...")
p_tree, s_tree = strategy.buy_tree.evaluate("TEST001", test_bars_yang, ce.eval_condition)
print(f"  条件树(阳线数据): passed={p_tree}, score={s_tree:.2f}")

p_tree2, s_tree2 = strategy.buy_tree.evaluate("TEST001", test_bars_yin, ce.eval_condition)
print(f"  条件树(阴线数据): passed={p_tree2}, score={s_tree2:.2f}")

# 5. 回测
print("\n[5] 执行回测...")
engine = ScanEngine(condition_engine=ce)
batch = engine.backtest(
    symbols=["TEST001"],
    strategy=strategy,
    all_bars_dict={"TEST001": bars},
    warmup=20,
    is_intraday=False,
    execution_interval=Interval.DAILY
)

print(f"  信号数量: {batch.count}")

if batch.count > 0:
    print(f"\n  ✓ 回测成功！")
    for sig in batch.signals[:5]:
        print(f"    - {sig.symbol} @ {sig.dt} price={sig.price:.2f} score={sig.score:.2f}")
else:
    print(f"\n  ❌ 回测无结果！")
    
    # 深入调试
    print("\n  [调试] 检查 backtest loop 中的条件评估...")
    # 模拟第51根K线（第一根阳线）
    bars_at_51 = bars[:51]
    p51, s51 = strategy.buy_tree.evaluate("TEST001", bars_at_51, ce.eval_condition)
    print(f"    bars[:51] (阳线出现): passed={p51}, score={s51:.2f}")
    
    # 检查 _eval_fn_fast 是否有问题
    print("\n  [调试] 检查 _precomputed 模式...")
    import numpy as np
    _all_closes = np.array([b.close for b in bars], dtype=np.float64)
    _all_highs = np.array([b.high for b in bars], dtype=np.float64)
    _all_lows = np.array([b.low for b in bars], dtype=np.float64)
    _all_volumes = np.array([float(b.volume) for b in bars], dtype=np.float64)
    
    precomputed = {
        "closes": _all_closes[:51],
        "highs": _all_highs[:51],
        "lows": _all_lows[:51],
        "volumes": _all_volumes[:51],
    }
    
    p_pre, s_pre = ce.eval_condition(yang_cond, "TEST001", bars_at_51, _precomputed=precomputed)
    print(f"    带 _precomputed: passed={p_pre}, score={s_pre:.2f}")
    
    p_no, s_no = ce.eval_condition(yang_cond, "TEST001", bars_at_51)
    print(f"    不带 _precomputed: passed={p_no}, score={s_no:.2f}")

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)