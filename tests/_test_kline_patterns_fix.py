"""
测试 K线形态指标修复后的功能
验证 KLINE_YANG、KLINE_YIN 等指标现在可以正确评估
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vnpy.strategy_condition.constant import ConditionIndicator
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine


def make_bar(dt, o, h, l, c, v):
    """Create a mock bar with open/high/low/close/volume attributes."""
    return SimpleNamespace(
        datetime=dt, open=o, high=h, low=l, close=c, volume=v
    )


def test_kline_yang():
    print("\n=== KLINE_YANG ===")
    bars = [make_bar(datetime(2024,1,i+1), 100+i, 105+i, 95+i, 102+i, 1e6) for i in range(5)]
    bars.append(make_bar(datetime(2024,1,6), 104, 107, 103, 106, 1.2e6))
    cond = Condition(indicator=ConditionIndicator.KLINE_YANG, params={})
    engine = ConditionEngine()
    passed, score = engine.eval_condition(cond, "TEST", bars)
    print(f"  passed={passed}, score={score:.2f}")
    assert passed == True, f"Expected True, got {passed}"
    print("  OK")


def test_kline_yin():
    print("\n=== KLINE_YIN ===")
    bars = [make_bar(datetime(2024,1,i+1), 100+i, 105+i, 95+i, 102+i, 1e6) for i in range(5)]
    bars.append(make_bar(datetime(2024,1,6), 106, 107, 102, 103, 1.2e6))
    cond = Condition(indicator=ConditionIndicator.KLINE_YIN, params={})
    engine = ConditionEngine()
    passed, score = engine.eval_condition(cond, "TEST", bars)
    print(f"  passed={passed}, score={score:.2f}")
    assert passed == True, f"Expected True, got {passed}"
    print("  OK")


def test_kline_doji():
    print("\n=== KLINE_DOJI ===")
    bars = [make_bar(datetime(2024,1,i+1), 100+i, 105+i, 95+i, 102+i, 1e6) for i in range(5)]
    bars.append(make_bar(datetime(2024,1,6), 100, 105, 95, 100.2, 1.2e6))
    cond = Condition(indicator=ConditionIndicator.KLINE_DOJI, params={"max_body_ratio": 0.1})
    engine = ConditionEngine()
    passed, score = engine.eval_condition(cond, "TEST", bars)
    print(f"  passed={passed}, score={score:.2f}")
    assert passed == True, f"Expected True, got {passed}"
    print("  OK")


def test_kline_big_yang():
    print("\n=== KLINE_BIG_YANG ===")
    bars = [make_bar(datetime(2024,1,i+1), 100, 102, 98, 101, 1e6) for i in range(5)]
    bars.append(make_bar(datetime(2024,1,6), 100, 111, 99, 110, 1.5e6))
    cond = Condition(indicator=ConditionIndicator.KLINE_BIG_YANG, params={"min_pct": 5.0})
    engine = ConditionEngine()
    passed, score = engine.eval_condition(cond, "TEST", bars)
    print(f"  passed={passed}, score={score:.2f}")
    assert passed == True, f"Expected True, got {passed}"
    print("  OK")


def test_negative_yang():
    """Ensure a yin bar does NOT pass KLINE_YANG."""
    print("\n=== KLINE_YANG (negative case) ===")
    bars = [make_bar(datetime(2024,1,i+1), 100, 105, 95, 99, 1e6) for i in range(5)]
    bars.append(make_bar(datetime(2024,1,6), 106, 107, 102, 103, 1.2e6))
    cond = Condition(indicator=ConditionIndicator.KLINE_YANG, params={})
    engine = ConditionEngine()
    passed, score = engine.eval_condition(cond, "TEST", bars)
    print(f"  passed={passed}, score={score:.2f}")
    assert passed == False, f"Expected False for yin bar, got {passed}"
    print("  OK")


if __name__ == "__main__":
    print("=" * 50)
    print("K-line Pattern Dispatch Fix - Verification")
    print("=" * 50)
    try:
        test_kline_yang()
        test_kline_yin()
        test_kline_doji()
        test_kline_big_yang()
        test_negative_yang()
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED")
        print("=" * 50)
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)