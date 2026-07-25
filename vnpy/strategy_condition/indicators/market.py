"""
strategy_condition/indicators/market.py
市场环境模块：指数趋势、指数均线状态、涨跌比例、涨停数量、市场风险状态
用于控制策略整体开关
"""
from __future__ import annotations
from typing import List, Tuple, Dict


def _calc_ma(data: List[float], period: int) -> float:
    if len(data) < period:
        return 0.0
    return sum(data[-period:]) / period


def check_index_trend(index_closes: List[float],
                      ma_period: int = 20) -> Tuple[bool, float]:
    """
    指数趋势：指数收盘价 > MA(period)
    """
    if len(index_closes) < ma_period:
        return False, 0.0
    ma = _calc_ma(index_closes, ma_period)
    if ma <= 0:
        return False, 0.0
    passed = index_closes[-1] > ma
    above = (index_closes[-1] - ma) / ma * 100.0
    score = min(above / 3.0, 1.0) if passed else 0.0
    return passed, max(score, 0.0)


def check_index_ma_state(index_closes: List[float],
                         periods: List[int] = None) -> Tuple[bool, float]:
    """
    指数均线状态：指数多条均线多头排列
    """
    if periods is None:
        periods = [5, 10, 20, 60]
    if len(index_closes) < max(periods):
        return False, 0.0
    mas = [_calc_ma(index_closes, p) for p in periods]
    pairs = len(mas) - 1
    aligned = sum(1 for i in range(pairs) if mas[i] > mas[i + 1])
    score = aligned / pairs if pairs > 0 else 0.0
    passed = score >= 0.5
    return passed, score


def check_up_ratio(up_count: int, total_count: int,
                   min_ratio: float = 0.5) -> Tuple[bool, float]:
    """
    涨跌比例：上涨股票数/总股票数 >= min_ratio
    """
    if total_count <= 0:
        return False, 0.0
    ratio = up_count / total_count
    passed = ratio >= min_ratio
    score = min(ratio / (min_ratio * 1.5), 1.0) if passed else 0.0
    return passed, score


def check_limit_upcount(limit_up: int, min_count: int = 10) -> Tuple[bool, float]:
    """
    涨停数量 >= min_count (市场活跃度)
    """
    passed = limit_up >= min_count
    score = min(limit_up / (min_count * 3.0), 1.0) if passed else 0.0
    return passed, score


def check_limit_down_filter(limit_down: int,
                            max_count: int = 20) -> Tuple[bool, float]:
    """
    跌停数量过滤：跌停数 <= max_count（市场不恐慌）
    返回True表示市场安全
    """
    passed = limit_down <= max_count
    score = max(1.0 - limit_down / max_count, 0.0) if passed else 0.0
    return passed, score


def check_market_risk(index_closes: List[float],
                      up_count: int = 0, total_count: int = 0,
                      limit_down: int = 0) -> Tuple[bool, float]:
    """
    市场风险状态综合评估：
    - 指数趋势 (0.4)
    - 涨跌比例 (0.3)
    - 跌停数量 (0.3)
    返回True表示市场安全可以操作
    """
    score = 0.0
    _, s1 = check_index_trend(index_closes, 20)
    score += s1 * 0.4
    if total_count > 0:
        _, s2 = check_up_ratio(up_count, total_count, 0.4)
        score += s2 * 0.3
    else:
        score += 0.15  # 无数据时给中性分
    _, s3 = check_limit_down_filter(limit_down, 30)
    score += s3 * 0.3
    passed = score >= 0.4
    return passed, min(score, 1.0)


class MarketContext:
    """
    市场环境上下文，在扫描/回测时提供全市场数据
    """

    def __init__(self):
        self.index_closes: List[float] = []
        self.up_count: int = 0
        self.total_count: int = 0
        self.limit_upcount: int = 0
        self.limit_down_count: int = 0

    def update(self, index_closes: List[float],
               up_count: int, total_count: int,
               limit_up: int, limit_down: int):
        self.index_closes = index_closes
        self.up_count = up_count
        self.total_count = total_count
        self.limit_up_count = limit_up
        self.limit_down_count = limit_down

    def is_safe(self) -> Tuple[bool, float]:
        """市场是否安全可操作"""
        return check_market_risk(
            self.index_closes,
            self.up_count,
            self.total_count,
            self.limit_down_count
        )

    def to_dict(self) -> Dict:
        return {
            "up_count": self.up_count,
            "total_count": self.total_count,
            "limit_up": self.limit_up_count,
            "limit_down": self.limit_down_count,
            "index_len": len(self.index_closes),
        }