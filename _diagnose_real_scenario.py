"""
诊断用户实际场景: 阳线条件 + 止损-8% + data_interval='d' + 真实股票数据
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from dataclasses import dataclass
from vnpy.trader.constant import Interval
from vnpy.strategy_condition.constant import ConditionIndicator, ConditionCategory, NodeOp
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.strategy import Strategy, StrategyParams, StrategyMeta
from vnpy.strategy_condition.core.mtf_context import analyze_data_requirements
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.engine.scan_engine import ScanEngine

@dataclass
class FakeBar:
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    dt: datetime = None

def make_bars(n=200):
    """模拟真实股票数据：有涨有跌"""
    bars = []
    price = 10.0
    import random
    random.seed(42)
    base_date = datetime(2020, 1, 2)
    for i in range(n):
        chg = random.uniform(-0.03, 0.04) * price
        o = price
        c = price + chg
        h = max(o, c) + random.uniform(0, 0.5)
        l = min(o, c) - random.uniform(0, 0.5)
        bars.append(FakeBar(
            open=round(o, 2), high=round(h, 2),
            low=round(l, 2), close=round(c, 2),
            volume=random.randint(100000, 5000000),
            dt=base_date + timedelta(days=i)
        ))
        price = c
    return bars

print("="*70)
print("诊断：模拟用户实际场景（含 data_interval 设置）")
print("="*70)

# 1. 构造与用户截图一致的策略结构
# 买入: [AND] → [AND] → [OR] → LEAF(KLINE_YANG, data_interval='d')
yang_cond = Condition(
    category=ConditionCategory.KLINE,
    indicator=ConditionIndicator.KLINE_YANG,
    params={},
    weight=1.0,
    data_interval=Interval.DAILY,  # 用户截图显示 data_interval: 日线
)

# 卖出: [OR] → LEAF(STOP_LOSS, pct=8.0, data_interval='d')
stop_cond = Condition(
    category=ConditionCategory.EXIT,
    indicator=ConditionIndicator.STOP_LOSS,
    params={"pct": 8.0},
    weight=1.0,
    data_interval=Interval.DAILY,
)

# 构造买入树
yang_leaf = ConditionNode.leaf(yang_cond)
or_node = ConditionNode.or_node(yang_leaf)
inner_and = ConditionNode.and_node(or_node)
buy_tree = ConditionNode.and_node(inner_and)

# 构造卖出树
stop_leaf = ConditionNode.leaf(stop_cond)
sell_tree = ConditionNode.or_node(stop_leaf)

print(f"\n[1] 买入树: {buy_tree}")
print(f"    所有买入条件: {[c.indicator.value for c in buy_tree.all_conditions()]}")
print(f"    买入条件 data_interval: {[c.data_interval for c in buy_tree.all_conditions()]}")
print(f"\n[2] 卖出树: {sell_tree}")
print(f"    所有卖出条件: {[c.indicator.value for c in sell_tree.all_conditions()]}")
print(f"    卖出条件 data_interval: {[c.data_interval for c in sell_tree.all_conditions()]}")

# 2. 检查 analyze_data_requirements 的结果
req = analyze_data_requirements(buy_tree, Interval.DAILY)
print(f"\n[3] 数据需求分析:")
print(f"    intervals = {[i.value for i in req.intervals]}")
print(f"    is_multi_timeframe = {len(req.intervals) > 1}")
print(f"    strategy_execution_interval = {req.strategy_execution_interval}")

# 3. 创建测试数据
bars = make_bars(200)
yang_count = sum(1 for b in bars if b.close > b.open)
yin_count = sum(1 for b in bars if b.close <= b.open)
print(f"\n[4] 测试数据: {len(bars)} 根K线")
print(f"    阳线数量: {yang_count}, 阴线数量: {yin_count}")
print(f"    前10根阳/阴: {['阳' if b.close > b.open else '阴' for b in bars[:10]]}")

# 4. 直接测试 eval_condition
ce = ConditionEngine()
print(f"\n[5] 直接条件评估:")
# 取一段阳线数据
for i in range(60, 70):
    if bars[i].close > bars[i].open:
        test_bars = bars[:i+1]
        passed, score = ce.eval_condition(yang_cond, "TEST", test_bars)
        print(f"    bars[:{i+1}] (阳线 close={bars[i].close:.2f} > open={bars[i].open:.2f}): passed={passed}, score={score}")
        break

# 5. 测试条件树评估
print(f"\n[6] 条件树评估:")
test_bars = bars[:70]
# 确保最后一根是阳线
for i in range(69, 60, -1):
    if bars[i].close > bars[i].open:
        test_bars = bars[:i+1]
        passed, score = buy_tree.evaluate("TEST", test_bars, ce.eval_condition)
        print(f"    buy_tree (bars[:{i+1}], 最后一根阳线): passed={passed}, score={score}")
        break

# 6. 测试卖出树（空仓状态下的同日冲突检查）
print(f"\n[7] 卖出树评估（同日冲突检查场景）:")
last_bar = test_bars[-1]
sell_result = sell_tree.evaluate(
    "TEST", test_bars,
    lambda cond, sym, b: ce.eval_exit(
        cond, last_bar.close, last_bar.close, last_bar.close, 0, b, None
    )
)
print(f"    sell_tree (entry=cur=peak={last_bar.close:.2f}, hold=0): {sell_result}")
print(f"    → 如果 True，买入会被同日冲突拦截！")

# 7. 创建策略并回测
sp = StrategyParams(
    stop_loss_pct=8.0,
    take_profit_pct=4.0,
    trail_drawdown=15.0,
    max_hold_days=60,
    cooldown_days=3,
    min_bars=60,
)
strategy = Strategy(
    meta=StrategyMeta(name="test_yang_real"),
    buy_tree=buy_tree,
    sell_tree=sell_tree,
    params=sp,
)

print(f"\n[8] 执行回测:")
se = ScanEngine(ce)
batch = se.backtest(
    ["TEST001"],
    strategy,
    {"TEST001": bars},
    warmup=60,
)
print(f"    信号数量: {batch.count}")
if batch.count > 0:
    print(f"    ✓ 回测成功！")
    for s in batch.signals[:5]:
        print(f"      {s.symbol} @ {s.dt} price={s.price:.2f} exit={s.exit_price:.2f} pnl={s.pnl_pct*100:.2f}% reason={s.exit_reason}")
else:
    print(f"    ❌ 回测无结果！")
    # 逐步诊断
    print(f"\n[9] 逐步诊断回测循环:")
    import numpy as np
    n_bars = len(bars)
    _all_closes = np.array([b.close for b in bars], dtype=np.float64)
    _all_opens = np.array([b.open for b in bars], dtype=np.float64)
    
    buy_attempts = 0
    buy_passed = 0
    sell_conflict = 0
    
    for i in range(60, min(100, n_bars-1)):
        bars_so_far = bars[:i+1]
        passed, score = buy_tree.evaluate("TEST001", bars_so_far, ce.eval_condition)
        if passed:
            buy_passed += 1
            # 检查同日冲突
            sell_triggered, _ = sell_tree.evaluate(
                "TEST001", bars_so_far,
                lambda cond, sym, b: ce.eval_exit(
                    cond, bars[i].close, bars[i].close, bars[i].close, 0, b, sp
                )
            )
            if sell_triggered:
                sell_conflict += 1
                if sell_conflict <= 3:
                    print(f"    bar[{i}]: 买入通过但卖出也触发(同日冲突)")
                    # 详细分析为什么止损触发
                    for sc in sell_tree.all_conditions():
                        r = ce.eval_exit(sc, bars[i].close, bars[i].close, bars[i].close, 0, bars_so_far, sp)
                        print(f"      {sc.indicator.value}: {r}")
        buy_attempts += 1
    
    print(f"\n    统计: 检查 {buy_attempts} 根K线, 买入条件通过 {buy_passed} 次, 同日冲突 {sell_conflict} 次")

print("\n" + "="*70)
print("诊断完成")
print("="*70)