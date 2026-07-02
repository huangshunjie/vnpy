"""
strategy_lifecycle_ai/utils/evolution_utils.py  (Phase 4)

策略进化工具函数（完整实现）。

实现：
  - mutate_params           参数变异（高斯扰动 + 边界约束）
  - adjust_factor_weights   因子权重调整（绩效导向）
  - recombine_strategies    策略参数重组（加权混合）
  - clone_strategy          强策略克隆（复制 + 变体后缀）
  - select_evolution_type   进化类型决策（基于状态矩阵）
  - compute_evolution_score 进化潜力评分
  - validate_params         参数合法性验证
  - apply_constraints       边界约束

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations
import math
import random
from ..constant import EvolutionType, DecayLevel


# ─────────────────────────────────────────────────────────────────────────────
#  内部工具
# ─────────────────────────────────────────────────────────────────────────────

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _gauss_mutate(value: float, rate: float, lo: float, hi: float) -> float:
    """对单个数值施加高斯扰动，扰动幅度 = rate × 参数绝对值（最小 1e-4）。"""
    std   = max(abs(value) * rate, 1e-4)
    delta = random.gauss(0, std)
    return _clamp(value + delta, lo, hi)


# ─────────────────────────────────────────────────────────────────────────────
#  参数合法性 & 边界约束
# ─────────────────────────────────────────────────────────────────────────────

# 默认参数类型范围（可被外部覆盖）
_PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "lookback":   (5.0,    500.0),
    "threshold":  (0.001,  1.0),
    "stop_loss":  (0.001,  0.5),
    "take_profit": (0.001, 2.0),
    "leverage":   (0.1,    10.0),
    "window":     (5.0,    500.0),
    "fast":       (2.0,    100.0),
    "slow":       (5.0,    500.0),
    "signal":     (2.0,    50.0),
}


def validate_params(params: dict) -> tuple[bool, list[str]]:
    """
    验证参数合法性。

    Returns
    -------
    (is_valid, error_list)
    """
    errors: list[str] = []
    for k, v in params.items():
        if not isinstance(v, (int, float)):
            continue
        if k in _PARAM_BOUNDS:
            lo, hi = _PARAM_BOUNDS[k]
            if not (lo <= float(v) <= hi):
                errors.append(f"{k}={v} out of [{lo}, {hi}]")
    # fast < slow 约束
    if "fast" in params and "slow" in params:
        if float(params["fast"]) >= float(params["slow"]):
            errors.append(
                f"fast({params['fast']}) must be < slow({params['slow']})")
    return (len(errors) == 0, errors)


def apply_constraints(params: dict) -> dict:
    """
    对参数施加边界约束，返回修正后的参数字典。
    """
    result = dict(params)
    for k, v in result.items():
        if not isinstance(v, (int, float)):
            continue
        if k in _PARAM_BOUNDS:
            lo, hi = _PARAM_BOUNDS[k]
            result[k] = type(v)(_clamp(float(v), lo, hi))
    # fast < slow 修正
    if "fast" in result and "slow" in result:
        f = float(result["fast"])
        s = float(result["slow"])
        if f >= s:
            result["slow"] = type(result["slow"])(f * 1.5)
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  参数变异
# ─────────────────────────────────────────────────────────────────────────────

def mutate_params(
    params:        dict,
    mutation_rate: float = 0.1,
    seed:          int | None = None,
    bounds:        dict[str, tuple[float, float]] | None = None,
) -> dict:
    """
    参数变异（高斯扰动）。

    对每个数值型参数施加高斯扰动，扰动幅度 = mutation_rate × |参数值|。
    整数参数在变异后四舍五入并保持整数类型。

    Parameters
    ----------
    params        : 原始参数字典
    mutation_rate : 变异幅度（相对值，默认 10%）
    seed          : 随机种子（None = 不固定）
    bounds        : 自定义边界 {param_name: (lo, hi)}

    Returns
    -------
    dict  变异后的参数（不修改原始字典）
    """
    if seed is not None:
        random.seed(seed)

    effective_bounds = {**_PARAM_BOUNDS, **(bounds or {})}
    result = {}

    for k, v in params.items():
        if not isinstance(v, (int, float)):
            result[k] = v
            continue
        lo, hi = effective_bounds.get(k, (-1e9, 1e9))
        mutated = _gauss_mutate(float(v), mutation_rate, lo, hi)
        result[k] = type(v)(round(mutated) if isinstance(v, int)
                            else round(mutated, 6))

    return apply_constraints(result)


# ─────────────────────────────────────────────────────────────────────────────
#  因子权重调整
# ─────────────────────────────────────────────────────────────────────────────

def adjust_factor_weights(
    weights:     dict[str, float],
    performance: float,
    decay_score: float,
    lr:          float = 0.05,
) -> dict[str, float]:
    """
    绩效导向因子权重调整。

    调整规则：
      - performance > 1.0（Sharpe 良好）→ 强化所有权重（向 1/N 均值靠拢）
      - decay_score > 0.35（衰减中）→ 按权重逆比例收缩低权重、扩大高权重
      - lr：调整步长（默认 5%）

    Parameters
    ----------
    weights     : 因子权重字典 {factor_name: weight}，权重可为任意正实数
    performance : Sharpe Ratio（正 = 良好）
    decay_score : 综合衰减评分 [0,1]
    lr          : 学习率

    Returns
    -------
    dict  调整后的因子权重（自动归一化，总和 = 1.0）
    """
    if not weights:
        return {}

    n     = len(weights)
    total = sum(weights.values())
    if total <= 0:
        return {k: 1.0 / n for k in weights}

    norm = {k: v / total for k, v in weights.items()}
    uniform = 1.0 / n

    result = {}
    for k, w in norm.items():
        if performance > 1.0:
            # 向均匀分布靠拢（平滑，避免过度集中）
            new_w = w + lr * (uniform - w)
        elif decay_score > 0.35:
            # 强化优势因子，弱化劣势因子（放大差异）
            new_w = w + lr * (w - uniform) * decay_score
        else:
            new_w = w

        result[k] = max(1e-4, new_w)

    # 归一化
    total_new = sum(result.values())
    return {k: round(v / total_new, 6) for k, v in result.items()}


# ─────────────────────────────────────────────────────────────────────────────
#  策略参数重组
# ─────────────────────────────────────────────────────────────────────────────

def recombine_strategies(
    parent_a: dict,
    parent_b: dict,
    ratio:    float = 0.5,
    seed:     int | None = None,
) -> dict:
    """
    策略参数重组（加权线性混合）。

    对共有参数进行 ratio 加权混合：
        child[k] = ratio × A[k] + (1-ratio) × B[k]

    非共有参数从比例更高的父本继承。

    Parameters
    ----------
    parent_a : 父本 A 参数字典
    parent_b : 父本 B 参数字典
    ratio    : A 的贡献比例 [0,1]（0.5 = 等比混合）
    seed     : 随机种子

    Returns
    -------
    dict  重组后的子策略参数
    """
    if seed is not None:
        random.seed(seed)

    ratio = _clamp(ratio, 0.0, 1.0)
    all_keys = set(parent_a) | set(parent_b)
    result = {}

    for k in all_keys:
        a_val = parent_a.get(k)
        b_val = parent_b.get(k)

        if a_val is None:
            result[k] = b_val
        elif b_val is None:
            result[k] = a_val
        elif isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
            mixed = ratio * float(a_val) + (1 - ratio) * float(b_val)
            result[k] = (type(a_val)(round(mixed)) if isinstance(a_val, int)
                         else round(mixed, 6))
        else:
            # 非数值：按比例随机继承
            result[k] = a_val if random.random() < ratio else b_val

    return apply_constraints(result)


# ─────────────────────────────────────────────────────────────────────────────
#  强策略克隆
# ─────────────────────────────────────────────────────────────────────────────

def clone_strategy(
    source_params:  dict,
    variant_suffix: str  = "_v1",
    mutation_rate:  float = 0.05,
    seed:           int | None = None,
) -> dict:
    """
    强策略克隆：复制参数 + 轻微变异（生成变体）。

    相比 mutate_params 使用更低的变异率（默认 5%），
    确保变体与父本高度相似但不完全相同。

    Parameters
    ----------
    source_params  : 源策略参数
    variant_suffix : 变体标识后缀（若参数中有 name 字段则追加）
    mutation_rate  : 克隆变异率（默认 5%）
    seed           : 随机种子

    Returns
    -------
    dict  克隆变体参数
    """
    cloned = mutate_params(source_params, mutation_rate, seed)
    if "name" in cloned:
        cloned["name"] = str(cloned["name"]) + variant_suffix
    return cloned


# ─────────────────────────────────────────────────────────────────────────────
#  进化类型决策
# ─────────────────────────────────────────────────────────────────────────────

def select_evolution_type(
    sharpe:          float,
    decay_score:     float,
    live_days:       int,
    decay_level:     "DecayLevel | None" = None,
    has_strong_peers: bool = False,
) -> EvolutionType:
    """
    根据策略状态矩阵选择最优进化类型。

    决策规则（优先级从高到低）：

    1. CLONING
       条件：Sharpe > 2.0 且 decay_score < 0.15 且 live_days > 30
       → 强策略克隆（优秀策略生成变体）

    2. RECOMBINATION
       条件：has_strong_peers = True 且 decay_score > 0.35
       → 与强策略重组（衰减时引入外部优良基因）

    3. WEIGHT_ADJUST
       条件：0.15 < decay_score ≤ 0.55 且 Sharpe > 0
       → 因子权重调整（轻度衰减，优先调整权重）

    4. PARAM_MUTATION
       条件：decay_score > 0.15 或 Sharpe < 1.0
       → 参数变异（通用修复手段）

    5. NONE
       其余情况（策略健康，不需要进化）

    Parameters
    ----------
    sharpe           : 当前 Sharpe Ratio
    decay_score      : 衰减评分 [0,1]
    live_days        : 策略运行天数
    decay_level      : 当前衰减等级（可选，增强决策精度）
    has_strong_peers : 是否存在可供重组的强策略

    Returns
    -------
    EvolutionType
    """
    # CLONING: 优秀策略复制
    if sharpe > 2.0 and decay_score < 0.15 and live_days > 30:
        return EvolutionType.CLONING

    # RECOMBINATION: 衰减时借鉴强策略
    if has_strong_peers and decay_score > 0.35:
        return EvolutionType.RECOMBINATION

    # WEIGHT_ADJUST: 轻度衰减调整权重
    if 0.15 < decay_score <= 0.55 and sharpe > 0:
        return EvolutionType.WEIGHT_ADJUST

    # PARAM_MUTATION: 通用修复
    if decay_score > 0.15 or sharpe < 1.0:
        return EvolutionType.PARAM_MUTATION

    return EvolutionType.NONE


# ─────────────────────────────────────────────────────────────────────────────
#  进化潜力评分
# ─────────────────────────────────────────────────────────────────────────────

def compute_evolution_score(
    sharpe:      float,
    decay_score: float,
    live_days:   int,
    win_rate:    float = 0.5,
) -> float:
    """
    计算策略进化潜力评分 [0, 1]。

    高分 = 进化潜力大（值得投入资源进化）。

    公式：
        base   = clamp((sharpe / 3.0))          # Sharpe 贡献
        decay_boost = clamp(decay_score * 0.5)  # 衰减紧迫性加成
        maturity = clamp(live_days / 60.0)      # 成熟度（数据充分）
        win_r    = clamp((win_rate - 0.3) / 0.4) # 胜率贡献
        score  = 0.3*base + 0.3*decay_boost + 0.2*maturity + 0.2*win_r

    Returns
    -------
    float [0, 1]
    """
    base       = _clamp(sharpe / 3.0, 0.0, 1.0)
    decay_boost = _clamp(decay_score * 0.5, 0.0, 1.0)
    maturity   = _clamp(live_days / 60.0, 0.0, 1.0)
    win_r      = _clamp((win_rate - 0.3) / 0.4, 0.0, 1.0)
    score = 0.3 * base + 0.3 * decay_boost + 0.2 * maturity + 0.2 * win_r
    return round(_clamp(score, 0.0, 1.0), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  进化效果评估
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_evolution_success(
    sharpe_before: float,
    sharpe_after:  float,
    threshold:     float = 0.05,
) -> bool:
    """
    判断进化是否成功（Sharpe 改善超过阈值）。

    Parameters
    ----------
    sharpe_before : 进化前 Sharpe
    sharpe_after  : 进化后 Sharpe（经过验证期）
    threshold     : 成功门槛（默认改善 0.05）

    Returns
    -------
    bool
    """
    return (sharpe_after - sharpe_before) >= threshold


def compute_improvement_rate(
    sharpe_before: float,
    sharpe_after:  float,
) -> float:
    """
    计算进化改善率（百分比）。

    Returns
    -------
    float  改善率，正值 = 改善，负值 = 退化
    """
    if sharpe_before == 0:
        return 0.0
    return round((sharpe_after - sharpe_before) / abs(sharpe_before), 6)
