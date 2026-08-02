"""
冒烟测试：验证卖出条件参数优先级（节点参数优先，StrategyParams 兜底）

背景：
- 修复前 eval_exit 中的阈值取自 StrategyParams（若非 None），
  导致用户在条件编辑器里调节的节点参数完全不生效。
- 修复后：节点自身 params 优先，只有当节点没有相应键时才回退到
  StrategyParams。

本测试覆盖 4 个卖出指标：
  STOP_LOSS / TAKE_PROFIT / TRAILING_STOP / MAX_HOLD_DAYS
"""
from __future__ import annotations

import sys
import os

# 让脚本可从任意目录运行
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.strategy import StrategyParams
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine


def _make_cond(indicator: ConditionIndicator, params: dict) -> Condition:
    return Condition(
        category=ConditionCategory.EXIT,
        indicator=indicator,
        params=params,
        weight=1.0,
        label=indicator.value,
    )


def test_stop_loss_priority():
    """STOP_LOSS：节点 pct=5 优先于 StrategyParams.stop_loss_pct=8"""
    ce = ConditionEngine()
    sp = StrategyParams(stop_loss_pct=8.0)

    # 节点自定义止损 5%，实际亏损 6%
    cond = _make_cond(ConditionIndicator.STOP_LOSS, {"pct": 5.0})
    entry = 100.0
    cur = 94.0        # -6%
    ok, _ = ce.eval_exit(cond, entry, cur, entry, 0, [], sp)
    assert ok, f"节点 pct=5 应触发（实际亏损 6%），但未触发"

    # 换一个不会触发节点阈值但会触发全局阈值的场景
    # 亏损 7%：节点 5% 应触发，若被 sp 覆盖为 8% 就不会触发
    cur = 93.0        # -7%
    ok, _ = ce.eval_exit(cond, entry, cur, entry, 0, [], sp)
    assert ok, "节点 pct=5 优先，7% 亏损应触发；若被全局 8% 覆盖则错误"

    # 边界：节点未提供 pct，回退到全局 8%
    cond2 = _make_cond(ConditionIndicator.STOP_LOSS, {})
    cur = 93.0        # -7% < 8% 全局
    ok, _ = ce.eval_exit(cond2, entry, cur, entry, 0, [], sp)
    assert not ok, "节点无 pct 时应回退到全局 8%，7% 不应触发"

    cur = 91.0        # -9% >= 8% 全局
    ok, _ = ce.eval_exit(cond2, entry, cur, entry, 0, [], sp)
    assert ok, "节点无 pct 时应回退到全局 8%，9% 应触发"

    print("[PASS] test_stop_loss_priority")


def test_take_profit_priority():
    """TAKE_PROFIT：节点 pct=10 优先于 StrategyParams.take_profit_pct=15"""
    ce = ConditionEngine()
    sp = StrategyParams(take_profit_pct=15.0)

    cond = _make_cond(ConditionIndicator.TAKE_PROFIT, {"pct": 10.0})
    entry = 100.0
    cur = 112.0       # +12%：节点 10% 应触发；若被全局 15% 覆盖则不触发
    ok, _ = ce.eval_exit(cond, entry, cur, entry, 0, [], sp)
    assert ok, "节点 pct=10 优先，12% 盈利应触发"

    # 节点未提供 pct，回退到 15%
    cond2 = _make_cond(ConditionIndicator.TAKE_PROFIT, {})
    cur = 112.0       # +12% < 15%
    ok, _ = ce.eval_exit(cond2, entry, cur, entry, 0, [], sp)
    assert not ok, "节点无 pct 时应回退到全局 15%，12% 不应触发"

    print("[PASS] test_take_profit_priority")


def test_trailing_stop_priority():
    """TRAILING_STOP：节点 take_profit/trail_drawdown 优先"""
    ce = ConditionEngine()
    sp = StrategyParams(take_profit_pct=15.0, trail_drawdown=10.0)

    # 节点 tp=8, trail=3
    cond = _make_cond(
        ConditionIndicator.TRAILING_STOP,
        {"take_profit": 8.0, "trail_drawdown": 3.0},
    )
    entry = 100.0
    peak = 112.0      # 最大到过 +12%（>8% 门槛激活）
    cur = 108.0       # 从峰值回撤 (112-108)/112 ≈ 3.57%
    ok, _ = ce.eval_exit(cond, entry, cur, peak, 0, [], sp)
    assert ok, "节点 trail_drawdown=3% 应触发（实际回撤 3.57%）"

    # 若被全局 10% 覆盖：3.57% 达不到 10%，不会触发
    # 上面 ok=True 已经反证被覆盖 → 修复正确

    # 反向验证：改用全局兜底（节点没设置这两个键）
    # 注意：TRAILING_STOP 会先检查 ret >= take_profit_pct 才启动追踪
    cond2 = _make_cond(ConditionIndicator.TRAILING_STOP, {})
    peak = 130.0      # 峰值 +30%
    cur = 118.0       # ret=18% >= 全局15%(启动)；回撤 (130-118)/130=9.23% < 10%
    ok, _ = ce.eval_exit(cond2, entry, cur, peak, 0, [], sp)
    assert not ok, "节点无参数时回退全局 10%，9.23% 不应触发"

    cur = 116.0       # ret=16% >= 15%；回撤 (130-116)/130=10.77% >= 10%
    ok, _ = ce.eval_exit(cond2, entry, cur, peak, 0, [], sp)
    assert ok, "节点无参数时回退全局 10%，10.77% 应触发"

    print("[PASS] test_trailing_stop_priority")


def test_max_hold_days_priority():
    """MAX_HOLD_DAYS：节点 days=5 优先于 StrategyParams.max_hold_days=60"""
    ce = ConditionEngine()
    sp = StrategyParams(max_hold_days=60)

    cond = _make_cond(ConditionIndicator.MAX_HOLD_DAYS, {"days": 5})
    entry = 100.0
    cur = 100.0

    ok, _ = ce.eval_exit(cond, entry, cur, entry, 4, [], sp)
    assert not ok, "持仓 4 < 节点 5，不应触发"

    ok, _ = ce.eval_exit(cond, entry, cur, entry, 5, [], sp)
    assert ok, "持仓 5 >= 节点 5，应触发（若被全局 60 覆盖则错误）"

    # 节点无 days，回退到 60
    cond2 = _make_cond(ConditionIndicator.MAX_HOLD_DAYS, {})
    ok, _ = ce.eval_exit(cond2, entry, cur, entry, 30, [], sp)
    assert not ok, "节点无 days 时回退全局 60，30 不应触发"
    ok, _ = ce.eval_exit(cond2, entry, cur, entry, 60, [], sp)
    assert ok, "节点无 days 时回退全局 60，60 应触发"

    print("[PASS] test_max_hold_days_priority")


if __name__ == "__main__":
    test_stop_loss_priority()
    test_take_profit_priority()
    test_trailing_stop_priority()
    test_max_hold_days_priority()
    print("\nAll smoke tests passed.")