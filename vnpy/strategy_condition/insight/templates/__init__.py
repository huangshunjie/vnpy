"""Insight 模板数据汇总"""
from .trend_insights import TREND_INSIGHTS
from .volume_insights import VOLUME_INSIGHTS
from .pullback_insights import PULLBACK_INSIGHTS
from .momentum_insights import MOMENTUM_INSIGHTS
from .kline_insights import KLINE_INSIGHTS
from .strength_insights import STRENGTH_INSIGHTS
from .deviation_insights import DEVIATION_INSIGHTS
from .market_insights import MARKET_INSIGHTS, EXIT_INSIGHTS


def get_all_insights() -> dict:
    """获取所有条件的 Insight 数据（合并所有模块）"""
    all_insights = {}
    all_insights.update(TREND_INSIGHTS)
    all_insights.update(VOLUME_INSIGHTS)
    all_insights.update(PULLBACK_INSIGHTS)
    all_insights.update(MOMENTUM_INSIGHTS)
    all_insights.update(KLINE_INSIGHTS)
    all_insights.update(STRENGTH_INSIGHTS)
    all_insights.update(DEVIATION_INSIGHTS)
    all_insights.update(MARKET_INSIGHTS)
    all_insights.update(EXIT_INSIGHTS)
    return all_insights


# manager._load_builtin() 使用此变量
BUILTIN_INSIGHTS = get_all_insights()
