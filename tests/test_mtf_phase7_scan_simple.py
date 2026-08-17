#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 7: ScanEngine 多周期集成测试（简化版）

验证核心多周期功能，不依赖复杂的指标逻辑。
"""
import sys
import os
from datetime import datetime, timedelta
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnpy.trader.constant import Interval
from vnpy.strategy_condition.engine.scan_engine import ScanEngine
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.strategy import Strategy, StrategyParams
from vnpy.strategy_condition.core.mtf_context import analyze_data_requirements
from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer
from vnpy.strategy_condition.constant import ConditionIndicator, ConditionCategory


@dataclass
class MockBar:
    """模拟 K 线数据"""
    open: float = 10.0
    high: float = 11.0
    low: float = 9.5
    close: float = 10.5
    volume: float = 1000000.0
    dt: datetime = None

    def __post_init__(self):
        if self.dt is None:
            self.dt = datetime(2025, 1, 1)


def make_bars(n: int, base_price: float = 10.0, interval_days: int = 1) -> list:
    """生成模拟 K 线序列"""
    bars = []
    start_date = datetime(2025, 1, 1)
    for i in range(n):
        price = base_price + i * 0.1
        dt = start_date + timedelta(days=i * interval_days)
        bars.append(MockBar(
            open=price - 0.05,
            high=price + 0.5,
            low=price - 0.5,
            close=price,
            volume=1000000.0 + i * 10000,
            dt=dt,
        ))
    return bars


def make_simple_strategy() -> Strategy:
    """创建简单策略（使用实际存在的指标）"""
    buy_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MACD_GOLDEN,
        params={},
    )
    buy_tree = ConditionNode(logic="AND", conditions=[buy_cond])

    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={},
    )
    sell_tree = ConditionNode(logic="OR", conditions=[sell_cond])

    return Strategy(
        name="简单测试策略",
        buy_tree=buy_tree,
        sell_tree=sell_tree,
        params=StrategyParams(),
    )


def make_mtf_strategy() -> Strategy:
    """创建多周期策略"""
    # 日线条件
    daily_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MACD_GOLDEN,
        params={},
    )

    # 周线条件（设置 data_interval）
    weekly_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MACD_GOLDEN,
        params={},
        data_interval=Interval.WEEKLY,
    )

    buy_tree = ConditionNode(logic="AND", conditions=[daily_cond, weekly_cond])

    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={},
    )
    sell_tree = ConditionNode(logic="OR", conditions=[sell_cond])

    return Strategy(
        name="多周期测试策略",
        buy_tree=buy_tree,
        sell_tree=sell_tree,
        params=StrategyParams(),
    )


# ── 核心测试 ──────────────────────────────────────────────────────

def test_1_mtf_detection():
    """测试1: 多周期策略自动检测"""
    print("\n[测试1] 多周期策略自动检测")
    
    single_strategy = make_simple_strategy()
    mtf_strategy = make_mtf_strategy()
    
    # 分析单周期策略
    req1 = analyze_data_requirements(single_strategy.buy_tree, Interval.DAILY)
    print(f"  单周期策略需要的周期: {[i.value for i in req1.intervals]}")
    assert len(req1.intervals) == 1
    assert Interval.DAILY in req1.intervals
    
    # 分析多周期策略
    req2 = analyze_data_requirements(mtf_strategy.buy_tree, Interval.DAILY)
    print(f"  多周期策略需要的周期: {[i.value for i in req2.intervals]}")
    assert len(req2.intervals) > 1
    assert Interval.DAILY in req2.intervals
    assert Interval.WEEKLY in req2.intervals
    
    print("  ✓ 多周期检测正常")


def test_2_mtf_buffer_integration():
    """测试2: MTFCandleBuffer 集成"""
    print("\n[测试2] MTFCandleBuffer 集成")
    
    ce = ConditionEngine()
    se = ScanEngine(ce)
    
    # 初始无 buffer
    assert se.get_mtf_buffer() is None
    print("  ✓ 初始状态无 buffer")
    
    # 设置 buffer
    mtf_buffer = MultiTimeframeCandleBuffer()
    se.set_mtf_buffer(mtf_buffer)
    assert se.get_mtf_buffer() is mtf_buffer
    print("  ✓ 成功设置 buffer")
    
    # 注入数据
    bars = make_bars(50)
    mtf_buffer.inject("TEST.SH", Interval.DAILY, bars)
    result = se._get_bars("TEST.SH", 50, Interval.DAILY)
    assert len(result) == 50
    print(f"  ✓ 成功获取 {len(result)} 根K线")


def test_3_scan_execution():
    """测试3: scan() 执行流程"""
    print("\n[测试3] scan() 执行流程")
    
    ce = ConditionEngine()
    se = ScanEngine(ce)
    strategy = make_simple_strategy()
    
    # 准备数据
    bars_dict = {"TEST.SH": make_bars(100)}
    
    # 执行 scan
    batch = se.scan(
        symbols=["TEST.SH"],
        strategy=strategy,
        n_bars=100,
        _bars_dict=bars_dict,
    )
    
    assert batch is not None
    assert batch.strategy_name == "简单测试策略"
    print(f"  ✓ scan() 正常执行，返回 {batch.count} 个信号")


def test_4_backtest_execution():
    """测试4: backtest() 执行流程"""
    print("\n[测试4] backtest() 执行流程")
    
    ce = ConditionEngine()
    se = ScanEngine(ce)
    strategy = make_simple_strategy()
    
    # 构造回测数据
    bars = make_bars(200, base_price=10.0)
    all_bars_dict = {"TEST.SH": bars}
    
    # 执行回测
    batch = se.backtest(
        symbols=["TEST.SH"],
        strategy=strategy,
        all_bars_dict=all_bars_dict,
        warmup=60,
    )
    
    assert batch is not None
    assert batch.strategy_name == "简单测试策略"
    print(f"  ✓ backtest() 正常执行，返回 {batch.count} 个信号")


def test_5_mtf_scan_with_buffer():
    """测试5: 多周期 scan() 集成"""
    print("\n[测试5] 多周期 scan() 集成")
    
    ce = ConditionEngine()
    se = ScanEngine(ce)
    strategy = make_mtf_strategy()
    
    # 准备多周期数据
    daily_bars = make_bars(100, base_price=10.0)
    weekly_bars = make_bars(20, base_price=10.0, interval_days=7)
    
    # 设置 MTF Buffer
    mtf_buffer = MultiTimeframeCandleBuffer()
    mtf_buffer.inject("TEST.SH", Interval.DAILY, daily_bars)
    mtf_buffer.inject("TEST.SH", Interval.WEEKLY, weekly_bars)
    se.set_mtf_buffer(mtf_buffer)
    
    # 执行多周期 scan
    batch = se.scan(
        symbols=["TEST.SH"],
        strategy=strategy,
        n_bars=100,
        execution_interval=Interval.DAILY,
    )
    
    assert batch is not None
    assert batch.strategy_name == "多周期测试策略"
    print(f"  ✓ 多周期 scan() 正常执行，返回 {batch.count} 个信号")


def test_6_mtf_backtest_with_buffer():
    """测试6: 多周期 backtest() 集成"""
    print("\n[测试6] 多周期 backtest() 集成")
    
    ce = ConditionEngine()
    se = ScanEngine(ce)
    strategy = make_mtf_strategy()
    
    # 准备多周期数据
    daily_bars = make_bars(200, base_price=10.0)
    weekly_bars = make_bars(40, base_price=10.0, interval_days=7)
    all_bars_dict = {"TEST.SH": daily_bars}
    
    # 设置 MTF Buffer
    mtf_buffer = MultiTimeframeCandleBuffer()
    mtf_buffer.inject("TEST.SH", Interval.DAILY, daily_bars)
    mtf_buffer.inject("TEST.SH", Interval.WEEKLY, weekly_bars)
    se.set_mtf_buffer(mtf_buffer)
    
    # 执行多周期回测
    batch = se.backtest(
        symbols=["TEST.SH"],
        strategy=strategy,
        all_bars_dict=all_bars_dict,
        warmup=60,
        execution_interval=Interval.DAILY,
    )
    
    assert batch is not None
    assert batch.strategy_name == "多周期测试策略"
    print(f"  ✓ 多周期 backtest() 正常执行，返回 {batch.count} 个信号")


# ── 主入口 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 7: ScanEngine 多周期集成测试（简化版）")
    print("=" * 60)
    
    tests = [
        test_1_mtf_detection,
        test_2_mtf_buffer_integration,
        test_3_scan_execution,
        test_4_backtest_execution,
        test_5_mtf_scan_with_buffer,
        test_6_mtf_backtest_with_buffer,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n  ✗ {test.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败 / 共 {len(tests)} 项")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ Phase 7 ScanEngine 多周期集成测试全部通过!")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败")
        sys.exit(1)