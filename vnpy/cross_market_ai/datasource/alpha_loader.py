"""
cross_market_ai/datasource/alpha_loader.py

Phase 3: 只读 Alpha 信号加载器。
数据来源：AlphaFactory / Alpha Research（只读）。
禁止写入或修改任何 Alpha 逻辑。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional


class AlphaDataLoader:
    """
    从 AlphaFactory / Alpha Research 读取 Alpha 信号元数据。
    纯只读；上层不可用时返回占位描述符。
    """

    # 内置 Alpha 类型先验特征
    _ALPHA_PRIORS: dict[str, dict] = {
        "momentum": {
            "signal_decay_days":  20,
            "vol_sensitivity":    0.7,
            "liquidity_sensitivity": 0.5,
            "regime_sensitivity": {"bull": 0.8, "bear": 0.3, "sideways": 0.2, "high_vol": 0.4},
            "market_dependency":  "trend",
            "typical_ic":         0.05,
            "typical_sharpe":     0.8,
        },
        "mean_reversion": {
            "signal_decay_days":  5,
            "vol_sensitivity":    0.4,
            "liquidity_sensitivity": 0.8,
            "regime_sensitivity": {"bull": 0.3, "bear": 0.3, "sideways": 0.9, "high_vol": 0.2},
            "market_dependency":  "microstructure",
            "typical_ic":         0.04,
            "typical_sharpe":     0.6,
        },
        "value": {
            "signal_decay_days":  60,
            "vol_sensitivity":    0.3,
            "liquidity_sensitivity": 0.3,
            "regime_sensitivity": {"bull": 0.5, "bear": 0.6, "sideways": 0.5, "high_vol": 0.3},
            "market_dependency":  "fundamental",
            "typical_ic":         0.03,
            "typical_sharpe":     0.5,
        },
        "volatility": {
            "signal_decay_days":  10,
            "vol_sensitivity":    0.9,
            "liquidity_sensitivity": 0.6,
            "regime_sensitivity": {"bull": 0.4, "bear": 0.7, "sideways": 0.3, "high_vol": 0.9},
            "market_dependency":  "volatility_structure",
            "typical_ic":         0.06,
            "typical_sharpe":     0.7,
        },
        "carry": {
            "signal_decay_days":  30,
            "vol_sensitivity":    0.5,
            "liquidity_sensitivity": 0.4,
            "regime_sensitivity": {"bull": 0.6, "bear": 0.3, "sideways": 0.7, "high_vol": 0.2},
            "market_dependency":  "rate_structure",
            "typical_ic":         0.04,
            "typical_sharpe":     0.6,
        },
    }
    _DEFAULT_ALPHA = {
        "signal_decay_days":  15,
        "vol_sensitivity":    0.5,
        "liquidity_sensitivity": 0.5,
        "regime_sensitivity": {"bull": 0.5, "bear": 0.5, "sideways": 0.5, "high_vol": 0.5},
        "market_dependency":  "unknown",
        "typical_ic":         0.03,
        "typical_sharpe":     0.5,
    }

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    # ── 主接口 ────────────────────────────────────────────────────────

    def load_alpha_metadata(self, alpha_id: str) -> dict:
        """
        加载 Alpha 元数据：信号类型、衰减周期、市场敏感度。
        优先从 AlphaFactory 读取，不可用时返回类型先验。
        """
        live = self._try_fetch_live_metadata(alpha_id)
        if live:
            return {**live, "source": "live", "alpha_id": alpha_id, "loaded_at": _now()}

        prior_key = self._infer_alpha_type(alpha_id)
        prior     = self._ALPHA_PRIORS.get(prior_key, self._DEFAULT_ALPHA)
        return {
            "alpha_id":              alpha_id,
            "alpha_type":            prior_key,
            "signal_decay_days":     prior["signal_decay_days"],
            "vol_sensitivity":       prior["vol_sensitivity"],
            "liquidity_sensitivity": prior["liquidity_sensitivity"],
            "regime_sensitivity":    prior["regime_sensitivity"],
            "market_dependency":     prior["market_dependency"],
            "typical_ic":            prior["typical_ic"],
            "typical_sharpe":        prior["typical_sharpe"],
            "source":                "prior",
            "loaded_at":             _now(),
        }

    def load_alpha_performance(
        self, alpha_id: str, market_id: str
    ) -> dict:
        """
        加载 Alpha 在特定市场的历史表现统计。
        优先从 AlphaFactory 读取。
        """
        live = self._try_fetch_live_performance(alpha_id, market_id)
        if live:
            return {**live, "source": "live", "loaded_at": _now()}

        prior_key  = self._infer_alpha_type(alpha_id)
        prior      = self._ALPHA_PRIORS.get(prior_key, self._DEFAULT_ALPHA)
        # 基于市场类型对先验进行调整
        ic_adj     = self._market_ic_adjustment(market_id)
        return {
            "alpha_id":       alpha_id,
            "market_id":      market_id,
            "ic_mean":        round(prior["typical_ic"] * ic_adj, 5),
            "ic_std":         round(prior["typical_ic"] * 0.8, 5),
            "ic_ir":          round(prior["typical_ic"] / max(prior["typical_ic"] * 0.8, 1e-9), 4),
            "sharpe":         round(prior["typical_sharpe"] * ic_adj, 4),
            "max_drawdown":   round(0.15 / ic_adj, 4),
            "win_rate":       round(0.52 + prior["typical_ic"] * 2, 4),
            "n_observations": 252,
            "source":         "prior",
            "loaded_at":      _now(),
        }

    def load_alpha_regime_profile(
        self, alpha_id: str, market_id: str
    ) -> dict:
        """
        加载 Alpha 在不同 Regime 下的分条件表现。
        用于判断 Alpha 是否具备 Regime 不变性。
        """
        prior_key = self._infer_alpha_type(alpha_id)
        prior     = self._ALPHA_PRIORS.get(prior_key, self._DEFAULT_ALPHA)
        ic_adj    = self._market_ic_adjustment(market_id)
        reg_sens  = prior["regime_sensitivity"]

        profiles: dict[str, dict] = {}
        for regime, sensitivity in reg_sens.items():
            ic = round(prior["typical_ic"] * sensitivity * ic_adj, 5)
            profiles[regime] = {
                "ic_mean":  ic,
                "active":   sensitivity >= 0.4,
                "weight":   round(sensitivity, 4),
            }

        # Regime 不变性：各 regime 下 IC 方差越小越好
        ic_values = [v["ic_mean"] for v in profiles.values()]
        avg_ic    = sum(ic_values) / len(ic_values) if ic_values else 0.0
        ic_std    = (sum((x - avg_ic) ** 2 for x in ic_values) / len(ic_values)) ** 0.5
        invariance = max(0.0, 1.0 - ic_std / max(abs(avg_ic), 1e-9) * 0.5)

        return {
            "alpha_id":          alpha_id,
            "market_id":         market_id,
            "regime_profiles":   profiles,
            "regime_invariance": round(invariance, 4),
            "avg_ic":            round(avg_ic, 5),
            "ic_std_across_regimes": round(ic_std, 5),
            "source":            "prior",
            "loaded_at":         _now(),
        }

    def list_available_alphas(self) -> list[str]:
        """返回已知 Alpha 类型列表。"""
        live = self._try_list_live_alphas()
        if live:
            return live
        return list(self._ALPHA_PRIORS.keys())

    # ── 只读上层引擎 ──────────────────────────────────────────────────

    def _try_fetch_live_metadata(self, alpha_id: str) -> Optional[dict]:
        if self._main_engine is None:
            return None
        try:
            af = self._main_engine.get_engine("AlphaFactoryAI")
            if af and hasattr(af, "get_alpha_metadata"):
                return af.get_alpha_metadata(alpha_id) or None
        except Exception:
            pass
        return None

    def _try_fetch_live_performance(
        self, alpha_id: str, market_id: str
    ) -> Optional[dict]:
        if self._main_engine is None:
            return None
        try:
            af = self._main_engine.get_engine("AlphaFactoryAI")
            if af and hasattr(af, "get_alpha_performance"):
                return af.get_alpha_performance(alpha_id, market_id) or None
        except Exception:
            pass
        return None

    def _try_list_live_alphas(self) -> Optional[list]:
        if self._main_engine is None:
            return None
        try:
            af = self._main_engine.get_engine("AlphaFactoryAI")
            if af and hasattr(af, "list_alphas"):
                return af.list_alphas() or None
        except Exception:
            pass
        return None

    @staticmethod
    def _infer_alpha_type(alpha_id: str) -> str:
        """从 alpha_id 推断 Alpha 类型。"""
        aid = alpha_id.lower()
        for key in ("momentum", "mean_reversion", "value", "volatility", "carry"):
            if key.replace("_", "") in aid.replace("_", ""):
                return key
        return "momentum"

    @staticmethod
    def _market_ic_adjustment(market_id: str) -> float:
        """基于市场类型给出 IC 调整系数。"""
        adjustments = {
            "equity_cn":    1.0,
            "futures_cn":   0.9,
            "equity_us":    0.8,
            "crypto":       1.2,
            "forex":        0.7,
            "fixed_income": 0.6,
        }
        for key, adj in adjustments.items():
            if market_id.startswith(key.split("_")[0]):
                return adj
        return 0.85


def _now() -> str:
    return str(datetime.now())[:19]
