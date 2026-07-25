"""
策略模板：强势股缩量回调低吸策略
自动生成条件树，支持 JSON 序列化保存和版本管理
"""
from __future__ import annotations
from typing import Dict, Any

from ..core.condition import (
    Condition,
    cond_ma_alignment,
    cond_stop_loss,
    cond_trailing_stop,
    cond_ma_break_down,
)
from ..core.condition_advanced import (
    cond_trend_strength,
    cond_price_above_ma,
    cond_strength_limit_up_count,
    cond_strength_returnn,
    cond_volume_layer,
    cond_volume_yin_filter,
    cond_pullback_to_ma10,
    cond_shrink_pullback,
    cond_kline_yin,
    cond_kline_shrink_yin,
    cond_dev_ma10_ma20,
)
from ..core.condition_tree import ConditionNode, NodeOp


TEMPLATE_NAME = "强势股缩量回调低吸策略"
TEMPLATE_VERSION = "1.0.0"
TEMPLATE_DESCRIPTION = """
核心逻辑：
1. 趋势确认：MA5>MA10>MA20>MA30多头排列，价格站上MA20
2. 强势确认：20日内存在涨停或20日涨幅>20%
3. 量能确认：上涨阶段放量，调整阶段缩量
4. 回调买点：价格回踩MA10附近（距离<2%），缩量阴线
5. 偏离过滤：MA10与MA20距离不能过大
6. 卖出规则：止损8%、追踪止盈15%回撤10%、跌破MA20
"""


def build_buy_tree() -> ConditionNode:
    """构建买入条件树"""
    # 根节点 AND
    root = ConditionNode(op=NodeOp.AND, label="买入条件(全部满足)")

    # 1. 趋势组
    trend_group = ConditionNode(op=NodeOp.AND, label="趋势确认")
    trend_group.add_child(ConditionNode.leaf(
        cond_ma_alignment(periods=[5, 10, 20, 30], max_gap_pct=0.0)))
    trend_group.add_child(ConditionNode.leaf(
        cond_price_above_ma(ma_period=20)))
    trend_group.add_child(ConditionNode.leaf(
        cond_trend_strength(periods=[5, 10, 20, 30])))
    root.add_child(trend_group)

    # 2. 强势组（OR：任一满足）
    strength_group = ConditionNode(op=NodeOp.OR, label="强势确认(满足其一)")
    strength_group.add_child(ConditionNode.leaf(
        cond_strength_limit_up_count(n=20, min_count=1)))
    strength_group.add_child(ConditionNode.leaf(
        cond_strength_returnn(n=20, min_return=20.0)))
    root.add_child(strength_group)

    # 3. 量能组
    volume_group = ConditionNode(op=NodeOp.AND, label="量能确认")
    volume_group.add_child(ConditionNode.leaf(
        cond_volume_layer(up_window=10, dn_window=5, max_ratio=0.6)))
    volume_group.add_child(ConditionNode.leaf(
        cond_volume_yin_filter()))
    root.add_child(volume_group)

    # 4. 回调组
    pullback_group = ConditionNode(op=NodeOp.AND, label="回调买点")
    pullback_group.add_child(ConditionNode.leaf(
        cond_pullback_to_ma10(tol_pct=2.0)))
    pullback_group.add_child(ConditionNode.leaf(
        cond_shrink_pullback(pullback_days=3, vol_period=10, max_vol_ratio=0.7)))
    root.add_child(pullback_group)

    # 5. K线组
    kline_group = ConditionNode(op=NodeOp.AND, label="K线形态")
    kline_group.add_child(ConditionNode.leaf(cond_kline_yin()))
    kline_group.add_child(ConditionNode.leaf(cond_kline_shrink_yin(vol_period=5)))
    root.add_child(kline_group)

    # 6. 偏离过滤
    dev_group = ConditionNode(op=NodeOp.AND, label="偏离过滤")
    dev_group.add_child(ConditionNode.leaf(
        cond_dev_ma10_ma20(max_distance_pct=5.0)))
    root.add_child(dev_group)

    return root


def build_sell_tree() -> ConditionNode:
    """构建卖出条件树"""
    # 卖出用 OR（任一触发即卖出）
    root = ConditionNode(op=NodeOp.OR, label="卖出条件(任一触发)")
    root.add_child(ConditionNode.leaf(cond_stop_loss(pct=8.0)))
    root.add_child(ConditionNode.leaf(
        cond_trailing_stop(take_profit=15.0, trail_drawdown=10.0)))
    root.add_child(ConditionNode.leaf(cond_ma_break_down(ma_period=20)))
    return root


def build_score_weights() -> Dict[str, float]:
    """评分权重配置"""
    return {
        "trend": 25.0,
        "strength": 20.0,
        "volume": 20.0,
        "pullback": 20.0,
        "kline": 10.0,
        "market": 5.0,
    }


def get_template_config() -> Dict[str, Any]:
    """获取策略模板完整配置（可JSON序列化保存）"""
    buy_tree = build_buy_tree()
    sell_tree = build_sell_tree()
    return {
        "name": TEMPLATE_NAME,
        "version": TEMPLATE_VERSION,
        "description": TEMPLATE_DESCRIPTION,
        "buy_tree": buy_tree.to_dict(),
        "sell_tree": sell_tree.to_dict(),
        "score_weights": build_score_weights(),
        "score_threshold": 80.0,
        "parameters": {
            "ma_periods": [5, 10, 20, 30],
            "pullback_ma": 10,
            "pullback_tolerance_pct": 2.0,
            "strength_lookback": 20,
            "strength_min_return": 20.0,
            "volume_shrink_ratio": 0.6,
            "stop_loss_pct": 8.0,
            "trailing_take_profit": 15.0,
            "trailing_drawdown": 10.0,
        }
    }