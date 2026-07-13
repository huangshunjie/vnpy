"""
cross_market_ai/datasource/market_loader.py

Phase 2: 只读市场结构数据加载器。
数据来源：Data Intelligence Layer + Market Reality Simulation。
禁止写入或修改任何上层引擎。
"""
from __future__ import annotations
import math
import random
from datetime import datetime
from typing import Optional


class MarketDataLoader:
    """
    从 Data Intelligence / Market Reality 读取市场结构数据。
    纯只读；上层不可用时返回统计先验（graceful degradation）。
    """

    _MARKET_PRIORS: dict[str, dict] = {
        "equity_cn": {
            "volatility_annual": 0.28, "bid_ask_spread_bps": 8.0,
            "daily_turnover_pct": 0.015, "tick_size": 0.01, "lot_size": 100,
            "participant_retail": 0.75, "has_price_limit": True,
            "price_limit_pct": 0.10, "session_hours": 4.0, "has_overnight": False,
        },
        "futures_cn": {
            "volatility_annual": 0.22, "bid_ask_spread_bps": 2.0,
            "daily_turnover_pct": 0.35, "tick_size": 1.0, "lot_size": 1,
            "participant_retail": 0.35, "has_price_limit": True,
            "price_limit_pct": 0.05, "session_hours": 17.0, "has_overnight": True,
        },
        "equity_us": {
            "volatility_annual": 0.18, "bid_ask_spread_bps": 1.5,
            "daily_turnover_pct": 0.008, "tick_size": 0.01, "lot_size": 1,
            "participant_retail": 0.20, "has_price_limit": False,
            "price_limit_pct": 0.0, "session_hours": 6.5, "has_overnight": False,
        },
        "crypto": {
            "volatility_annual": 0.75, "bid_ask_spread_bps": 5.0,
            "daily_turnover_pct": 0.05, "tick_size": 0.01, "lot_size": 0.001,
            "participant_retail": 0.55, "has_price_limit": False,
            "price_limit_pct": 0.0, "session_hours": 24.0, "has_overnight": True,
        },
        "forex": {
            "volatility_annual": 0.08, "bid_ask_spread_bps": 0.5,
            "daily_turnover_pct": 999.0, "tick_size": 0.0001, "lot_size": 1000,
            "participant_retail": 0.05, "has_price_limit": False,
            "price_limit_pct": 0.0, "session_hours": 24.0, "has_overnight": True,
        },
        "fixed_income": {
            "volatility_annual": 0.05, "bid_ask_spread_bps": 1.0,
            "daily_turnover_pct": 0.003, "tick_size": 0.001, "lot_size": 1,
            "participant_retail": 0.02, "has_price_limit": False,
            "price_limit_pct": 0.0, "session_hours": 8.0, "has_overnight": False,
        },
    }
    _DEFAULT_PRIOR: dict = {
        "volatility_annual": 0.25, "bid_ask_spread_bps": 5.0,
        "daily_turnover_pct": 0.01, "tick_size": 0.01, "lot_size": 1,
        "participant_retail": 0.40, "has_price_limit": False,
        "price_limit_pct": 0.0, "session_hours": 8.0, "has_overnight": False,
    }

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    # ── 主接口 ────────────────────────────────────────────────────────

    def load_volatility_structure(self, market_id: str, lookback_days: int = 252) -> dict:
        """波动率结构：annual_vol / daily_vol / vol_of_vol / skew / kurtosis / jump_intensity"""
        prior    = self._get_prior(market_id)
        σ_annual = prior["volatility_annual"]
        σ_daily  = σ_annual / math.sqrt(252)
        live     = self._try_fetch_live_volatility(market_id)
        if live:
            σ_annual = live.get("annual_vol", σ_annual)
            σ_daily  = live.get("daily_vol",  σ_daily)
            source   = "live"
        else:
            source = "prior"
        has_limit  = prior["has_price_limit"]
        jump_base  = 0.005 if has_limit else 0.02
        skew_base  = -0.3 if market_id.startswith("equity") else 0.0
        return {
            "market_id": market_id,
            "annual_vol": round(σ_annual, 6),
            "daily_vol":  round(σ_daily, 6),
            "vol_of_vol": round(σ_annual * 0.25, 6),
            "skew":       round(skew_base + random.gauss(0, 0.05), 4),
            "excess_kurtosis": round(2.5 + random.gauss(0, 0.5), 4),
            "jump_intensity":  round(jump_base, 4),
            "lookback_days":   lookback_days,
            "source": source, "loaded_at": _now(),
        }

    def load_liquidity_structure(self, market_id: str) -> dict:
        """流动性结构：bid_ask_spread_bps / depth_score / turnover_ratio / impact_coeff"""
        prior  = self._get_prior(market_id)
        spread = prior["bid_ask_spread_bps"]
        turn   = prior["daily_turnover_pct"]
        live   = self._try_fetch_live_liquidity(market_id)
        if live:
            spread = live.get("spread_bps", spread)
            source = "live"
        else:
            source = "prior"
        depth_score  = max(0.0, min(1.0, 1.0 - spread / 20.0))
        impact_coeff = min(1.0, 0.1 / max(turn, 1e-6) * 0.5)
        return {
            "market_id": market_id,
            "bid_ask_spread_bps": round(spread, 4),
            "depth_score":        round(depth_score, 4),
            "turnover_ratio":     round(min(turn, 1.0), 6),
            "market_impact_coeff":round(impact_coeff, 6),
            "lot_size":  prior["lot_size"],
            "tick_size": prior["tick_size"],
            "source": source, "loaded_at": _now(),
        }

    def load_participant_structure(self, market_id: str) -> dict:
        """参与者结构：retail_ratio / institutional_ratio / hft_ratio / info_asymmetry"""
        prior        = self._get_prior(market_id)
        retail       = prior["participant_retail"]
        inst         = 1.0 - retail
        hft          = inst * (0.05 if market_id == "equity_cn" else 0.40)
        info_asym    = retail * 0.6
        return {
            "market_id": market_id,
            "retail_ratio":        round(retail, 4),
            "institutional_ratio": round(inst - hft, 4),
            "hft_ratio":           round(hft, 4),
            "info_asymmetry":      round(info_asym, 4),
            "source": "prior", "loaded_at": _now(),
        }

    def load_microstructure_noise(self, market_id: str) -> dict:
        """微观结构噪音：noise_ratio / autocorr_lag1 / price_discreteness / adverse_selection"""
        prior          = self._get_prior(market_id)
        spread         = prior["bid_ask_spread_bps"]
        has_limit      = prior["has_price_limit"]
        noise_ratio    = min(spread / 100.0 * 2, 1.0)
        autocorr_lag1  = -0.05 if spread < 3 else -0.15
        price_disc     = min(prior["tick_size"] / 100.0, 1.0)
        adverse_sel    = prior["participant_retail"] * 0.2
        limit_dist     = 0.3 if has_limit else 0.0
        return {
            "market_id": market_id,
            "noise_ratio":        round(noise_ratio, 6),
            "autocorr_lag1":      round(autocorr_lag1, 4),
            "price_discreteness": round(price_disc, 6),
            "adverse_selection":  round(adverse_sel, 4),
            "limit_distortion":   round(limit_dist, 4),
            "source": "prior", "loaded_at": _now(),
        }

    def load_regime_distribution(self, market_id: str, lookback_days: int = 504) -> dict:
        """Regime 分布：各状态历史占比。优先从 MarketRegimeAI 读取。"""
        live = self._try_fetch_live_regime(market_id)
        if live:
            return {**live, "source": "live", "loaded_at": _now()}
        dist = _regime_prior_distribution(market_id)
        return {
            "market_id": market_id, "distribution": dist,
            "n_regimes": len(dist), "lookback_days": lookback_days,
            "source": "prior", "loaded_at": _now(),
        }

    def load_cross_market_correlation(self, market_a: str, market_b: str) -> dict:
        """跨市场相关性先验估计。"""
        corr = _estimate_cross_market_corr(market_a, market_b)
        return {
            "market_a": market_a, "market_b": market_b,
            "correlation": round(corr, 4),
            "stability":   round(max(0.0, 1.0 - abs(corr) * 0.3), 4),
            "source": "prior", "loaded_at": _now(),
        }

    def list_available_markets(self) -> list[str]:
        return list(self._MARKET_PRIORS.keys())

    # ── 只读上层引擎（graceful degradation）─────────────────────────

    def _try_fetch_live_volatility(self, market_id: str) -> Optional[dict]:
        if self._main_engine is None:
            return None
        try:
            dil = self._main_engine.get_engine("DataIntelligenceAI")
            if dil and hasattr(dil, "get_feature_snapshot"):
                return dil.get_feature_snapshot(market_id, "volatility") or None
        except Exception:
            pass
        return None

    def _try_fetch_live_liquidity(self, market_id: str) -> Optional[dict]:
        if self._main_engine is None:
            return None
        try:
            exe = self._main_engine.get_engine("ExecutionIntelligenceAI")
            if exe and hasattr(exe, "get_liquidity_snapshot"):
                return exe.get_liquidity_snapshot(market_id) or None
        except Exception:
            pass
        return None

    def _try_fetch_live_regime(self, market_id: str) -> Optional[dict]:
        if self._main_engine is None:
            return None
        try:
            reng = self._main_engine.get_engine("MarketRegimeAI")
            if reng and hasattr(reng, "get_regime_distribution"):
                return reng.get_regime_distribution(market_id) or None
        except Exception:
            pass
        return None

    def _get_prior(self, market_id: str) -> dict:
        if market_id in self._MARKET_PRIORS:
            return self._MARKET_PRIORS[market_id]
        prefix = market_id.split("_")[0]
        for key in self._MARKET_PRIORS:
            if key.startswith(prefix):
                return self._MARKET_PRIORS[key]
        return self._DEFAULT_PRIOR


# ── 模块级工具 ────────────────────────────────────────────────────────

def _now() -> str:
    return str(datetime.now())[:19]


def _regime_prior_distribution(market_id: str) -> dict:
    mapping = {
        "equity_cn":    {"bull": 0.38, "bear": 0.28, "sideways": 0.22, "panic": 0.12},
        "futures_cn":   {"trend_up": 0.30, "trend_down": 0.25, "range": 0.35, "extreme": 0.10},
        "equity_us":    {"bull": 0.45, "bear": 0.20, "sideways": 0.28, "crash": 0.07},
        "crypto":       {"bull": 0.30, "bear": 0.35, "sideways": 0.20, "extreme": 0.15},
        "forex":        {"trend": 0.40, "range": 0.50, "volatile": 0.10},
        "fixed_income": {"rally": 0.35, "selloff": 0.20, "stable": 0.45},
    }
    return mapping.get(market_id, {"bull": 0.35, "bear": 0.25, "sideways": 0.30, "extreme": 0.10})


def _estimate_cross_market_corr(market_a: str, market_b: str) -> float:
    if market_a.split("_")[0] == market_b.split("_")[0]:
        return 0.65
    pairs = {
        frozenset({"equity_cn", "equity_us"}):    0.35,
        frozenset({"equity_cn", "futures_cn"}):   0.28,
        frozenset({"equity_us", "futures_cn"}):   0.15,
        frozenset({"equity_cn", "crypto"}):       0.12,
        frozenset({"equity_us", "crypto"}):       0.20,
        frozenset({"futures_cn", "crypto"}):      0.05,
        frozenset({"equity_cn", "forex"}):        0.08,
        frozenset({"equity_us", "forex"}):        0.18,
        frozenset({"equity_cn", "fixed_income"}): -0.15,
        frozenset({"equity_us", "fixed_income"}): -0.25,
    }
    return pairs.get(frozenset({market_a, market_b}), 0.05)
