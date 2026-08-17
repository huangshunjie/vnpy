#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 7: ScanEngine 多周期集成测试

验证：
1. ScanEngine 向后兼容性（单周期策略不受影响）
2. scan() 多周期检测和评估
3. backtest() 多周期回测
4. 条件级路由正确工作
5. MTFCandleBuffer 集成
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
from vnpy.strategy_condition.core.mtf_context import MultiTimeframeContext, analyze_data_requirements
from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer
from vnpy.strategy_condition.constant import ConditionIndicator, ConditionCategory


# ── 测试辅助 ──────────────────────────────────────────────────────

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


def make_bars(n: int, base_price: float = 10.0, interval_days: int = 1,
              start_date: datetime = None) -> list:
    """生成模拟 K 线序列"""
    if start_date is None:
        start_date = datetime(2025, 1, 1)
    
    bars = []
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


def make_single_timeframe_strategy() -> Strategy:
    """创建单周期策略（仅使用日线）"""
    buy_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_CROSS,
        params={"fast_period": 5, "slow_period": 20},
    )
    buy_tree = ConditionNode(logic="AND", conditions=[buy_cond])

    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"threshold": -0.05},
    )
    sell_tree = ConditionNode(logic="OR", conditions=[sell_cond])

    return Strategy(
        name="单周期测试策略",
        buy_tree=buy_tree,
        sell_tree=sell_tree,
        params=StrategyParams(),
    )


def make_multi_timeframe_strategy() -> Strategy:
    """创建多周期策略（日线 + 周线）"""
    # 日线条件（无 data_interval = 使用执行周期）
    daily_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_CROSS,
        params={"fast_period": 5, "slow_period": 20},
    )

    # 周线条件（设置 data_interval = WEEKLY）
    weekly_cond = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_CROSS,
        params={"fast_period": 5, "slow_period": 10},
        data_interval=Interval.WEEKLY,
    )

    buy_tree = ConditionNode(logic="AND", conditions=[daily_cond, weekly_cond])

    sell_cond = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"threshold": -0.05},
    )
    sell_tree = ConditionNode(logic="OR", conditions=[sell_cond])

    return Strategy(
        name="多周期测试策略",
        buy_tree=buy_tree,
        sell_tree=sell_tree,
        params=StrategyParams(),
    )


# ── 测试用例 ──────────────────────────────────────────────────────

def test_1_scan_backward_compatible():
    """测试1: scan() 向后兼容性 - 单周期策略正常工作"""
    ce = ConditionEngine()
    se = ScanEngine(ce)
    strategy = make_single_timeframe_strategy()
    
    # 构造预加载数据
    bars_dict = {"TEST.SH": make_bars(100)}
    
    # scan() 不传多周期参数
    batch = se.scan(
        symbols=["TEST.SH"],
        strategy=strategy,
        n_bars=100,
        _bars_dict=bars_dict,
    )
    
    # 应该正常执行，不抛异常
    assert batch is not None
    assert batch.strategy_name == "单周期测试策略"


def test_2_scan_multi_timeframe_detection():
    """测试2: scan() 多周期策略自动检测"""
    strategy = make_multi_timeframe_strategy()
    
    # 分析数据需求
    req = analyze_data_requirements(strategy.buy_tree, Interval.DAILY)
    
    # 应该检测到多个周期
    assert len(req.intervals) > 1
    assert Interval.DAILY in req.intervals
    assert Interval.WEEKLY in req.intervals


def test_3_scan_multi_timeframe_execution():
    """测试3: scan() 多周期执行流程"""
    ce = ConditionEngine()
    se = ScanEngine(ce)
    strategy = make_multi_timeframe_strategy()
    
    # 准备数据
    daily_bars = make_bars(100, base_price=10.0)
    weekly_bars = make_bars(20, base_price=10.0, interval_days=7)
    
    # 设置 MTF Buffer
    mtf_buffer = MultiTimeframeCandleBuffer()
    mtf_buffer.inject("TEST.SH", Interval.DAILY, daily_bars)
    mtf_buffer.inject("TEST.SH", Interval.WEEKLY, weekly_bars)
    se.set_mtf_buffer(mtf_buffer)
    
    # 执行 scan
    batch = se.scan(
        symbols=["TEST.SH"],
        strategy=strategy,
        n_bars=100,
        execution_interval=Interval.DAILY,
    )
    
    # 应该正常执行
    assert batch is not None
    assert batch.strategy_name == "多周期测试策略"


def test_4_backtest_backward_compatible():
    """测试4: backtest() 向后兼容性 - 单周期策略正常工作"""
    ce = ConditionEngine()
    se = ScanEngine(ce)
    strategy = make_single_timeframe_strategy()
    
    # 构造回测数据
    bars = make_bars(200, base_price=10.0)
    all_bars_dict = {"TEST.SH": bars}
    
    # backtest() 单周期
    batch = se.backtest(
        symbols=["TEST.SH"],
        strategy=strategy,
        all_bars_dict=all_bars_dict,
        warmup=60,
    )
    
    # 应该正常执行
    assert batch is not None
    assert batch.strategy_name == "单周期测试策略"


def test_5_backtest_multi_timeframe():
    """测试5: backtest() 多周期回测"""
    ce = ConditionEngine()
    se = ScanEngine(ce)
    strategy = make_multi_timeframe_strategy()
    
    # 构造回测数据
    daily_bars = make_bars(200, base_price=10.0)
    weekly_bars = make_bars(40, base_price=10.0, interval_days=7)
    all_bars_dict = {"TEST.SH": daily_bars}
    
    # 设置 MTF Buffer
    mtf_buffer = MultiTimeframeCandleBuffer()
    mtf_buffer.inject("TEST.SH", Interval.DAILY, daily_bars)
    mtf_buffer.inject("TEST.SH", Interval.WEEKLY, weekly_bars)
    se.set_mtf_buffer(mtf_buffer)
    
    # backtest() 多周期
    batch = se.backtest(
        symbols=["TEST.SH"],
        strategy=strategy,
        all_bars_dict=all_bars_dict,
        warmup=60,
        execution_interval=Interval.DAILY,
    )
    
    # 应该正常执行
    assert batch is not None
    assert batch.strategy_name == "多周期测试策略"


def test_6_condition_level_routing():
    """测试6: 条件级路由 - 多周期条件使用 eval_condition_mtf"""
    strategy = make_multi_timeframe_strategy()
    
    # 验证条件的 data_interval 属性
    all_conds = strategy.buy_tree.all_conditions()
    
    has_mtf_cond = False
    has_normal_cond = False
    
    for cond in all_conds:
        if hasattr(cond, 'data_interval') and cond.data_interval is not None:
            has_mtf_cond = True
            assert cond.data_interval == Interval.WEEKLY
        else:
            has_normal_cond = True
    
    # 应该同时有多周期条件和普通条件
    assert has_mtf_cond, "应该有多周期条件"
    assert has_normal_cond, "应该有普通条件"


def test_7_mtf_buffer_integration():
    """测试7: MTFCandleBuffer 集成"""
    ce = ConditionEngine()
    se = ScanEngine(ce)
    
    # 初始状态无 buffer
    assert se.get_mtf_buffer() is None
    
    # 设置 buffer
    mtf_buffer = MultiTimeframeCandleBuffer()
    se.set_mtf_buffer(mtf_buffer)
    
    assert se.get_mtf_buffer() is mtf_buffer
    
    # 注入数据
    bars = make_bars(50)
    mtf_buffer.inject("TEST.SH", Interval.DAILY, bars)
    
    # 通过 _get_bars 获取数据
    result = se._get_bars("TEST.SH", 50, Interval.DAILY)
    assert len(result) == 50


def test_8_single_timeframe_no_overhead():
    """测试8: 单周期策略无多周期开销"""
    strategy = make_single_timeframe_strategy()
    
    # 分析数据需求
    req = analyze_data_requirements(strategy.buy_tree, Interval.DAILY)
    
    # 单周期策略只有一个周期
    assert len(req.intervals) == 1
    assert Interval.DAILY in req.intervals
    
    # 不应进入多周期路径
    is_multi_timeframe = len(req.intervals) > 1
    assert not is_multi_timeframe


# ── 主入口 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_1_scan_backward_compatible,
        test_2_scan_multi_timeframe_detection,
        test_3_scan_multi_timeframe_execution,
        test_4_backtest_backward_compatible,
        test_5_backtest_multi_timeframe,
        test_6_condition_level_routing,
        test_7_mtf_buffer_integration,
        test_8_single_timeframe_no_overhead,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"结果: {passed} passed, {failed} failed / {len(tests)} total")
    
    if failed == 0:
        print("✅ Phase 7 ScanEngine 多周期集成测试全部通过!")
    else:
        print("❌ 存在失败的测试")
        sys.exit(1)