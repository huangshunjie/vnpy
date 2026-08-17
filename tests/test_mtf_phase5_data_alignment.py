# -*- coding: utf-8 -*-
"""
Phase 5 数据对齐和 As-of Time 机制测试

测试内容：
1. MTFCandleBuffer.get_bars_as_of() 正确过滤时间
2. MTFCandleBuffer.set_base_bars_multi() 多数据源
3. ScanEngine._get_bars_as_of() 正确调用
4. 回测中无未来函数泄露
5. 多周期数据独立性验证
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List

from vnpy.trader.constant import Interval


# ─── 测试用 BarData 模拟 ───────────────────────────────────────

@dataclass
class MockBar:
    """模拟 BarData"""
    datetime: datetime
    open_price: float = 10.0
    high_price: float = 11.0
    low_price: float = 9.0
    close_price: float = 10.5
    volume: float = 1000.0
    turnover: float = 10000.0
    open_interest: float = 0.0
    symbol: str = "TEST.SH"
    exchange: str = "SSE"
    interval: str = "d"
    gateway_name: str = ""

    # 兼容属性
    @property
    def open(self):
        return self.open_price

    @property
    def high(self):
        return self.high_price

    @property
    def low(self):
        return self.low_price

    @property
    def close(self):
        return self.close_price

    @property
    def dt(self):
        return self.datetime


def create_daily_bars(n: int, start_date: datetime = None) -> List[MockBar]:
    """创建 n 根日线测试数据"""
    if start_date is None:
        start_date = datetime(2025, 1, 1, 15, 0, 0)
    bars = []
    price = 10.0
    for i in range(n):
        dt = start_date + timedelta(days=i)
        # 跳过周末
        while dt.weekday() >= 5:
            dt += timedelta(days=1)
        price *= (1.0 + (i % 7 - 3) * 0.005)  # 小幅波动
        bars.append(MockBar(
            datetime=dt,
            open_price=round(price * 0.99, 2),
            high_price=round(price * 1.02, 2),
            low_price=round(price * 0.98, 2),
            close_price=round(price, 2),
            volume=float(1000 + i * 10),
            symbol="TEST.SH",
        ))
    return bars


def create_minute_bars(n: int, start_date: datetime = None) -> List[MockBar]:
    """创建 n 根5分钟线测试数据"""
    if start_date is None:
        start_date = datetime(2025, 1, 2, 9, 30, 0)
    bars = []
    price = 10.0
    dt = start_date
    for i in range(n):
        price *= (1.0 + (i % 11 - 5) * 0.001)
        bars.append(MockBar(
            datetime=dt,
            open_price=round(price * 0.999, 2),
            high_price=round(price * 1.002, 2),
            low_price=round(price * 0.998, 2),
            close_price=round(price, 2),
            volume=float(500 + i * 5),
            symbol="TEST.SH",
            interval="5m",
        ))
        dt += timedelta(minutes=5)
        # 跳过午休和收盘后
        if dt.hour == 11 and dt.minute >= 30:
            dt = dt.replace(hour=13, minute=0)
        if dt.hour >= 15:
            dt = (dt + timedelta(days=1)).replace(hour=9, minute=30)
            while dt.weekday() >= 5:
                dt += timedelta(days=1)
    return bars


# ─── 测试函数 ────────────────────────────────────────────────────

def test_1_get_bars_as_of_basic():
    """测试 1: get_bars_as_of 基本功能"""
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer

    buf = MultiTimeframeCandleBuffer()
    bars = create_daily_bars(100)
    buf.inject("TEST.SH", Interval.DAILY, bars)

    # 在第50根K线时间点获取数据
    as_of_time = bars[49].datetime

    result = buf.get_bars_as_of("TEST.SH", 20, Interval.DAILY, as_of_time)

    # 验证：不超过 20 根
    assert len(result) == 20, f"期望20根，实际{len(result)}根"
    # 验证：所有K线时间 <= as_of_time
    for b in result:
        assert b.datetime <= as_of_time, \
            f"未来数据泄露: bar.dt={b.datetime} > as_of={as_of_time}"
    # 验证：最后一根是第50根（索引49）
    assert result[-1].datetime == bars[49].datetime

    print("  ✓ PASS: get_bars_as_of 基本功能正确")


def test_2_get_bars_as_of_no_future_leak():
    """测试 2: 验证不会泄露未来数据"""
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer

    buf = MultiTimeframeCandleBuffer()
    bars = create_daily_bars(200)
    buf.inject("TEST.SH", Interval.DAILY, bars)

    # 在第100根K线时间点
    as_of_time = bars[99].datetime

    # 请求200根（超过可用的100根）
    result = buf.get_bars_as_of("TEST.SH", 200, Interval.DAILY, as_of_time)

    # 验证：只返回前100根
    assert len(result) == 100, f"期望100根，实际{len(result)}根"
    # 验证：最后一根不超过 as_of_time
    assert result[-1].datetime <= as_of_time

    # 验证：没有任何 > as_of_time 的数据
    future_bars = [b for b in result if b.datetime > as_of_time]
    assert len(future_bars) == 0, f"发现 {len(future_bars)} 根未来数据"

    print("  ✓ PASS: 无未来数据泄露")


def test_3_set_base_bars_multi():
    """测试 3: 多数据源注入"""
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer

    buf = MultiTimeframeCandleBuffer()

    daily_bars = create_daily_bars(100)
    minute_bars = create_minute_bars(500)

    # 同时注入多个周期
    buf.set_base_bars_multi("TEST.SH", {
        Interval.DAILY: daily_bars,
        Interval.MINUTE_5: minute_bars,
    })

    # 验证两个周期都可访问
    daily_result = buf.get("TEST.SH", 50, Interval.DAILY)
    minute_result = buf.get("TEST.SH", 50, Interval.MINUTE_5)

    assert len(daily_result) == 50, f"日线期望50，实际{len(daily_result)}"
    assert len(minute_result) == 50, f"分钟线期望50，实际{len(minute_result)}"

    # 验证数据独立性
    assert daily_result[0].datetime != minute_result[0].datetime

    print("  ✓ PASS: 多数据源注入正确")


def test_4_multi_interval_independent_data():
    """测试 4: 多周期数据独立性"""
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer

    buf = MultiTimeframeCandleBuffer()

    # 日线：100根，价格从10开始上涨
    daily_bars = create_daily_bars(100)
    # 周线：20根，价格从20开始（不同于日线）
    weekly_bars = []
    start = datetime(2025, 1, 6, 15, 0, 0)
    price = 20.0
    for i in range(20):
        dt = start + timedelta(weeks=i)
        price *= 1.01
        weekly_bars.append(MockBar(
            datetime=dt,
            close_price=round(price, 2),
            open_price=round(price * 0.99, 2),
            high_price=round(price * 1.02, 2),
            low_price=round(price * 0.98, 2),
            symbol="TEST.SH",
        ))

    buf.inject("TEST.SH", Interval.DAILY, daily_bars)
    buf.inject("TEST.SH", Interval.WEEKLY, weekly_bars)

    # 获取数据
    daily_result = buf.get("TEST.SH", 10, Interval.DAILY)
    weekly_result = buf.get("TEST.SH", 10, Interval.WEEKLY)

    # 验证周线收盘价在20附近（不是10附近）
    assert weekly_result[-1].close_price > 15, \
        f"周线数据被日线污染: close={weekly_result[-1].close_price}"
    assert daily_result[-1].close_price < 15, \
        f"日线数据异常: close={daily_result[-1].close_price}"

    print("  ✓ PASS: 多周期数据独立性验证")


def test_5_as_of_time_with_different_intervals():
    """测试 5: 不同周期使用 As-of Time"""
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer

    buf = MultiTimeframeCandleBuffer()

    # 创建日线和分钟线（同一时间范围）
    base_date = datetime(2025, 3, 1)
    daily_bars = create_daily_bars(60, start_date=base_date.replace(hour=15))
    minute_bars = create_minute_bars(1000, start_date=base_date.replace(hour=9, minute=30))

    buf.inject("TEST.SH", Interval.DAILY, daily_bars)
    buf.inject("TEST.SH", Interval.MINUTE_5, minute_bars)

    # 以第30个交易日15:00为评估时间点
    eval_time = daily_bars[29].datetime

    # 日线：应该返回前30根
    daily_as_of = buf.get_bars_as_of("TEST.SH", 100, Interval.DAILY, eval_time)
    assert len(daily_as_of) == 30, f"日线As-of期望30，实际{len(daily_as_of)}"

    # 分钟线：应该返回 <= eval_time 的所有分钟线
    minute_as_of = buf.get_bars_as_of("TEST.SH", 5000, Interval.MINUTE_5, eval_time)
    for b in minute_as_of:
        assert b.datetime <= eval_time, \
            f"分钟线未来数据: {b.datetime} > {eval_time}"

    print("  ✓ PASS: 不同周期 As-of Time 正确")


def test_6_scan_engine_get_bars_as_of():
    """测试 6: ScanEngine._get_bars_as_of 集成"""
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.engine.scan_engine import ScanEngine

    # 构造 ScanEngine
    ce = ConditionEngine()
    se = ScanEngine(condition_engine=ce)

    # 设置多周期缓存
    buf = MultiTimeframeCandleBuffer()
    daily_bars = create_daily_bars(100)
    buf.inject("TEST.SH", Interval.DAILY, daily_bars)
    se.set_mtf_buffer(buf)

    # 使用 _get_bars_as_of
    eval_time = daily_bars[49].datetime
    result = se._get_bars_as_of("TEST.SH", 20, Interval.DAILY, eval_time)

    assert len(result) == 20, f"期望20根，实际{len(result)}根"
    assert all(b.datetime <= eval_time for b in result)

    print("  ✓ PASS: ScanEngine._get_bars_as_of 集成正确")


def test_7_backtest_data_alignment_simulation():
    """测试 7: 回测数据对齐模拟"""
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer

    buf = MultiTimeframeCandleBuffer()

    # 模拟回测场景：5分钟线执行，日线过滤
    daily_bars = create_daily_bars(60, datetime(2025, 1, 2, 15, 0, 0))
    minute_bars = create_minute_bars(2000, datetime(2025, 1, 2, 9, 30, 0))

    buf.inject("TEST.SH", Interval.DAILY, daily_bars)
    buf.inject("TEST.SH", Interval.MINUTE_5, minute_bars)

    # 模拟逐bar回测：在第500根分钟线时评估
    eval_time = minute_bars[499].datetime

    # 获取分钟线（执行周期）
    exec_bars = buf.get_bars_as_of("TEST.SH", 500, Interval.MINUTE_5, eval_time)
    # 获取日线（过滤周期）
    filter_bars = buf.get_bars_as_of("TEST.SH", 60, Interval.DAILY, eval_time)

    # 验证：分钟线数据量正确
    assert len(exec_bars) == 500, f"分钟线期望500，实际{len(exec_bars)}"
    # 验证：日线数据不超过评估时间
    for b in filter_bars:
        assert b.datetime <= eval_time, \
            f"日线未来数据: {b.datetime} > {eval_time}"
    # 验证：日线数据量合理（评估时间对应的交易天数）
    assert len(filter_bars) > 0, "日线数据为空"

    print("  ✓ PASS: 回测数据对齐模拟正确")


def test_8_get_cache_stats():
    """测试 8: 缓存统计"""
    from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer

    buf = MultiTimeframeCandleBuffer()
    stats = buf.get_cache_stats()

    assert "total_requests" in stats
    assert "cache_hits" in stats
    assert "hit_rate" in stats
    assert stats["hit_rate"] >= 0.0

    print("  ✓ PASS: 缓存统计接口正确")


# ─── 主入口 ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Phase 5 数据对齐和 As-of Time 机制测试")
    print("=" * 60)
    print()

    tests = [
        ("测试 1: get_bars_as_of 基本功能", test_1_get_bars_as_of_basic),
        ("测试 2: 无未来数据泄露", test_2_get_bars_as_of_no_future_leak),
        ("测试 3: 多数据源注入", test_3_set_base_bars_multi),
        ("测试 4: 多周期数据独立性", test_4_multi_interval_independent_data),
        ("测试 5: 不同周期 As-of Time", test_5_as_of_time_with_different_intervals),
        ("测试 6: ScanEngine._get_bars_as_of", test_6_scan_engine_get_bars_as_of),
        ("测试 7: 回测数据对齐模拟", test_7_backtest_data_alignment_simulation),
        ("测试 8: 缓存统计", test_8_get_cache_stats),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"[{name}]")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()

    print("=" * 60)
    if failed == 0:
        print(f"ALL PHASE 5 DATA ALIGNMENT TESTS PASSED ({passed}/{passed})")
    else:
        print(f"FAILED: {failed}/{passed + failed}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)