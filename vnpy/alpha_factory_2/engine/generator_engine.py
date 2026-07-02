"""
alpha_factory_2/engine/generator_engine.py  (Phase 2)

GeneratorEngine — Alpha 生成引擎。

支持三种生成模式：
  1. LINEAR_COMBO  — 多因子线性组合（指定权重）
  2. WEIGHTED      — 因子加权组合（Dirichlet 权重采样）
  3. RANDOM        — 随机组合生成（因子随机选取 + 随机权重）

❌ 不执行任何交易逻辑
❌ 不访问交易所 API
✔  仅读取 FactorLoader 提供的因子数据
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Callable

from ..constant import AlphaType
from ..model.alpha_model import AlphaSignal
from ..datasource.factor_loader import FactorLoader, BUILTIN_FACTORS
from ..utils.alpha_utils import (
    build_expression,
    normalize_weights,
    generate_alpha_id,
    sample_weights,
    select_random_factors,
    validate_expression,
)


class GeneratorEngine:
    """
    Alpha 生成引擎（Phase 2）。

    使用方式：
        ge = GeneratorEngine(factor_loader=FactorLoader())
        # 线性组合（指定因子和权重）
        alpha = ge.generate(
            factors=['MOM_5D', 'REV_1D'],
            weights=[0.6, 0.4],
            alpha_type=AlphaType.LINEAR_COMBO,
        )
        # 随机组合
        alphas = ge.batch_generate(n=10, factors=BUILTIN_FACTORS[:10])
    """

    def __init__(
        self,
        factor_loader: FactorLoader | None = None,
        log_fn:        Callable | None     = None,
        seed:          int | None          = None,
    ) -> None:
        self._loader  = factor_loader or FactorLoader()
        self._log     = log_fn or (lambda msg: None)
        self._seed    = seed
        self._rng     = random.Random(seed)
        self._count   = 0     # 累计生成数量

    # ------------------------------------------------------------------ #
    #  单个生成
    # ------------------------------------------------------------------ #

    def generate(
        self,
        factors:        list[str] | None  = None,
        weights:        list[float] | None = None,
        alpha_type:     AlphaType          = AlphaType.LINEAR_COMBO,
        weight_method:  str                = "uniform",
        allow_negative: bool               = False,
        seed:           int | None         = None,
        **kwargs,
    ) -> AlphaSignal:
        """
        生成单个 Alpha 信号。

        Parameters
        ----------
        factors        : 因子名称列表（None 时随机选取 3-6 个）
        weights        : 权重列表（None 时自动采样）
        alpha_type     : 生成类型
        weight_method  : 权重采样方法（"uniform"/"dirichlet"/"random_sign"）
        allow_negative : 是否允许负权重
        seed           : 本次生成的随机种子（可复现）

        Returns
        -------
        AlphaSignal  已生成的 Alpha（status = GENERATED）
        """
        effective_seed = seed if seed is not None else (
            self._rng.randint(0, 2**31) if self._seed is None else self._seed + self._count
        )

        # 确定因子列表
        available = self._loader.list_available_factors()
        if not factors:
            n_factors  = random.Random(effective_seed).randint(3, min(6, len(available)))
            factors    = select_random_factors(available, n_factors, seed=effective_seed)
        else:
            # 只保留可用因子
            factors = [f for f in factors if f in available or True]  # Phase 2: 允许任意

        if not factors:
            self._log("[GeneratorEngine] No factors available")
            factors = ["F_PLACEHOLDER"]

        # 确定权重
        if weights is None or len(weights) != len(factors):
            if alpha_type == AlphaType.WEIGHTED:
                w_method = "dirichlet"
            elif alpha_type == AlphaType.RANDOM:
                w_method = "random_sign" if allow_negative else "uniform"
            else:
                w_method = weight_method
            weights = sample_weights(
                n              = len(factors),
                method         = w_method,
                allow_negative = allow_negative,
                seed           = effective_seed,
            )
        else:
            weights = normalize_weights(weights)

        # 构建表达式
        expression = build_expression(factors, weights)

        # 创建 AlphaSignal
        alpha_id = generate_alpha_id()
        alpha    = AlphaSignal(
            alpha_id   = alpha_id,
            alpha_type = alpha_type,
            factors    = list(factors),
            weights    = [round(w, 6) for w in weights],
            expression = expression,
            meta       = {
                "seed":           effective_seed,
                "weight_method":  w_method if weights is None else weight_method,
                "generated_by":   "GeneratorEngine",
            },
        )

        self._count += 1
        self._log(
            f"[GeneratorEngine] generated {alpha_id}"
            f"  type={alpha_type.value}"
            f"  factors={len(factors)}"
            f"  expr={expression[:60]}{'...' if len(expression) > 60 else ''}"
        )
        return alpha

    # ------------------------------------------------------------------ #
    #  批量生成
    # ------------------------------------------------------------------ #

    def batch_generate(
        self,
        n:              int,
        factors:        list[str] | None = None,
        alpha_type:     AlphaType        = AlphaType.RANDOM,
        weight_method:  str              = "dirichlet",
        allow_negative: bool             = False,
        min_factors:    int              = 2,
        max_factors:    int              = 6,
    ) -> list[AlphaSignal]:
        """
        批量生成 n 个 Alpha 候选（多样性生成）。

        每个 Alpha 从 factors 中随机选取 [min_factors, max_factors] 个，
        并使用指定采样方法生成权重。

        Parameters
        ----------
        n            : 生成数量
        factors      : 候选因子池（None 时使用全部内置因子）
        alpha_type   : 生成类型（默认 RANDOM）
        weight_method: 权重采样方法
        allow_negative: 是否允许负权重
        min_factors  : 每个 Alpha 最少使用的因子数
        max_factors  : 每个 Alpha 最多使用的因子数

        Returns
        -------
        list[AlphaSignal]  长度为 n 的 Alpha 列表
        """
        if n <= 0:
            return []

        available    = factors or self._loader.list_available_factors()
        max_factors  = min(max_factors, len(available))
        min_factors  = min(min_factors, max_factors)
        results: list[AlphaSignal] = []

        for i in range(n):
            batch_seed  = (self._seed or 0) + self._count + i
            n_factors   = self._rng.randint(min_factors, max_factors)
            sel_factors = select_random_factors(available, n_factors, seed=batch_seed)

            alpha = self.generate(
                factors        = sel_factors,
                weights        = None,
                alpha_type     = alpha_type,
                weight_method  = weight_method,
                allow_negative = allow_negative,
                seed           = batch_seed,
            )
            results.append(alpha)

        self._log(
            f"[GeneratorEngine] batch_generate: {n} alphas"
            f"  type={alpha_type.value}  method={weight_method}"
        )
        return results

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def count(self) -> int:
        return self._count

    def available_factors(self) -> list[str]:
        return self._loader.list_available_factors()

    def summary(self) -> dict:
        return {
            "count":             self._count,
            "available_factors": len(self._loader.list_available_factors()),
        }
