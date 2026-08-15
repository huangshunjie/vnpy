"""
strategy_condition/templates/builtin.py
三个内置策略模板：趋势回踩 / 突破 / 强势股
"""
from __future__ import annotations

from ..core.condition import (
    cond_weekly_ma_slope, cond_ma_slope, cond_ma_alignment,
    cond_pullback_from_high, cond_pullback_to_ma,
    cond_macd_golden, cond_macd_death_sell,
    cond_volume_price_up, cond_volume_ratio,
    cond_new_high_n, cond_limit_up_count, cond_kline_strength,
    cond_rsi_range, cond_atr_ratio,
    cond_trailing_stop, cond_stop_loss, cond_max_hold_days, cond_ma_break_down,
)
from ..core.condition_tree import ConditionNode
from ..core.strategy import Strategy, StrategyMeta, StrategyParams


def _layered_buy(filter_node: ConditionNode, trigger_node: ConditionNode) -> ConditionNode:
    return ConditionNode.and_node(filter_node, trigger_node, label="买入条件")


def _layered_sell(risk_node: ConditionNode, exit_node: ConditionNode) -> ConditionNode:
    return ConditionNode.or_node(risk_node, exit_node, label="卖出条件")


def template_trend_pullback() -> Strategy:
    """
    趋势回踩策略
    BUY:  13周均线向上 AND 从高点回踩 AND MACD金叉 AND 放量
    SELL: 追踪止盈 OR 固定止损 OR 最大持仓
    """
    buy = ConditionNode.and_node(
        ConditionNode.and_node(
            ConditionNode.leaf(cond_weekly_ma_slope(13, 5, 0.0,  weight=1.5)),
            ConditionNode.leaf(cond_pullback_from_high(20, -10.0, -2.0, weight=1.2)),
            label="日线过滤层",
        ),
        ConditionNode.or_node(
            ConditionNode.leaf(cond_macd_golden(weight=1.0)),
            ConditionNode.leaf(cond_volume_price_up(20, 1.5, 1.0, weight=1.0)),
            label="分钟触发层",
        ),
        label="趋势回踩买入",
    )
    sell = ConditionNode.or_node(
        ConditionNode.leaf(cond_trailing_stop(15.0, 10.0)),
        ConditionNode.leaf(cond_stop_loss(8.0)),
        ConditionNode.leaf(cond_max_hold_days(60)),
        label="卖出条件",
    )
    return Strategy(
        meta=Strategy.__new__(Strategy).meta if False else StrategyMeta(
            name="趋势回踩策略",
            version="1.0.0",
            description="13周均线向上 + 回踩 + MACD金叉 + 放量，追踪止盈",
            tags=["趋势", "回踩", "MACD"],
        ),
        buy_tree=  buy,
        sell_tree= sell,
        params=    StrategyParams(
            max_hold_days=60, stop_loss_pct=8.0,
            take_profit_pct=15.0, trail_drawdown=10.0,
        ),
    )


def template_breakout() -> Strategy:
    """
    突破策略
    BUY:  20日新高 AND 成交量放大 AND MA多头排列
    SELL: 止损 OR 跌破MA20 OR 最大持仓
    """
    buy = ConditionNode.and_node(
        ConditionNode.and_node(
            ConditionNode.leaf(cond_new_high_n(20, weight=1.5)),
            ConditionNode.leaf(cond_ma_alignment([5, 10, 20, 60], weight=1.0)),
            label="日线过滤层",
        ),
        ConditionNode.or_node(
            ConditionNode.leaf(cond_volume_ratio(20, 1.8, weight=1.2)),
            label="分钟触发层",
        ),
        label="突破买入",
    )
    sell = ConditionNode.or_node(
        ConditionNode.leaf(cond_stop_loss(6.0)),
        ConditionNode.leaf(cond_ma_break_down(20)),
        ConditionNode.leaf(cond_max_hold_days(30)),
        label="卖出条件",
    )
    return Strategy(
        meta=StrategyMeta(
            name="突破策略",
            version="1.0.0",
            description="20日新高突破 + 放量 + 均线多头，快进快出",
            tags=["突破", "新高", "趋势"],
        ),
        buy_tree=  buy,
        sell_tree= sell,
        params=    StrategyParams(
            max_hold_days=30, stop_loss_pct=6.0,
            take_profit_pct=20.0, trail_drawdown=8.0,
        ),
    )


def template_strong_stock() -> Strategy:
    """
    强势股策略
    BUY:  涨停次数 >= 2 AND K线强度 AND MA斜率向上 AND RSI健康
    SELL: 追踪止盈 OR 止损 OR MACD死叉 OR 最大持仓
    """
    buy = ConditionNode.and_node(
        ConditionNode.and_node(
            ConditionNode.leaf(cond_limit_up_count(20, 2, weight=2.0)),
            ConditionNode.leaf(cond_kline_strength(0.5, weight=1.5)),
            label="日线过滤层",
        ),
        ConditionNode.or_node(
            ConditionNode.leaf(cond_ma_slope(20, 10, 0.1, weight=1.0)),
            ConditionNode.leaf(cond_rsi_range(14, 40.0, 80.0, weight=0.8)),
            label="分钟触发层",
        ),
        label="强势股买入",
    )
    sell = ConditionNode.or_node(
        ConditionNode.leaf(cond_trailing_stop(20.0, 12.0)),
        ConditionNode.leaf(cond_stop_loss(10.0)),
        ConditionNode.leaf(cond_macd_death_sell()),
        ConditionNode.leaf(cond_max_hold_days(45)),
        label="卖出条件",
    )
    return Strategy(
        meta=StrategyMeta(
            name="强势股策略",
            version="1.0.0",
            description="涨停 + K线强度 + 趋势，捕捉热门强势股",
            tags=["强势", "涨停", "动量"],
        ),
        buy_tree=  buy,
        sell_tree= sell,
        params=    StrategyParams(
            max_hold_days=45, stop_loss_pct=10.0,
            take_profit_pct=20.0, trail_drawdown=12.0,
        ),
    )


# 所有内置模板列表
BUILTIN_TEMPLATES = [
    template_trend_pullback,
    template_breakout,
    template_strong_stock,
]


def get_all_templates() -> list:
    """返回所有内置策略模板实例列表"""
    return [fn() for fn in BUILTIN_TEMPLATES]


def get_template(name: str):
    """按名称获取内置模板"""
    for fn in BUILTIN_TEMPLATES:
        s = fn()
        if s.name == name:
            return s
    return None
