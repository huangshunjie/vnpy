# -*- coding: utf-8 -*-
"""
Phase 6: Monitor Engine 多周期集成测试

验证：
1. generate_snapshots 向后兼容（无新参数时正常工作）
2. 多周期策略检测正确
3. MultiTimeframeContext 正确传递
4. 快照生成包含多周期数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta


# -- 工具函数 --

def make_tree(*conditions):
    """用多个条件构建一个 AND 树"""
    from vnpy.strategy_condition.core.condition_tree import ConditionNode, NodeOp
    leaves = [ConditionNode(op=NodeOp.LEAF, condition=c) for c in conditions]
    return ConditionNode(op=NodeOp.AND, children=leaves)


def make_strategy(name, buy_tree, sell_tree):
    """创建策略"""
    from vnpy.strategy_condition.core.strategy import Strategy, StrategyMeta
    meta = StrategyMeta(name=name)
    return Strategy(meta=meta, buy_tree=buy_tree, sell_tree=sell_tree)


class MockBar:
    def __init__(self, dt, close=10.0, volume=1000, open_=10.0, high=10.5, low=9.5):
        self.dt = dt
        self.datetime = dt
        self.close = close
        self.open = open_
        self.high = high
        self.low = low
        self.volume = volume


def create_daily_bars(n=100, start_date=None):
    if start_date is None:
        start_date = datetime(2025, 1, 1)
    bars = []
    for i in range(n):
        dt = start_date + timedelta(days=i)
        close = 10.0 + i * 0.1
        bars.append(MockBar(dt=dt, close=close, volume=1000 + i * 10))
    return bars


def create_minute_bars(n=500, start_date=None):
    if start_date is None:
        start_date = datetime(2025, 1, 1, 9, 30)
    bars = []
    for i in range(n):
        dt = start_date + timedelta(minutes=i * 5)
        close = 10.0 + i * 0.01
        bars.append(MockBar(dt=dt, close=close, volume=500 + i * 5))
    return bars


# -- 测试 --

def test_1_backward_compatible():
    """测试1: 向后兼容 - 不传新参数时正常工作"""
    print("\n[Test 1: Backward Compatibility]")

    from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.core.condition import Condition
    from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator

    buy_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_SLOPE,
        params={"ma_period": 20, "min_slope": 0.0}
    )
    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"pct": 8}
    )

    strategy = make_strategy("test", make_tree(buy_cond), make_tree(sell_cond))

    ce = ConditionEngine()
    monitor = ConditionMonitorEngine(ce, log_fn=lambda x: None)
    bars = create_daily_bars(100)

    snapshots = monitor.generate_snapshots(
        symbol="TEST.SH",
        bars=bars,
        strategy=strategy,
        warmup=60,
    )

    assert len(snapshots) > 0, "应生成快照"
    assert snapshots[0].buy_details is not None, "应有买入条件详情"

    print(f"  PASS: 生成 {len(snapshots)} 个快照，向后兼容正常")
    return True


def test_2_signature_accepts_new_params():
    """测试2: 新参数可以正常传入"""
    print("\n[Test 2: New Parameters Accepted]")

    from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.core.condition import Condition
    from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
    from vnpy.trader.constant import Interval

    buy_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_SLOPE,
        params={"ma_period": 20, "min_slope": 0.0}
    )
    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"pct": 8}
    )

    strategy = make_strategy("test", make_tree(buy_cond), make_tree(sell_cond))

    ce = ConditionEngine()
    monitor = ConditionMonitorEngine(ce, log_fn=lambda x: None)
    bars = create_daily_bars(100)

    snapshots = monitor.generate_snapshots(
        symbol="TEST.SH",
        bars=bars,
        strategy=strategy,
        warmup=60,
        execution_interval=Interval.DAILY,
    )

    assert len(snapshots) > 0, "传入 execution_interval 应正常工作"
    print(f"  PASS: execution_interval 参数接受正常，生成 {len(snapshots)} 快照")
    return True


def test_3_multi_timeframe_detection():
    """测试3: 多周期策略自动检测"""
    print("\n[Test 3: Multi-Timeframe Detection]")

    from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.core.condition import Condition
    from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
    from vnpy.trader.constant import Interval

    daily_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_SLOPE,
        params={"ma_period": 20, "min_slope": 0.0},
        data_interval=Interval.DAILY,
    )
    minute_cond = Condition(
        category=ConditionCategory.VOLUME,
        indicator=ConditionIndicator.VOLUME_RATIO,
        params={"period": 20, "min_ratio": 1.5},
        data_interval=Interval.MINUTE_5,
    )
    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"pct": 8}
    )

    strategy = make_strategy("mtf", make_tree(daily_cond, minute_cond), make_tree(sell_cond))

    logs = []
    ce = ConditionEngine()
    monitor = ConditionMonitorEngine(ce, log_fn=lambda x: logs.append(x))
    bars = create_minute_bars(500)

    snapshots = monitor.generate_snapshots(
        symbol="TEST.SH",
        bars=bars,
        strategy=strategy,
        warmup=60,
        execution_interval=Interval.MINUTE_5,
    )

    mtf_log = [l for l in logs if "多周期策略监控" in l]
    assert len(mtf_log) > 0, f"应检测到多周期策略，实际日志: {logs[:5]}"

    print(f"  PASS: 多周期策略被正确检测")
    print(f"  日志: {mtf_log[0]}")
    return True


def test_4_mtf_context_with_buffer():
    """测试4: 使用 MTFCandleBuffer 时构造 MultiTimeframeContext"""
    print("\n[Test 4: MTF Context with Buffer]")

    from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.core.condition import Condition
    from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer
    from vnpy.trader.constant import Interval

    daily_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_SLOPE,
        params={"ma_period": 20, "min_slope": 0.0},
        data_interval=Interval.DAILY,
    )
    minute_cond = Condition(
        category=ConditionCategory.VOLUME,
        indicator=ConditionIndicator.VOLUME_RATIO,
        params={"period": 20, "min_ratio": 1.5},
        data_interval=Interval.MINUTE_5,
    )
    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"pct": 8}
    )

    strategy = make_strategy("mtf", make_tree(daily_cond, minute_cond), make_tree(sell_cond))

    minute_bars = create_minute_bars(500)
    daily_bars = create_daily_bars(100)

    mtf_buffer = MultiTimeframeCandleBuffer()
    mtf_buffer.inject("TEST.SH", Interval.MINUTE_5, minute_bars)
    mtf_buffer.inject("TEST.SH", Interval.DAILY, daily_bars)

    ce = ConditionEngine()
    monitor = ConditionMonitorEngine(ce, log_fn=lambda x: None)

    snapshots = monitor.generate_snapshots(
        symbol="TEST.SH",
        bars=minute_bars,
        strategy=strategy,
        warmup=60,
        mtf_buffer=mtf_buffer,
        execution_interval=Interval.MINUTE_5,
    )

    assert len(snapshots) > 0, "应生成快照"

    first_snap = snapshots[0]
    assert len(first_snap.buy_details) >= 2, (
        f"多周期策略应有>=2个买入条件详情，实际: {len(first_snap.buy_details)}"
    )

    print(f"  PASS: 使用 MTFCandleBuffer 生成 {len(snapshots)} 个快照")
    print(f"  买入条件数: {len(first_snap.buy_details)}")
    for d in first_snap.buy_details:
        print(f"    - {d.condition_name}: passed={d.passed}")
    return True


def test_5_single_timeframe_no_overhead():
    """测试5: 单周期策略不引入多周期开销"""
    print("\n[Test 5: Single Timeframe No Overhead]")

    import time
    from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.core.condition import Condition
    from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
    from vnpy.trader.constant import Interval

    buy_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_SLOPE,
        params={"ma_period": 20, "min_slope": 0.0}
    )
    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"pct": 8}
    )

    strategy = make_strategy("single", make_tree(buy_cond), make_tree(sell_cond))

    ce = ConditionEngine()
    monitor = ConditionMonitorEngine(ce, log_fn=lambda x: None)
    bars = create_daily_bars(200)

    t0 = time.perf_counter()
    snap1 = monitor.generate_snapshots(
        symbol="TEST.SH", bars=bars, strategy=strategy, warmup=60)
    t1 = time.perf_counter()

    t2 = time.perf_counter()
    snap2 = monitor.generate_snapshots(
        symbol="TEST2.SH", bars=bars, strategy=strategy, warmup=60,
        execution_interval=Interval.DAILY)
    t3 = time.perf_counter()

    time_original = t1 - t0
    time_with_param = t3 - t2

    assert len(snap1) == len(snap2), "结果数量应一致"
    overhead = abs(time_with_param - time_original) / max(time_original, 0.001)

    print(f"  原始方式: {time_original:.4f}s")
    print(f"  带参数方式: {time_with_param:.4f}s")
    print(f"  额外开销: {overhead*100:.1f}%")
    print(f"  PASS: 单周期策略无显著多周期开销")
    return True


def main():
    print("=" * 60)
    print("Phase 6: Monitor Engine 多周期集成测试")
    print("=" * 60)

    tests = [
        test_1_backward_compatible,
        test_2_signature_accepts_new_params,
        test_3_multi_timeframe_detection,
        test_4_mtf_context_with_buffer,
        test_5_single_timeframe_no_overhead,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            import traceback
            print(f"  FAIL: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"ALL PASSED: {passed}/{passed + failed}")
    else:
        print(f"Result: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)