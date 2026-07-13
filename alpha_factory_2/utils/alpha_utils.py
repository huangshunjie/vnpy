"""
alpha_factory_2/utils/alpha_utils.py

Alpha 工具函数（Phase 2 升级）。
"""

from __future__ import annotations

import random
import uuid


def build_expression(factors: list[str], weights: list[float]) -> str:
    """
    构建 Alpha 表达式字符串。
    e.g. build_expression(['F1','F2'],[0.3,0.7]) -> '0.3*F1 + 0.7*F2'
    """
    if not factors or not weights:
        return ""
    parts = [f"{round(w, 4)}*{f}" for f, w in zip(factors, weights)]
    return " + ".join(parts)


def normalize_weights(weights: list[float]) -> list[float]:
    """将权重归一化（绝对值之和 = 1）。"""
    total = sum(abs(w) for w in weights)
    if total == 0:
        return weights
    return [w / total for w in weights]


def generate_alpha_id(prefix: str = "ALPHA") -> str:
    """生成唯一 Alpha ID。"""
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


# ─────────────────────────────────────────────────────────────────────────────
#  Phase 2 新增
# ─────────────────────────────────────────────────────────────────────────────

def sample_weights(
    n: int,
    method: str = "uniform",
    allow_negative: bool = False,
    seed: int | None = None,
) -> list[float]:
    """
    随机采样 n 个权重并归一化。

    Parameters
    ----------
    n              : 权重个数
    method         : 采样方法
        "uniform"  — 均匀分布 [0, 1)
        "dirichlet"— Dirichlet 分布（天然归一化，更多样）
        "random_sign"— 符号随机，权重有正有负
    allow_negative : 是否允许负权重（method=uniform 时生效）
    seed           : 随机种子（可复现）

    Returns
    -------
    list[float]  长度为 n，绝对值归一化后的权重
    """
    if n <= 0:
        return []
    rng = random.Random(seed)

    if method == "dirichlet":
        # 用 Gamma 分布模拟 Dirichlet
        gammas = [-rng.expovariate(1.0) for _ in range(n)]
        gammas = [abs(g) + 1e-9 for g in gammas]   # all positive
        total  = sum(gammas)
        return [g / total for g in gammas]

    elif method == "random_sign":
        raw = [rng.uniform(0.05, 1.0) for _ in range(n)]
        signs = [rng.choice([-1, 1]) for _ in range(n)]
        raw   = [r * s for r, s in zip(raw, signs)]
        return normalize_weights(raw)

    else:  # uniform
        if allow_negative:
            raw = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        else:
            raw = [rng.uniform(0.05, 1.0) for _ in range(n)]
        return normalize_weights(raw)


def validate_expression(expression: str, factors: list[str]) -> bool:
    """
    验证 Alpha 表达式是否合法。

    规则：
      - 表达式非空
      - 每个因子名称均出现在表达式中
      - 不含危险字符

    Returns
    -------
    bool  True = 合法
    """
    if not expression or not expression.strip():
        return False
    # 禁止危险字符
    for bad in (";", "import", "exec", "eval", "__"):
        if bad in expression:
            return False
    # 每个因子均应出现
    for f in factors:
        if f not in expression:
            return False
    return True


def select_random_factors(
    available: list[str],
    n: int,
    seed: int | None = None,
) -> list[str]:
    """
    从可用因子列表中随机选取 n 个（不重复）。

    Parameters
    ----------
    available : 可用因子名称列表
    n         : 选取数量
    seed      : 随机种子
    """
    if not available or n <= 0:
        return []
    rng = random.Random(seed)
    n   = min(n, len(available))
    return rng.sample(available, n)
