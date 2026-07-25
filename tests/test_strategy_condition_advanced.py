"""
测试 Strategy Condition Engine 升级模块
验证所有新增指标和条件工厂函数的正确性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_constant_enums():
    """测试新增枚举值"""
    from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator

    # 新增分类
    assert ConditionCategory.STRENGTH.value == "strength"
    assert ConditionCategory.DEVIATION.value == "deviation"
    assert ConditionCategory.MARKET.value == "market"
    assert ConditionCategory.SCORE.value == "score"

    # 新增指标（枚举值是大写字符串）
    assert ConditionIndicator.STRENGTH_RETURN_N.value == "STRENGTH_RETURN_N"
    assert ConditionIndicator.DEV_MA10.value == "DEV_MA10"
    assert ConditionIndicator.MARKET_INDEX_TREND.value == "MARKET_INDEX_TREND"
    assert ConditionIndicator.SCORE_NODE.value == "SCORE_NODE"
    assert ConditionIndicator.KLINE_YIN.value == "KLINE_YIN"
    assert ConditionIndicator.VOLUME_LAYER.value == "VOLUME_LAYER"
    assert ConditionIndicator.PULLBACK_TO_MA10.value == "PULLBACK_TO_MA10"
    assert ConditionIndicator.TREND_STRENGTH.value == "TREND_STRENGTH"
    print("  [PASS] constant enums")


def test_strength_indicators():
    """测试强势股指标"""
    from vnpy.strategy_condition.indicators.strength import (
        check_strength_return_n,
        check_strength_limit_up_count,
        check_strength_big_yang_count,
        check_strength_vol_break,
        check_strength_score,
    )
    closes = [float(x) for x in range(100, 130)]  # 30天上涨
    opens = [c - 0.5 for c in closes]
    highs = [c + 2.0 for c in closes]
    volumes = [1000000.0] * 30

    # check_strength_return_n(closes, n, min_return)
    passed, score = check_strength_return_n(closes, n=20, min_return=10.0)
    assert passed, "N日涨幅应通过"

    # check_strength_limit_up_count(closes, opens, n, min_count)
    passed, _ = check_strength_limit_up_count(closes, opens, n=20, min_count=1)
    # 此数据无涨停，应不通过
    assert not passed

    # check_strength_big_yang_count(closes, opens, n, min_count, min_pct)
    passed, _ = check_strength_big_yang_count(closes, opens, n=20, min_count=1, min_pct=2.0)
    # 每天涨1点约1%<2%，应不通过
    assert not passed

    # check_strength_score(closes, highs, opens, volumes, n)
    passed, score = check_strength_score(closes, highs, opens, volumes, n=20)
    assert 0.0 <= score <= 1.
    print("  [PASS] strength indicators")


def test_deviation_indicators():
    """测试偏离指标"""
    from vnpy.strategy_condition.indicators.deviation import (
        check_dev_ma,
        check_dev_ma_distance,
        check_dev_overbought,
    )
    # 构造close在MA附近的数据
    closes = [10.0] * 30

    # check_dev_ma(closes, ma_period, max_dev_pct)
    passed, score = check_dev_ma(closes, ma_period=10, max_dev_pct=5.0)
    assert passed, "价格等于MA，乖离为0，应通过"
    assert score == 1.0

    # check_dev_ma_distance(closes, fast_period, slow_period, max_distancepct)
    passed, _ = check_dev_ma_distance(closes, fast_period=5, slow_period=20, max_distance_pct=5.0)
    assert passed, "两均线相同，距离为0"

    # check_dev_overbought(closes, ma_period, max_above_pct)
    passed, _ = check_dev_overbought(closes, ma_period=10, max_above_pct=10.0)
    assert passed, "价格等于MA，不超涨"
    print("  [PASS] deviation indicators")


def test_kline_patterns():
    """测试K线形态"""
    from vnpy.strategy_condition.indicators.kline_patterns import (
        check_kline_yin,
        check_kline_yang,
        check_kline_shrink_yin,
        check_kline_doji,
        check_kline_long_lower,
    )
    # check_kline_yin(closes, opens) - 使用列表
    passed, score = check_kline_yin([9.5], [10.0])
    assert passed is True, "阴线"

    # check_kline_yang(closes, opens)
    passed, _ = check_kline_yang([10.5], [10.0])
    assert passed is True, "阳线"

    # check_kline_doji(closes, opens, highs, lows, max_body_ratio)
    passed, _ = check_kline_doji([10.01], [10.0], [10.5], [9.5], max_body_ratio=0.1)
    assert passed, "十字星"

    # check_kline_long_lower(closes, opens, highs, lows, min_ratio)
    passed, _ = check_kline_long_lower([9.8], [10.0], [10.1], [9.0], min_ratio=2.0)
    assert passed, "长下影线"

    # check_kline_shrink_yin(closes, opens, volumes_period)
    closes = [9.5, 9.4, 9.3, 9.2, 9.1, 9.0]
    opens = [10.0, 9.5, 9.4, 9.3, 9.2, 9.1]
    volumes = [1000.0, 900.0, 800.0, 700.0, 600.0, 500.0]
    passed, _ = check_kline_shrink_yin(closes, opens, volumes, vol_period=5)
    assert isinstance(passed, bool)
    print("  [PASS] kline patterns")


def test_volume_advanced():
    """测试量能升级"""
    from vnpy.strategy_condition.indicators.volume_advanced import (
        check_volume_upphase,
        check_volume_layer,
        check_fund_intensity,
    )
    closes = [10.0 + i * 0.1 for i in range(30)]
    volumes = [1000.0] * 15 + [500.0] * 15

    # check_volume_upphase(closes, volumes, n, min_ratio)
    passed, score = check_volume_upphase(closes, volumes, n=20, min_ratio=1.0)
    assert isinstance(passed, bool)

    # check_volume_layer(closes, volumes, up_window, dn_window, max_ratio)
    passed, score = check_volume_layer(closes, volumes, up_window=10, dn_window=5, max_ratio=0.8)
    assert isinstance(score, float)

    # check_fund_intensity(closes, volumes, n, min_score)
    passed, score = check_fund_intensity(closes, volumes, n=10, min_score=0.1)
    assert 0.0 <= score <= 1.0
    print("  [PASS] volume advanced")


def test_trend_advanced():
    """测试趋势升级"""
    from vnpy.strategy_condition.indicators.trend_advanced import (
        check_price_above_ma,
        check_trend_strength,
        check_trend_days,
        check_trend_score,
    )
    # 持续上涨数据
    closes = [10.0 + i * 0.5 for i in range(60)]
    highs = [c + 0.3 for c in closes]
    lows = [c - 0.3 for c in closes]

    # check_price_above_ma(closes, ma_period)
    passed, score = check_price_above_ma(closes, 20)
    assert passed, "持续上涨应站上MA20"

    # check_trend_strength(closes, periods)
    passed, score = check_trend_strength(closes, [5, 10, 20, 30])
    assert passed, "持续上涨应多头排列"

    # check_trend_days(closes, ma_period, min_days)
    passed, score = check_trend_days(closes, 20, 5)
    assert passed, "趋势持续天数应足够"

    # check_trend_score(closes, highs, lows)
    passed, score = check_trend_score(closes, highs, lows)
    assert passed, "趋势综合评分应通过"
    assert score > 0.5
    print("  [PASS] trend advanced")


def test_pullback_advanced():
    """测试回调升级"""
    from vnpy.strategy_condition.indicators.pullback_advanced import (
        check_pullback_to_ma_n,
        check_retracement_pct,
        check_shrink_pullback,
        check_yin_pullback,
    )
    # check_pullback_to_ma_n(closes, ma_period, tol_pct)
    closes = [10.0] * 20+ [10.1]
    passed, score = check_pullback_to_ma_n(closes, ma_period=10, tol_pct=2.0)
    assert passed, "价格接近MA10"

    # check_retracement_pct(closes, highs, n, min_ret, max_ret)
    highs = [12.0] * 20
    closes_ret = [10.0] * 19 + [10.5]
    passed, _ = check_retracement_pct(closes_ret, highs, n=20,
                                      min_ret=-15.0, max_ret=-10.0)
    assert passed, "从12回到10.5约-12.5%在范围内"

    # check_yin_pullback(closes, opens, n)
    closes_yin = [10.0, 9.9, 9.8]
    opens_yin = [10.1, 10.0, 9.9]
    passed, _ = check_yin_pullback(closes_yin, opens_yin, n=3)
    assert passed, "3天阴线"
    print("  [PASS] pullback advanced")


def test_market_indicators():
    """测试市场环境"""
    from vnpy.strategy_condition.indicators.market import (
        check_index_trend,
        check_index_ma_state,
        check_up_ratio,
        check_limit_down_filter,
        MarketContext,
    )
    index_closes = [3000.0 + i * 10 for i in range(60)]

    # check_index_trend(index_closes, ma_period)
    passed, score = check_index_trend(index_closes, 20)
    assert passed, "指数持续上涨应>MA20"

    # check_index_ma_state(index_closes, periods)
    passed, _ = check_index_ma_state(index_closes, [5, 10, 20, 60])
    assert passed

    # check_up_ratio(up_count, total_count, min_ratio)
    passed, _ = check_up_ratio(2500, 5000, 0.4)
    assert passed

    # check_limit_down_filter(limit_down, max_count)
    passed, _ = check_limit_down_filter(5, 20)
    assert passed

    # MarketContext.update(index_closes, up_count, total_count, limit_up, limit_down)
    ctx = MarketContext()
    ctx.update(index_closes, 2500, 5000, 30, 5)
    safe, score = ctx.is_safe()
    assert safe, "上涨市场应安全"
    print("  [PASS] market indicators")


def test_condition_advancedfactories():
    """测试新增条件工厂函数"""
    from vnpy.strategy_condition.core.condition_advanced import (
        cond_strength_returnn,
        cond_strength_limit_up_count,
        cond_strength_score,
        cond_dev_ma10,
        cond_dev_ma10_ma20,
        cond_kline_yin,
        cond_kline_shrink_yin,
        cond_volume_layer,
        cond_fund_intensity,
        cond_pullback_to_ma10,
        cond_first_pullback,
        cond_trend_strength,
        cond_price_above_ma,
        cond_trend_score,
        cond_market_index_trend,
        cond_score_node,
    )
    from vnpy.strategy_condition.constant import ConditionCategory

    c = cond_strength_returnn(n=20, min_return=20.0)
    assert c.category == ConditionCategory.STRENGTH
    assert c.params["n"] == 20

    c = cond_score_node(min_score=80.0)
    assert c.category == ConditionCategory.SCORE
    assert c.params["min_score"] == 80.0
    assert "trend" in c.params["weights"]

    c = cond_kline_yin()
    assert c.category == ConditionCategory.KLINE

    c = cond_market_index_trend(ma_period=20)
    assert c.category == ConditionCategory.MARKET

    # 序列化测试
    d = c.to_dict()
    from vnpy.strategy_condition.core.condition import Condition
    c2 = Condition.from_dict(d)
    assert c2.indicator == c.indicator
    assert c2.params == c.params
    print("  [PASS] condition advanced factories")


def test_all():
    print("=" * 60)
    print("Strategy Condition Engine Advanced - Unit Tests")
    print("=" * 60)
    test_constant_enums()
    test_strength_indicators()
    test_deviation_indicators()
    test_kline_patterns()
    test_volume_advanced()
    test_trend_advanced()
    test_pullback_advanced()
    test_market_indicators()
    test_condition_advancedfactories()
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_all()