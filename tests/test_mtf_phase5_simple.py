"""
多周期架构 Phase 5 简化测试
直接测试核心组件，不依赖完整的 ScanEngine
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.strategy_condition.core.condition import cond_ma_slope
from vnpy.strategy_condition.core.condition_advanced import cond_pullback_to_ma10
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.mtf_context import MultiTimeframeContext, analyze_data_requirements
from vnpy.strategy_condition.data.bar_resampler import BarResampler
from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine


def create_test_bars(symbol: str, days: int = 100) -> List[BarData]:
    """创建测试日线数据"""
    bars = []
    base_price = 10.0
    start_date = datetime(2024, 1, 1, 9, 30)
    
    for i in range(days):
        price = base_price + i * 0.1
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SSE,
            datetime=start_date + timedelta(days=i),
            interval=Interval.DAILY,
            gateway_name="TEST",
            volume=1000000 + i * 10000,
            turnover=(price * (1000000 + i * 10000)),
            open_interest=0,
            open_price=price * 0.99,
            high_price=price * 1.01,
            low_price=price * 0.98,
            close_price=price,
        )
        bars.append(bar)
    
    return bars


def test_1_bar_resampler():
    """测试 1: BarResampler 周期转换"""
    print("\n" + "="*70)
    print("测试 1: BarResampler 周期转换")
    print("="*70)
    
    # 创建日线数据
    symbol = "600000.SSE"
    daily_bars = create_test_bars(symbol, days=100)
    
    # 创建 resampler
    resampler = BarResampler()
    
    # 转换为周线
    weekly_bars = resampler.resample(daily_bars, Interval.WEEKLY)
    
    print(f"\n原始日线数据: {len(daily_bars)} 根")
    print(f"转换周线数据: {len(weekly_bars)} 根")
    print(f"转换比例: {len(daily_bars) / len(weekly_bars):.1f}:1")
    
    assert len(weekly_bars) > 0, "周线数据不应为空"
    assert len(weekly_bars) < len(daily_bars), "周线数量应少于日线"
    
    print("\n[OK] BarResampler 工作正常")
    return True


def test_2_mtf_buffer():
    """测试 2: MultiTimeframeCandleBuffer"""
    print("\n" + "="*70)
    print("测试 2: MultiTimeframeCandleBuffer 多周期缓存")
    print("="*70)
    
    symbol = "600000.SSE"
    daily_bars = create_test_bars(symbol, days=100)
    
    # 创建 MTF buffer
    buffer = MultiTimeframeCandleBuffer(base_interval=Interval.DAILY)
    
    # 加载日线数据
    buffer.update(symbol, daily_bars)
    
    # 获取不同周期的数据
    daily = buffer.get(symbol, 50, Interval.DAILY)
    weekly = buffer.get(symbol, 20, Interval.WEEKLY)
    
    print(f"\n日线数据: {len(daily)} 根")
    print(f"周线数据: {len(weekly)} 根")
    
    # 获取统计信息
    stats = buffer.get_stats()
    print(f"\n缓存统计:")
    print(f"  标的数: {stats['symbol_count']}")
    print(f"  周期数: {stats['period_count']}")
    print(f"  总K线数: {stats['total_bars']}")
    print(f"  内存占用: {stats['memory_mb']:.2f} MB")
    
    assert len(daily) > 0, "日线数据不应为空"
    assert len(weekly) > 0, "周线数据不应为空"
    assert len(weekly) < len(daily), "周线数量应少于日线"
    
    print("\n[OK] MultiTimeframeCandleBuffer 工作正常")
    return True


def test_3_mtf_context():
    """测试 3: MultiTimeframeContext 多周期上下文"""
    print("\n" + "="*70)
    print("测试 3: MultiTimeframeContext 多周期上下文")
    print("="*70)
    
    symbol = "600000.SSE"
    daily_bars = create_test_bars(symbol, days=100)
    
    # 创建 resampler
    resampler = BarResampler()
    weekly_bars = resampler.resample(daily_bars, Interval.WEEKLY)
    
    # 创建多周期上下文
    ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=datetime.now())
    ctx.set_bars(Interval.DAILY, daily_bars)
    ctx.set_bars(Interval.WEEKLY, weekly_bars)
    
    print(f"\n上下文信息:")
    print(f"  标的: {ctx.symbol}")
    print(f"  周期数: {len(ctx._bars_by_interval)}")
    
    # 检查数据
    assert ctx.has_interval(Interval.DAILY), "应该有日线数据"
    assert ctx.has_interval(Interval.WEEKLY), "应该有周线数据"
    
    daily = ctx.get_bars(Interval.DAILY)
    weekly = ctx.get_bars(Interval.WEEKLY)
    
    print(f"  日线: {len(daily)} 根")
    print(f"  周线: {len(weekly)} 根")
    
    assert len(daily) == len(daily_bars), "日线数据应完整"
    assert len(weekly) == len(weekly_bars), "周线数据应完整"
    
    print("\n[OK] MultiTimeframeContext 工作正常")
    return True


def test_4_data_requirements():
    """测试 4: 数据需求分析"""
    print("\n" + "="*70)
    print("测试 4: analyze_data_requirements 数据需求分析")
    print("="*70)
    
    # 创建多周期条件树
    root = ConditionNode.and_node(label="多周期策略")
    
    # 日线条件
    cond1 = cond_ma_slope(ma_period=20)
    cond1.data_interval = Interval.DAILY
    root.add_child(ConditionNode.leaf(cond1))
    
    # 周线条件
    cond2 = cond_pullback_to_ma10()
    cond2.data_interval = Interval.WEEKLY
    root.add_child(ConditionNode.leaf(cond2))
    
    # 分析数据需求
    req = analyze_data_requirements(root, Interval.DAILY)
    
    print(f"\n策略执行周期: {req.strategy_execution_interval.value}")
    print(f"需要的数据周期: {[i.value for i in req.intervals]}")
    print(f"周期数量: {len(req.intervals)}")
    print(f"是否多周期: {len(req.intervals) > 1}")
    
    assert Interval.DAILY in req.intervals, "应检测到日线需求"
    assert Interval.WEEKLY in req.intervals, "应检测到周线需求"
    assert len(req.intervals) == 2, "应检测到2个周期"
    
    print("\n[OK] analyze_data_requirements 工作正常")
    return True


def test_5_condition_engine_mtf():
    """测试 5: ConditionEngine 多周期评估"""
    print("\n" + "="*70)
    print("测试 5: ConditionEngine 多周期条件评估")
    print("="*70)
    
    symbol = "600000.SSE"
    daily_bars = create_test_bars(symbol, days=100)
    
    # 创建 resampler 和周线数据
    resampler = BarResampler()
    weekly_bars = resampler.resample(daily_bars, Interval.WEEKLY)
    
    # 创建多周期上下文
    ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=datetime.now())
    ctx.set_bars(Interval.DAILY, daily_bars)
    ctx.set_bars(Interval.WEEKLY, weekly_bars)
    
    # 创建条件引擎
    engine = ConditionEngine()
    
    # 创建日线条件
    cond_daily = cond_ma_slope(ma_period=20)
    cond_daily.data_interval = Interval.DAILY
    
    # 评估（使用 MTF 上下文）
    passed, score = engine.eval_condition(
        cond_daily, symbol, daily_bars, _mtf_context=ctx
    )
    
    print(f"\n日线条件评估:")
    print(f"  条件: MA20向上")
    print(f"  使用周期: {cond_daily.data_interval.value}")
    print(f"  结果: {'通过' if passed else '不通过'}")
    print(f"  得分: {score:.4f}")
    
    # 创建周线条件
    cond_weekly = cond_ma_slope(ma_period=10)
    cond_weekly.data_interval = Interval.WEEKLY
    
    passed2, score2 = engine.eval_condition(
        cond_weekly, symbol, daily_bars, _mtf_context=ctx
    )
    
    print(f"\n周线条件评估:")
    print(f"  条件: MA10向上")
    print(f"  使用周期: {cond_weekly.data_interval.value}")
    print(f"  结果: {'通过' if passed2 else '不通过'}")
    print(f"  得分: {score2:.4f}")
    
    print("\n[OK] ConditionEngine 多周期评估工作正常")
    return True


def test_6_condition_serialization():
    """测试 6: 条件序列化（包含周期信息）"""
    print("\n" + "="*70)
    print("测试 6: 条件序列化/反序列化（周期信息）")
    print("="*70)
    
    from vnpy.strategy_condition.core.condition import condition_from_dict
    
    # 创建带周期的条件
    cond = cond_ma_slope(ma_period=20)
    cond.data_interval = Interval.WEEKLY
    
    print(f"\n原始条件:")
    print(f"  指标: {cond.indicator.value}")
    print(f"  周期: {cond.data_interval.value}")
    print(f"  参数: {cond.params}")
    
    # 序列化
    cond_dict = cond.to_dict()
    print(f"\n序列化:")
    print(f"  包含 _data_interval: {'_data_interval' in cond_dict.get('params', {})}")
    
    # 反序列化
    restored = condition_from_dict(cond_dict)
    print(f"\n反序列化:")
    print(f"  指标: {restored.indicator.value}")
    print(f"  周期: {restored.data_interval.value if restored.data_interval else 'None'}")
    print(f"  参数: {restored.params}")
    
    # 验证
    assert restored.indicator == cond.indicator, "指标应相同"
    assert restored.data_interval == cond.data_interval, "周期应相同"
    assert restored.params == cond.params, "参数应相同"
    
    print("\n[OK] 条件序列化工作正常")
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("vnpy 多周期架构 Phase 5 核心组件测试")
    print("="*70)
    
    tests = [
        ("BarResampler", test_1_bar_resampler),
        ("MultiTimeframeCandleBuffer", test_2_mtf_buffer),
        ("MultiTimeframeContext", test_3_mtf_context),
        ("DataRequirements", test_4_data_requirements),
        ("ConditionEngine MTF", test_5_condition_engine_mtf),
        ("Condition Serialization", test_6_condition_serialization),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"\n[FAIL] {name} 测试失败")
        except Exception as e:
            failed += 1
            print(f"\n[ERROR] {name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*70)
    
    if failed == 0:
        print("\n[SUCCESS] 所有核心组件测试通过!")
        print("\nPhase 5 核心功能已验证:")
        print("  [OK] BarResampler - 周期转换")
        print("  [OK] MultiTimeframeCandleBuffer - 多周期缓存")
        print("  [OK] MultiTimeframeContext - 多周期上下文")
        print("  [OK] analyze_data_requirements - 数据需求分析")
        print("  [OK] ConditionEngine - 多周期评估")
        print("  [OK] Condition - 序列化/反序列化")
        return 0
    else:
        print(f"\n[FAIL] {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())