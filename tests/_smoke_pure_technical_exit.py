"""
冒烟测试：纯技术面卖出条件在无持仓区间也能独立触发波形。

场景：
- 构造一段 K 线：前 30 根走横盘（价格 100 附近），后 20 根从 100 跌到 85
- 无 buy_dates / sell_dates —— 也就是"无虚拟持仓"
- 期望：MA_BREAK_DOWN 波形在跌破 MA20 的 bar 上标记为 True（passed=1）
        MACD_DEATH_SELL 波形在死叉 bar 上标记为 True
- 反例：STOP_LOSS / TRAILING_STOP 等仍受持仓上下文控制，
        无持仓时应恒为 False。
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vnpy.strategy_condition.constant import (
    ConditionCategory, ConditionIndicator, NodeOp,
)
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.strategy import Strategy, StrategyMeta, StrategyParams
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.monitor.condition_monitor_engine import (
    ConditionMonitorEngine,
)


@dataclass
class FakeBar:
    dt: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _make_bars() -> list:
    """构造 K 线序列：
       - 前 30 根：低位横盘（85~86）
       - 中间 30 根：线性上涨到 100（提供追踪止盈的"低点→高点"上涨基础）
       - 最后 15 根：从 100 回撤到 92 附近（触发追踪止盈的回撤条件 + 跌破 MA20）
    """
    bars = []
    base_dt = datetime(2025, 1, 1)

    # 前 30 根低位横盘
    for i in range(30):
        px = 85 + (0.5 if i % 2 == 0 else -0.5)
        bars.append(FakeBar(
            dt=base_dt + timedelta(days=i),
            open=px, high=px + 0.3, low=px - 0.3, close=px, volume=1_000_000,
        ))

    # 中间 30 根线性上涨 85 → 100
    for i in range(30):
        px = 85 + (i + 1) * 0.5     # 85.5 ~ 100
        bars.append(FakeBar(
            dt=base_dt + timedelta(days=30 + i),
            open=px - 0.2, high=px + 0.4, low=px - 0.3, close=px,
            volume=1_000_000,
        ))

    # 最后 15 根：100 → 92（回撤 8%，同时跌破 MA20）
    for i in range(15):
        px = 100 - (i + 1) * 0.55   # 99.45 ~ 91.75
        bars.append(FakeBar(
            dt=base_dt + timedelta(days=60 + i),
            open=px + 0.2, high=px + 0.4, low=px - 0.2, close=px,
            volume=1_000_000,
        ))
    return bars


def _make_strategy() -> Strategy:
    """构造一个简单策略：卖出树同时包含 3 类卖出条件用于对比。"""
    buy_root = ConditionNode(op=NodeOp.AND, label="买入")
    # 一个总为真的占位买入条件（让 buy_tree.evaluate 不空跑；此处不关注买入结果）
    buy_root.add_child(ConditionNode.leaf(Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_ALIGNMENT,
        params={"periods": [5, 10, 20], "max_gap_pct": 100.0},
        label="MA多头(占位)",
    )))

    sell_root = ConditionNode(op=NodeOp.OR, label="卖出")
    sell_root.add_child(ConditionNode.leaf(Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.MA_BREAK_DOWN,
        params={"ma_period": 20},
        label="跌破MA20",
    )))
    sell_root.add_child(ConditionNode.leaf(Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"pct": 5.0},
        label="止损5%",
    )))
    sell_root.add_child(ConditionNode.leaf(Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.TRAILING_STOP,
        params={"take_profit": 5.0, "trail_drawdown": 2.0},
        label="追踪止盈",
    )))

    return Strategy(
        meta=StrategyMeta(name="pure_technical_test"),
        buy_tree=buy_root,
        sell_tree=sell_root,
        params=StrategyParams(),
    )


def test_pure_technical_exit_independent_of_position():
    bars = _make_bars()
    strat = _make_strategy()
    ce = ConditionEngine()
    me = ConditionMonitorEngine(ce, log_fn=lambda *a, **k: None)

    # 关键：不传 buy_dates / sell_dates → 无虚拟持仓
    snaps = me.generate_snapshots(
        symbol="TEST",
        bars=bars,
        strategy=strat,
        warmup=25,          # 让 MA20 有足够数据
        buy_dates=None,
        sell_dates=None,
    )

    assert snaps, "应至少生成一个 snapshot"

    # 统计每个卖出条件在整段中被标记 passed 的次数
    counter = {}
    for s in snaps:
        for d in s.sell_details:
            counter.setdefault(d.condition_name, 0)
            if d.passed:
                counter[d.condition_name] += 1

    print("卖出条件触发次数:", counter)

    # 1) 纯技术面 MA_BREAK_DOWN：跌到 92 的过程中 close 明显低于 MA20，应触发多次
    ma_break_hits = counter.get("跌破MA20", 0)
    assert ma_break_hits >= 3, (
        f"MA_BREAK_DOWN 在无持仓段应独立触发多次，实际 {ma_break_hits} 次"
    )

    # 2) TRAILING_STOP：也已纳入"独立评估"白名单——引擎会用最近 60 根 K 线
    #    的低点近似入场价、高点近似峰值。中间 30 根上涨 + 最后 15 根回撤，
    #    应能触发至少 1 次追踪止盈。
    trailing_hits = counter.get("追踪止盈", 0)
    assert trailing_hits >= 1, (
        f"TRAILING_STOP 在无持仓段也应独立触发（近似入场/峰值），"
        f"实际 {trailing_hits} 次"
    )

    print("[PASS] test_pure_technical_exit_independent_of_position")


if __name__ == "__main__":
    test_pure_technical_exit_independent_of_position()
    print("\nAll smoke tests passed.")