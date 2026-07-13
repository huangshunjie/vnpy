"""
screening/engine/portfolio_engine.py
Portfolio Engine Bridge — Phase 8
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PortfolioWeightResult:
    """权重分配结果。"""
    method:       str
    weights:      Dict[str, float]      # symbol -> weight (sum=1.0)
    scores:       Dict[str, float]      # symbol -> composite_score
    generated_at: datetime = field(default_factory=datetime.now)

    def top_n(self, n: int) -> List[tuple]:
        return sorted(self.weights.items(), key=lambda x: x[1], reverse=True)[:n]

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "count": len(self.weights),
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "generated_at": str(self.generated_at)[:19],
        }


def _inverse_vol_weights(
    symbols: List[str],
    vol_map: Dict[str, float],
    default_vol: float = 0.20,
) -> Dict[str, float]:
    """波动率倒数权重：w_i = (1/σ_i) / Σ(1/σ_j)。"""
    inv = {}
    for s in symbols:
        v = vol_map.get(s, default_vol)
        inv[s] = 1.0 / max(v, 0.01)
    total = sum(inv.values())
    return {s: w / total for s, w in inv.items()} if total > 0 else _equal_weights(symbols)


def _equal_weights(symbols: List[str]) -> Dict[str, float]:
    n = len(symbols)
    return {s: 1.0 / n for s in symbols} if n > 0 else {}


def _score_weights(
    symbols: List[str],
    scores: Dict[str, float],
) -> Dict[str, float]:
    """评分比例权重：w_i = score_i / Σ score_j。"""
    total = sum(max(scores.get(s, 0.0), 0.0) for s in symbols)
    if total < 1e-9:
        return _equal_weights(symbols)
    return {s: max(scores.get(s, 0.0), 0.0) / total for s in symbols}


class PortfolioEngineBridge:
    """
    Portfolio Engine Bridge（Phase 8）。

    三种权重方案：
      equal     — 等权
      inv_vol   — 波动率倒数（低波动率给予更高权重）
      score     — 评分加权（综合评分越高权重越大）

    尝试对接 vnpy.portfolio_engine.AllocationEngine；
    不可用时 fallback 到内置纯 Python 实现。
    """

    METHODS = ("equal", "inv_vol", "score")

    def __init__(
        self,
        log_fn: Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
    ) -> None:
        self._log = log_fn or print
        self._main_engine = main_engine
        self._method = "equal"
        self._max_single_weight = 0.10
        self._last_result: Optional[PortfolioWeightResult] = None
        self._allocation_engine = None
        self._init_allocation_engine()

    def _init_allocation_engine(self) -> None:
        try:
            from vnpy.portfolio_engine.engine.allocation_engine import AllocationEngine
            self._allocation_engine = AllocationEngine()
            self._log("[PortfolioBridge] AllocationEngine loaded")
        except Exception:
            self._log("[PortfolioBridge] Using builtin weight methods")

    # ── 配置 ─────────────────────────────────────────────────────────

    def set_method(self, method: str) -> None:
        if method in self.METHODS:
            self._method = method

    def set_max_single_weight(self, w: float) -> None:
        self._max_single_weight = max(0.0, min(1.0, w))

    # ── 主接口 ────────────────────────────────────────────────────────

    def generate_portfolio(
        self,
        symbols: List[str],
        scores: Optional[Dict[str, float]] = None,
    ) -> Optional[PortfolioWeightResult]:
        """生成组合权重建议。"""
        if not symbols:
            self._log("[PortfolioBridge] 股票池为空")
            return None

        self._log(
            f"[PortfolioBridge] 生成组合权重：{len(symbols)} 只，方式={self._method}"
        )

        scores = scores or {s: 1.0 for s in symbols}
        vol_map = self._get_vol_map(symbols)

        if self._method == "inv_vol":
            weights = _inverse_vol_weights(symbols, vol_map)
        elif self._method == "score":
            weights = _score_weights(symbols, scores)
        else:
            weights = _equal_weights(symbols)

        # 单票权重上限约束
        weights = self._apply_weight_cap(weights)

        self._last_result = PortfolioWeightResult(
            method=self._method,
            weights=weights,
            scores=scores,
        )
        top3 = self._last_result.top_n(3)
        self._log(
            f"[PortfolioBridge] 权重生成完成，Top3：{top3}"
        )
        return self._last_result

    def _apply_weight_cap(self, weights: Dict[str, float]) -> Dict[str, float]:
        """对超过上限的权重做截断并重新归一化。"""
        cap = self._max_single_weight
        if cap <= 0:
            return weights
        capped = {s: min(w, cap) for s, w in weights.items()}
        total = sum(capped.values())
        if total < 1e-9:
            return _equal_weights(list(weights.keys()))
        return {s: w / total for s, w in capped.items()}

    def _get_vol_map(self, symbols: List[str]) -> Dict[str, float]:
        """获取各股票近期波动率。"""
        result: Dict[str, float] = {}
        if self._main_engine is None:
            return result
        try:
            from ..utils.data_fetcher import DataFetcher
            fetcher = DataFetcher(main_engine=self._main_engine)
            for sym in symbols:
                sd = fetcher.get_symbol_data(sym)
                if len(sd.closes) >= 21:
                    closes = sd.closes[-21:]
                    rets = [(closes[i] - closes[i-1]) / closes[i-1]
                            for i in range(1, len(closes)) if closes[i-1] > 0]
                    if rets:
                        mu = sum(rets) / len(rets)
                        var = sum((r - mu)**2 for r in rets) / len(rets)
                        result[sym] = math.sqrt(var * 252)
        except Exception:
            pass
        return result

    # ── 查询 ──────────────────────────────────────────────────────────

    def get_last_result(self) -> Optional[PortfolioWeightResult]:
        return self._last_result

    def summary(self) -> dict:
        if self._last_result:
            return {
                "method": self._last_result.method,
                "count": len(self._last_result.weights),
                "generated_at": str(self._last_result.generated_at)[:19],
            }
        return {"status": "no_portfolio"}
