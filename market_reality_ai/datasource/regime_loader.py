"""
market_reality_ai/datasource/regime_loader.py

Phase 1: Stub — 只读接口，从 MarketRegimeAI 拉取市场状态。
❌ 禁止写入或修改 MarketRegimeAI。
"""
from __future__ import annotations
from datetime import datetime


class RegimeLoader:
    """
    市场状态加载器 (只读)。

    Phase 3+: 从 MarketRegimeAI 读取当前 Regime 标签、
              转换概率，供冲击模拟器和压力引擎使用。
    """

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    def get_current_regime(self) -> dict:
        """Phase 3+: 读取当前 Regime 快照。"""
        return {}   # stub

    def get_regime_probabilities(self) -> dict:
        """Phase 3+: 读取各 Regime 的当前概率分布。"""
        return {}   # stub

    def get_historical_regimes(self, start: datetime,
                                end: datetime) -> list:
        """Phase 4+: 读取历史 Regime 序列（用于 Walk-Forward 分层）。"""
        return []   # stub

    def get_transition_matrix(self) -> dict:
        """Phase 4+: 读取 Regime 转移矩阵。"""
        return {}   # stub
