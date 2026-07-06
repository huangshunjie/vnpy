"""
market_reality_ai/datasource/risk_loader.py

Phase 1: Stub — 只读接口，从 RiskEngine2 拉取风险状态。
❌ 禁止写入或修改 RiskEngine2。
"""
from __future__ import annotations
from datetime import datetime


class RiskLoader:
    """
    风险状态加载器 (只读)。

    Phase 2+: 从 RiskEngine2 读取 VaR / CVaR / 风险预算、
              风险告警，供压力测试引擎使用。
    """

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    def get_current_risk_metrics(self) -> dict:
        """Phase 2+: 读取当前风险指标快照。"""
        return {}   # stub

    def get_var(self, confidence: float = 0.99) -> float:
        """Phase 4+: 读取当前 VaR 估计值。"""
        return 0.0   # stub

    def get_risk_alerts(self) -> list:
        """Phase 4+: 读取当前活跃风险告警。"""
        return []   # stub

    def get_historical_risk(self, start: datetime,
                             end: datetime) -> list:
        """Phase 4+: 读取历史风险指标序列。"""
        return []   # stub
