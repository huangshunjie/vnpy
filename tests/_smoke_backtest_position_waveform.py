"""
冒烟测试：Monitor 面板"回测持仓段"辅助波形算法。

验证 ConditionWaveformView._compute_backtest_position_waveform() 能否
根据 buy_indices / sell_indices 正确标出"处于持仓段"的 K 线区间。
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np


@dataclass
class FakeSnapshot:
    """轻量替代 ConditionSnapshot：算法只依赖 bar_index 字段。"""
    bar_index: int


def _make_snapshots(n: int, start: int = 30):
    """生成 bar_index 从 start 到 start+n-1 的连续快照序列。"""
    return [FakeSnapshot(bar_index=start + i) for i in range(n)]


def _run_algo(snapshots, buy_indices, sell_indices):
    """
    直接复用 ConditionWaveformView 里的纯函数逻辑，避免拉起 Qt。
    我们把 self._buy_indices / self._sell_indices 用一个鸭子对象承接。
    """
    from vnpy.strategy_condition.ui.condition_monitor_widget import (
        ConditionWaveformView,
    )

    # 用类的方法但不实例化整个 QWidget：直接 bind 一个 mock
    class _Mock:
        _buy_indices = buy_indices
        _sell_indices = sell_indices

    mock = _Mock()
    return ConditionWaveformView._compute_backtest_position_waveform(
        mock, snapshots
    )


def test_single_position_range():
    """单个 buy → sell 区间：中间几根应为 1，两端外为 0。"""
    # bar_index 范围 30..79
    snaps = _make_snapshots(50, start=30)
    y = _run_algo(snaps, buy_indices=[40], sell_indices=[45])

    # [40, 45] 含端点应为 1 = 6 个 bar
    assert int(y.sum()) == 6, f"期望 6 个高电平，实际 {int(y.sum())}"

    # 40..45 位置分别对应 snapshot index 10..15
    for i in range(10, 16):
        assert y[i] == 1.0, f"snapshot[{i}] (bar_index={snaps[i].bar_index}) 应为持仓"
    # 边界外
    assert y[9] == 0.0, "buy 前一根应为空仓"
    assert y[16] == 0.0, "sell 后一根应为空仓"

    print("[PASS] test_single_position_range")


def test_multiple_ranges():
    """多次 buy/sell 交替：只标记合法配对区间。"""
    snaps = _make_snapshots(100, start=0)
    # 3 次买卖
    y = _run_algo(snaps,
                  buy_indices=[10, 30, 60],
                  sell_indices=[15, 40, 75])

    expected_positions = set()
    for b, s in [(10, 15), (30, 40), (60, 75)]:
        for k in range(b, s + 1):
            expected_positions.add(k)

    actual_positions = {snaps[i].bar_index for i in range(len(snaps)) if y[i] > 0.5}
    assert actual_positions == expected_positions, (
        f"持仓段不匹配:\n  期望={sorted(expected_positions)}\n"
        f"  实际={sorted(actual_positions)}"
    )

    print("[PASS] test_multiple_ranges")


def test_unmatched_buy_extends_to_end():
    """有 buy 但没有对应 sell：应持仓至序列末尾。"""
    snaps = _make_snapshots(40, start=0)  # bar_index 0..39
    y = _run_algo(snaps, buy_indices=[20], sell_indices=[])

    # 20..39 都应为 1（20 根）
    assert int(y.sum()) == 20, f"期望 20 个高电平（持仓至末尾），实际 {int(y.sum())}"
    for i in range(20):
        assert y[i] == 0.0, f"snapshot[{i}] 应为空仓（在 buy 之前）"
    for i in range(20, 40):
        assert y[i] == 1.0, f"snapshot[{i}] 应为持仓（buy 之后无 sell）"

    print("[PASS] test_unmatched_buy_extends_to_end")


def test_no_signals():
    """无 buy_indices 时全为 0。"""
    snaps = _make_snapshots(30, start=0)
    y = _run_algo(snaps, buy_indices=[], sell_indices=[])

    assert int(y.sum()) == 0, "无信号时应全为空仓"
    print("[PASS] test_no_signals")


def test_illegal_sell_before_buy_is_dropped():
    """sell 早于 buy 时应被忽略，用下一个合法 sell 配对。"""
    snaps = _make_snapshots(50, start=0)
    # sell_indices 中第一个 5 早于 buy 10，应被丢弃；
    # 剩下 20 才是合法 sell
    y = _run_algo(snaps, buy_indices=[10], sell_indices=[5, 20])

    # 期望持仓段 = [10, 20]（含端点）= 11 根
    assert int(y.sum()) == 11, (
        f"非法 sell 应被忽略后配对下一个合法 sell，"
        f"期望 11 根持仓，实际 {int(y.sum())}"
    )
    print("[PASS] test_illegal_sell_before_buy_is_dropped")


if __name__ == "__main__":
    test_single_position_range()
    test_multiple_ranges()
    test_unmatched_buy_extends_to_end()
    test_no_signals()
    test_illegal_sell_before_buy_is_dropped()
    print("\nAll smoke tests passed.")