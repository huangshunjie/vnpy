"""
调试回测循环内部逻辑
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
from vnpy.trader.constant import Interval
import numpy as np

print("=" * 70)
print("调试回测循环内部逻辑")
print("=" * 70)

# 构造策略
yang_cond = Condition(category=ConditionCategory.KLINE, indicator=ConditionIndicator.KLINE_YANG, params={})
leaf = ConditionNode.leaf(yang_cond)
outer_and = ConditionNode.and_node(leaf)
meta = StrategyMeta(name="test_yang", description="test")
strategy = Strategy(
    meta=meta,
    buy_tree=outer_and,
    sell_tree=ConditionNode.or_node(),
    params=StrategyParams(stop_loss_pct=10.0, max_hold_days=60)
)

# 创建测试数据 - 100根K线，后50根是阳线
bars = []
for i in range(100):
    dt = datetime(2024, 1, 1) + timedelta(days=i)
    if i < 50:
        bars.append(SimpleNamespace(dt=dt, open=100.0, high=105.0, low=95.0, close=98.0, volume=1e6))
    else:
        bars.append(SimpleNamespace(dt=dt, open=100.0, high=107.0, low=99.0, close=105.0, volume=1.2e6))

# 模拟 scan_engine.backtest 中的逻辑
print("\n[模拟回测循环]")
warmup = 20
n_bars = len(bars)
all_bars = bars
ce = ConditionEngine()

# 预计算数组（模拟 scan_engine 的做法）
_all_closes = np.array([b.close for b in all_bars], dtype=np.float64)
_all_opens = np.array([b.open for b in all_bars], dtype=np.float64)

def _make_precomputed(end_idx):
    return {
        "closes": _all_closes[:end_idx],
        "opens": _all_opens[:end_idx],
        "highs": np.array([b.high for b in all_bars[:end_idx]], dtype=np.float64),
        "lows": np.array([b.low for b in all_bars[:end_idx]], dtype=np.float64),
        "volumes": np.array([float(b.volume) for b in all_bars[:end_idx]], dtype=np.float64),
    }

def _eval_fn_fast(cond, sym, bars, _precomputed=None):
    if _precomputed is not None:
        return ce.eval_condition(cond, sym, bars, _precomputed=_precomputed)
    else:
        return ce.eval_condition(cond, sym, bars)

# 测试几个关键索引
test_indices = [50, 51, 52]  # 第一根阳线和之后
for i in test_indices:
    bars_so_far = all_bars[:i + 1]
    precomp = _make_precomputed(i + 1)
    
    print(f"\n  i={i} (bars[:{ i+1}]):")
    print(f"    最后一根K线: open={bars_so_far[-1].open}, close={bars_so_far[-1].close}")
    print(f"    是阳线: {bars_so_far[-1].close > bars_so_far[-1].open}")
    
    # 测试条件评估
    passed, score = strategy.buy_tree.evaluate("TEST001", bars_so_far, 
                                                lambda c, s, b: _eval_fn_fast(c, s, b, _precomputed=precomp))
    print(f"    条件树评估: passed={passed}, score={score:.2f}")
    
    if not passed:
        print(f"    ❌ 条件未通过！")
        # 单独测试条件
        p2, s2 = ce.eval_condition(yang_cond, "TEST001", bars_so_far, _precomputed=precomp)
        print(f"      单条件(带precomp): passed={p2}, score={s2:.2f}")
        p3, s3 = ce.eval_condition(yang_cond, "TEST001", bars_so_far)
        print(f"      单条件(不带precomp): passed={p3}, score={s3:.2f}")

print("\n" + "=" * 70)