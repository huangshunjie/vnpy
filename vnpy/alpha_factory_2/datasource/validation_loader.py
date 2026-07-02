"""
alpha_factory_2/datasource/validation_loader.py  (Phase 3)

ValidationLoader — 验证结果加载器。

Phase 3 提供：
  - 基于 FactorLoader 模拟数据生成的验证结果
  - 支持单因子 / 批量加载
  - 供 ScoringEngine 使用

❌ 不连接外部数据源
✔  使用 FactorLoader 的模拟因子数据推导验证指标
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime

from .factor_loader import FactorLoader, BUILTIN_FACTORS
from ..utils.scoring_utils import (
    compute_ic,
    compute_rank_ic,
    compute_ic_series,
    compute_stability,
    compute_mean_turnover,
)
from ..utils.decay_utils import compute_ic_decay_from_panel, decay_half_life


@dataclass
class ValidationResult:
    """单个因子的验证结果。"""
    factor_name:  str
    ic:           float = 0.0
    rank_ic:      float = 0.0
    ic_ir:        float = 0.0       # IC 信息比率（Stability）
    half_life:    float = 0.0       # IC 半衰期（交易日）
    mean_turnover: float = 0.0
    n_periods:    int   = 0
    validated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "factor_name":    self.factor_name,
            "ic":             round(self.ic, 4),
            "rank_ic":        round(self.rank_ic, 4),
            "ic_ir":          round(self.ic_ir, 4),
            "half_life":      round(self.half_life, 2),
            "mean_turnover":  round(self.mean_turnover, 4),
            "n_periods":      self.n_periods,
            "validated_at":   str(self.validated_at)[:19],
        }


class ValidationLoader:
    """
    验证结果加载器（Phase 3）。

    Phase 3: 使用 FactorLoader 的模拟数据推导验证指标。
    Phase 4+: 接入真实 Validation Engine 输出（只读）。
    """

    def __init__(
        self,
        factor_loader: FactorLoader | None = None,
        n_symbols:     int = 50,    # 模拟截面标的数量
        n_periods:     int = 60,    # 历史期数
        seed:          int = 0,
    ) -> None:
        self._loader    = factor_loader or FactorLoader(n_bars=n_periods)
        self._n_symbols = n_symbols
        self._n_periods = n_periods
        self._seed      = seed
        self._cache: dict[str, ValidationResult] = {}
        self._rng   = random.Random(seed)

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def load_result(self, factor_name: str) -> ValidationResult:
        """加载指定因子的验证结果（有缓存）。"""
        if factor_name in self._cache:
            return self._cache[factor_name]
        result = self._compute(factor_name)
        self._cache[factor_name] = result
        return result

    def batch_load(self, factor_names: list[str]) -> dict[str, ValidationResult]:
        """批量加载验证结果。"""
        return {name: self.load_result(name) for name in factor_names}

    def list_validated_factors(self) -> list[str]:
        """列出所有可验证的因子名称。"""
        return self._loader.list_available_factors()

    def clear_cache(self) -> None:
        self._cache.clear()

    # ------------------------------------------------------------------ #
    #  内部计算
    # ------------------------------------------------------------------ #

    def _compute(self, factor_name: str) -> ValidationResult:
        """
        基于模拟数据推导单个因子的验证指标。

        每个标的有 n_periods 条数据，构建截面面板：
          alpha_panel[t]   : t 期各标的因子值（截面）
          returns_panel[t] : t 期各标的收益率（截面，模拟）
        """
        T  = self._n_periods
        N  = self._n_symbols

        # 加载该因子的模拟时序数据（T 条）
        fd = self._loader.load_factor(factor_name)
        factor_ts = fd.values[:T] if len(fd.values) >= T else fd.values

        # 生成模拟截面：每期 N 个标的的因子值 + 对应收益率
        name_hash   = sum(ord(c) for c in factor_name)
        rng         = random.Random(self._seed + name_hash)

        # 基础 IC 方向（模拟不同因子有不同预测力）
        base_ic = rng.uniform(-0.08, 0.12)   # 模拟真实因子 IC 分布

        alpha_panel:   list[list[float]] = []
        returns_panel: list[list[float]] = []

        for t in range(len(factor_ts)):
            # 截面因子值：围绕时序值加噪
            alpha_cross = [
                factor_ts[t] + rng.gauss(0, 0.5)
                for _ in range(N)
            ]
            # 收益率：与因子值有 base_ic 程度相关
            returns_cross = [
                base_ic * alpha_cross[i] + rng.gauss(0, 1.0)
                for i in range(N)
            ]
            alpha_panel.append(alpha_cross)
            returns_panel.append(returns_cross)

        # IC 序列（每期截面 IC）
        ic_series = compute_ic_series(alpha_panel, returns_panel, use_rank=False)
        ric_series = compute_ic_series(alpha_panel, returns_panel, use_rank=True)

        mean_ic   = sum(ic_series) / len(ic_series) if ic_series else 0.0
        mean_ric  = sum(ric_series) / len(ric_series) if ric_series else 0.0
        ic_ir     = compute_stability(ic_series)

        # IC Decay 曲线
        max_lag   = min(20, len(alpha_panel) // 2)
        ic_decay  = compute_ic_decay_from_panel(
            alpha_panel, returns_panel, max_lag=max_lag
        )
        hl        = decay_half_life(ic_decay)

        # 换手率：用每期截面归一化权重计算
        positions_series = []
        for cross in alpha_panel:
            total = sum(abs(v) for v in cross)
            if total > 0:
                positions_series.append([v / total for v in cross])
            else:
                positions_series.append([1.0 / N] * N)
        mean_to = compute_mean_turnover(positions_series)

        return ValidationResult(
            factor_name   = factor_name,
            ic            = round(mean_ic, 6),
            rank_ic       = round(mean_ric, 6),
            ic_ir         = round(ic_ir, 6),
            half_life     = round(hl, 2),
            mean_turnover = round(mean_to, 6),
            n_periods     = len(ic_series),
        )
