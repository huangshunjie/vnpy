"""
strategy_condition/templates/
策略模板包
"""
from .strong_pullback_strategy import (
    TEMPLATE_NAME,
    TEMPLATE_VERSION,
    build_buy_tree,
    build_sell_tree,
    build_score_weights,
    get_template_config,
)