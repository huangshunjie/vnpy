"""
market_regime_ai/datasource/factor_loader.py  (Phase 5)

FactorLoader — 从 Quant OS 只读取因子数据。

Phase 5 实现：
  - 读取 Quant OS 系统状态
  - 读取 Alpha 因子数据（波动率 / 趋势 / 流动性 / 相关性代理）
  - 向 Quant OS 输出 regime_state / capital_adjustment / risk_adjustment

❌ 只读 Quant OS 状态，不修改其调度逻辑
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_QOS_ENGINE_NAME = "QuantOS"


class FactorLoader:
    """
    从 Quant OS 读取因子数据 + 输出状态信号（Phase 5 完整实现）。
    """

    def __init__(
        self,
        main_engine: Any = None,
        engine_name: str = _QOS_ENGINE_NAME,
    ) -> None:
        self._main_engine = main_engine
        self._engine_name = engine_name
        self._qos_engine  = None

        # 缓存最新输出值
        self._last_regime_state:    str   = "unknown"
        self._last_capital_adj:     float = 1.0
        self._last_risk_adj:        float = 1.0
        self._last_recommendation:  str   = "neutral"

    # ------------------------------------------------------------------ #
    #  引擎获取（懒加载）
    # ------------------------------------------------------------------ #

    def _get_qos_engine(self):
        if self._qos_engine is not None:
            return self._qos_engine
        if self._main_engine is None:
            return None
        try:
            engine = self._main_engine.get_engine(self._engine_name)
            if engine is not None:
                self._qos_engine = engine
            return engine
        except Exception as e:
            logger.debug(f"[FactorLoader] get_engine failed: {e}")
            return None

    def is_available(self) -> bool:
        return self._get_qos_engine() is not None

    # ------------------------------------------------------------------ #
    #  只读数据获取（Quant OS → Market Regime）
    # ------------------------------------------------------------------ #

    def get_system_health(self) -> dict:
        """获取 Quant OS 系统健康状态（只读）。"""
        engine = self._get_qos_engine()
        if engine is None:
            return {"available": False}
        try:
            health = engine.system_health()
            if isinstance(health, dict):
                return health
            return {"available": True}
        except Exception as e:
            logger.debug(f"[FactorLoader] system_health: {e}")
            return {"available": False, "error": str(e)}

    def get_registered_modules(self) -> list[str]:
        """获取已注册模块列表（只读）。"""
        engine = self._get_qos_engine()
        if engine is None:
            return []
        try:
            modules = engine.registered_modules
            if isinstance(modules, dict):
                return list(modules.keys())
            return []
        except Exception as e:
            logger.debug(f"[FactorLoader] registered_modules: {e}")
            return []

    def get_volatility_factor(self, symbol: str = "") -> float:
        """
        返回波动率因子代理 [0, 1]。

        Phase 5: 优先从 Quant OS Alpha 因子中读取，
        降级时返回 0.4（中性值）。
        """
        engine = self._get_qos_engine()
        if engine is None:
            return 0.4
        try:
            # Quant OS 无直接因子接口，通过系统状态推断
            health = engine.system_health()
            if isinstance(health, dict):
                return float(health.get("volatility_factor", 0.4))
            return 0.4
        except Exception:
            return 0.4

    def get_trend_factor(self, symbol: str = "") -> float:
        """返回趋势因子代理 [0, 1]。"""
        engine = self._get_qos_engine()
        if engine is None:
            return 0.0
        try:
            health = engine.system_health()
            if isinstance(health, dict):
                return float(health.get("trend_factor", 0.0))
            return 0.0
        except Exception:
            return 0.0

    def get_liquidity_factor(self, symbol: str = "") -> float:
        """返回流动性因子代理 [0, 1]（高 = 流动性好）。"""
        engine = self._get_qos_engine()
        if engine is None:
            return 0.6
        try:
            health = engine.system_health()
            if isinstance(health, dict):
                return float(health.get("liquidity_factor", 0.6))
            return 0.6
        except Exception:
            return 0.6

    def get_correlation_factor(self, symbols: list[str] | None = None) -> float:
        """返回相关性因子代理 [0, 1]（高 = 系统性风险高）。"""
        engine = self._get_qos_engine()
        if engine is None:
            return 0.0
        try:
            health = engine.system_health()
            if isinstance(health, dict):
                return float(health.get("correlation_factor", 0.0))
            return 0.0
        except Exception:
            return 0.0

    # ------------------------------------------------------------------ #
    #  Phase 5 联动：输出信号 → Quant OS
    # ------------------------------------------------------------------ #

    def set_regime_output(
        self,
        regime_state:    str,
        capital_adj:     float,
        risk_adj:        float,
        recommendation:  str,
    ) -> None:
        """
        缓存 Market Regime 输出信号（由 dispatcher 调用）。

        ❌ 不直接调用 Quant OS 调度接口
        ✔  信号通过 EventEngine 事件总线传播
        """
        self._last_regime_state   = regime_state
        self._last_capital_adj    = max(0.40, min(1.50, capital_adj))
        self._last_risk_adj       = max(0.30, min(1.30, risk_adj))
        self._last_recommendation = recommendation

    def get_last_output(self) -> dict:
        """获取最近一次向 Quant OS 输出的信号。"""
        return {
            "regime_state":   self._last_regime_state,
            "capital_adj":    round(self._last_capital_adj,   4),
            "risk_adj":       round(self._last_risk_adj,      4),
            "recommendation": self._last_recommendation,
        }

    # ------------------------------------------------------------------ #
    #  摘要
    # ------------------------------------------------------------------ #

    def summary(self) -> dict:
        return {
            "source":          "quant_os",
            "available":       self.is_available(),
            "last_output":     self.get_last_output(),
            "phase":           5,
        }
