"""
冒烟测试：Sell Signal Lifecycle 四层诊断

验证：
  1. 无持仓时：条件可能触发但不产生 Signal
  2. 有持仓 + T+1保护：Signal 被 Decision 拒绝
  3. 有持仓 + 过保护期 + 条件触发：Signal 被 Approved
  4. 序列化 to_dict 正常
"""
import sys
sys.path.insert(0, ".")

from datetime import datetime, timedelta
from vnpy.strategy_condition.monitor.sell_signal_lifecycle import (
    ConditionLayerResult,
    DecisionCheck,
    DecisionLayerResult,
    ExecutionLayerResult,
    SellSignalLifecycle,
    SignalLayerResult,
)
from vnpy.strategy_condition.monitor.condition_snapshot import ConditionDetail
from vnpy.strategy_condition.constant import (
    DecisionResult,
    RejectReason,
    SellLifecycleStage,
)


def test_lifecycle_basic():
    """测试基本数据结构创建与序列化"""
    now = datetime(2026, 7, 18, 10, 0, 0)

    # 构建一个完整的 Lifecycle
    lc = SellSignalLifecycle(
        symbol="601211.SH",
        bar_index=100,
        dt=now,
        has_position=True,
        entry_price=18.0,
        peak_price=19.5,
        hold_bars=5,
        condition=ConditionLayerResult(
            condition_name="追踪止盈",
            indicator="TRAILING_STOP",
            triggered=True,
            score=0.85,
            trigger_time=now,
            context={"entry_price": 18.0, "peak_price": 19.5, "current_price": 18.2},
        ),
        signal=SignalLayerResult(
            signal_created=True,
            signal_source="追踪止盈",
            signal_time=now,
        ),
        decision=DecisionLayerResult(
            result=DecisionResult.REJECTED,
            reject_reason=RejectReason.T1_LOCK,
            reject_description="T+1当日锁定，无法卖出",
            checks=[
                DecisionCheck("T+1保护", False, "买入当日不可卖出"),
                DecisionCheck("买卖冲突", True, "无冲突"),
                DecisionCheck("持仓确认", True, "持仓中，入场价18.00"),
            ],
        ),
        execution=ExecutionLayerResult(executed=False),
    )

    # 验证属性
    assert lc.stage == SellLifecycleStage.DECISION
    assert lc.is_rejected is True
    assert lc.is_executed is False
    assert "被拒绝" in lc.status_summary or "锁定" in lc.status_summary

    # 序列化
    d = lc.to_dict()
    assert d["symbol"] == "601211.SH"
    assert d["stage"] == "DECISION"
    assert d["condition"]["triggered"] is True
    assert d["signal"]["signal_created"] is True
    assert d["decision"]["result"] == "REJECTED"
    assert d["decision"]["reject_reason"] == "T1_LOCK"
    assert len(d["decision"]["checks"]) == 3
    assert d["execution"]["executed"] is False

    print("✅ test_lifecycle_basic PASSED")


def test_lifecycle_no_position():
    """无持仓时：条件触发但不产生信号"""
    now = datetime(2026, 7, 18, 10, 0, 0)

    lc = SellSignalLifecycle(
        symbol="601211.SH",
        bar_index=50,
        dt=now,
        has_position=False,
        condition=ConditionLayerResult(
            condition_name="跌破MA20",
            indicator="MA_BREAK_DOWN",
            triggered=True,
            score=0.9,
            trigger_time=now,
        ),
        signal=SignalLayerResult(signal_created=False),
        decision=DecisionLayerResult(),
        execution=ExecutionLayerResult(),
    )

    assert lc.stage == SellLifecycleStage.CONDITION
    assert lc.signal.signal_created is False
    assert "无持仓" in lc.status_summary

    d = lc.to_dict()
    assert d["stage"] == "CONDITION"
    assert d["signal"]["signal_created"] is False

    print("✅ test_lifecycle_no_position PASSED")


def test_lifecycle_approved():
    """持仓 + 过保护期 + 条件触发 = Approved"""
    now = datetime(2026, 7, 19, 10, 0, 0)

    lc = SellSignalLifecycle(
        symbol="601211.SH",
        bar_index=105,
        dt=now,
        has_position=True,
        entry_price=18.0,
        peak_price=19.5,
        hold_bars=10,
        condition=ConditionLayerResult(
            condition_name="追踪止盈",
            indicator="TRAILING_STOP",
            triggered=True,
            score=0.85,
            trigger_time=now,
        ),
        signal=SignalLayerResult(
            signal_created=True,
            signal_source="追踪止盈",
            signal_time=now,
        ),
        decision=DecisionLayerResult(
            result=DecisionResult.APPROVED,
            reject_reason=RejectReason.NONE,
            checks=[
                DecisionCheck("T+1保护", True, "已过T+1保护期"),
                DecisionCheck("买卖冲突", True, "无冲突"),
                DecisionCheck("持仓确认", True, "持仓中，入场价18.00"),
            ],
        ),
        execution=ExecutionLayerResult(executed=False),
    )

    assert lc.stage == SellLifecycleStage.DECISION
    assert lc.is_rejected is False
    assert lc.decision.result == DecisionResult.APPROVED
    assert "批准" in lc.status_summary or "等待执行" in lc.status_summary

    print("✅ test_lifecycle_approved PASSED")


def test_lifecycle_executed():
    """Execution 层完成"""
    now = datetime(2026, 7, 19, 10, 0, 0)

    lc = SellSignalLifecycle(
        symbol="601211.SH",
        bar_index=105,
        dt=now,
        has_position=True,
        entry_price=18.0,
        peak_price=19.5,
        hold_bars=10,
        condition=ConditionLayerResult(
            condition_name="追踪止盈",
            indicator="TRAILING_STOP",
            triggered=True,
            score=0.85,
            trigger_time=now,
        ),
        signal=SignalLayerResult(
            signal_created=True,
            signal_source="追踪止盈",
            signal_time=now,
        ),
        decision=DecisionLayerResult(
            result=DecisionResult.APPROVED,
            reject_reason=RejectReason.NONE,
        ),
        execution=ExecutionLayerResult(
            executed=True,
            execution_time=now,
            execution_price=18.2,
            volume=100,
            exit_reason="trailing_stop",
        ),
    )

    assert lc.stage == SellLifecycleStage.EXECUTION
    assert lc.is_executed is True
    assert "18.20" in lc.status_summary

    d = lc.to_dict()
    assert d["stage"] == "EXECUTION"
    assert d["execution"]["executed"] is True
    assert d["execution"]["execution_price"] == 18.2

    print("✅ test_lifecycle_executed PASSED")


def test_condition_snapshot_with_lifecycles():
    """验证 ConditionSnapshot 包含 lifecycle 字段"""
    from vnpy.strategy_condition.monitor.condition_snapshot import ConditionSnapshot

    now = datetime(2026, 7, 18, 10, 0, 0)

    lc = SellSignalLifecycle(
        symbol="601211.SH",
        bar_index=100,
        dt=now,
        has_position=True,
        entry_price=18.0,
        condition=ConditionLayerResult("追踪止盈", "TRAILING_STOP", True, 0.8),
        signal=SignalLayerResult(True, "追踪止盈", now),
        decision=DecisionLayerResult(result=DecisionResult.REJECTED,
                                     reject_reason=RejectReason.T1_LOCK,
                                     reject_description="T+1锁定"),
    )

    snap = ConditionSnapshot(
        dt=now,
        symbol="601211.SH",
        price=18.2,
        bar_index=100,
        sell_lifecycles=[lc],
        sell_signal_created=True,
        sell_decision_result="REJECTED",
        sell_reject_reason="T+1锁定",
    )

    d = snap.to_dict()
    assert len(d["sell_lifecycles"]) == 1
    assert d["sell_signal_created"] is True
    assert d["sell_decision_result"] == "REJECTED"
    assert d["sell_reject_reason"] == "T+1锁定"

    print("✅ test_condition_snapshot_with_lifecycles PASSED")


if __name__ == "__main__":
    test_lifecycle_basic()
    test_lifecycle_no_position()
    test_lifecycle_approved()
    test_lifecycle_executed()
    test_condition_snapshot_with_lifecycles()
    print("\n🎉 All Sell Signal Lifecycle tests PASSED!")