"""
data_intelligence_ai/utils/fusion_utils.py  (Phase 4)

数据融合工具函数。

- 4种融合模式：weighted_average / latest_wins / consensus / regime_aware
- 归一化、置信度计算
- 各维度融合输入构建
"""
from __future__ import annotations
import uuid
from datetime import datetime
from ..constant import FusionMode, DataType
from ..model.fusion_model import FusionInput, FusedState


# ── 归一化 ────────────────────────────────────────────────────────────

def normalize_score(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """将任意值线性归一化到 [0, 1]。"""
    if hi <= lo:
        return 0.5
    return round(min(max((value - lo) / (hi - lo), 0.0), 1.0), 6)


def clamp01(v: float) -> float:
    return round(min(max(v, 0.0), 1.0), 6)


# ── FusionInput 构建 ──────────────────────────────────────────────────

def make_market_input(
    symbol:     str,
    price_ret:  float,     # 近期收益率
    vol:        float,     # 波动率
    quality:    float = 1.0,
) -> FusionInput:
    """
    行情融合输入。
    score = 0.5 + clamp(price_ret / (2 * vol), -0.5, 0.5)
    → 正收益 → score > 0.5；负收益 → score < 0.5
    """
    denom = max(2.0 * vol, 1e-6)
    score = clamp01(0.5 + max(min(price_ret / denom, 0.5), -0.5))
    return FusionInput(
        source     = DataType.MARKET,
        symbol     = symbol,
        score      = score,
        confidence = clamp01(quality),
        weight     = 1.0,
    )


def make_alpha_input(
    symbol:    str,
    ic_score:  float,      # IC 值 [-1, 1]
    quality:   float = 1.0,
) -> FusionInput:
    """Alpha 融合输入：IC → [0,1]"""
    score = clamp01(0.5 + ic_score * 0.5)
    return FusionInput(
        source     = DataType.ALPHA,
        symbol     = symbol,
        score      = score,
        confidence = clamp01(quality),
        weight     = 1.0,
    )


def make_portfolio_input(
    symbol:      str,
    weight_pct:  float,    # 当前权重 [0, 1]
    target_pct:  float,    # 目标权重 [0, 1]
    quality:     float = 1.0,
) -> FusionInput:
    """
    组合融合输入。
    drift = |current - target|, score = 1 - clamp(drift / 0.2, 0, 1)
    → 权重接近目标 → score 高
    """
    drift = abs(weight_pct - target_pct)
    score = clamp01(1.0 - min(drift / 0.2, 1.0))
    return FusionInput(
        source     = DataType.PORTFOLIO,
        symbol     = symbol,
        score      = score,
        confidence = clamp01(quality),
        weight     = 1.0,
    )


def make_execution_input(
    symbol:      str,
    fill_rate:   float,    # [0, 1]
    slippage_bps:float,    # 滑点 bps
    quality:     float = 1.0,
) -> FusionInput:
    """
    执行融合输入。
    score = fill_rate * (1 - clamp(slippage_bps / 50, 0, 1))
    """
    slippage_pen = min(slippage_bps / 50.0, 1.0)
    score = clamp01(fill_rate * (1.0 - slippage_pen))
    return FusionInput(
        source     = DataType.EXECUTION,
        symbol     = symbol,
        score      = score,
        confidence = clamp01(quality),
        weight     = 1.0,
    )


def make_risk_input(
    symbol:      str,
    utilization: float,    # 风险使用率 [0, 1]  1=触发上限
    quality:     float = 1.0,
) -> FusionInput:
    """
    风险融合输入。
    score = 1 - utilization   → 使用率越低越好
    """
    score = clamp01(1.0 - utilization)
    return FusionInput(
        source     = DataType.RISK,
        symbol     = symbol,
        score      = score,
        confidence = clamp01(quality),
        weight     = 1.0,
    )


def make_regime_input(
    symbol:     str,
    bull_prob:  float,     # 牛市概率 [0, 1]
    quality:    float = 1.0,
) -> FusionInput:
    """市场状态融合输入：bull_prob 直接作为 score。"""
    return FusionInput(
        source     = DataType.REGIME,
        symbol     = symbol,
        score      = clamp01(bull_prob),
        confidence = clamp01(quality),
        weight     = 1.0,
    )


# ── 4种融合模式 ───────────────────────────────────────────────────────

def fuse_weighted_average(inputs: list[FusionInput]) -> tuple[float, float]:
    """
    加权平均融合。
    effective_weight = weight × confidence
    unified = Σ(score × eff_w) / Σ(eff_w)
    """
    if not inputs:
        return 0.5, 0.0
    total_w = sum(i.weight * i.confidence for i in inputs)
    if total_w < 1e-10:
        return 0.5, 0.0
    unified = sum(i.score * i.weight * i.confidence for i in inputs) / total_w
    avg_conf = sum(i.confidence for i in inputs) / len(inputs)
    return round(clamp01(unified), 4), round(avg_conf, 4)


def fuse_latest_wins(inputs: list[FusionInput]) -> tuple[float, float]:
    """
    最新数据优先：选择时间戳最新的输入作为主要信号，其余以较低权重混合。
    主信号权重 0.6，其余均分 0.4。
    """
    if not inputs:
        return 0.5, 0.0
    latest = max(inputs, key=lambda i: i.timestamp)
    others = [i for i in inputs if i is not latest]
    if not others:
        return round(clamp01(latest.score), 4), round(latest.confidence, 4)
    others_avg = sum(i.score * i.confidence for i in others) / max(
        sum(i.confidence for i in others), 1e-10)
    unified  = 0.6 * latest.score + 0.4 * others_avg
    avg_conf = (latest.confidence + sum(i.confidence for i in others) / len(others)) / 2
    return round(clamp01(unified), 4), round(avg_conf, 4)


def fuse_consensus(inputs: list[FusionInput]) -> tuple[float, float]:
    """
    共识融合：仅当多数信号方向一致时给予高置信度结果。
    bullish  = score > 0.5
    bearish  = score < 0.5
    consensus_ratio = max(bullish, bearish) / n
    confidence_mult = 2 × consensus_ratio - 1   (0.5→0, 1.0→1.0)
    """
    if not inputs:
        return 0.5, 0.0
    bullish  = sum(1 for i in inputs if i.score > 0.5)
    bearish  = len(inputs) - bullish
    consensus_ratio = max(bullish, bearish) / len(inputs)
    conf_mult = max(2.0 * consensus_ratio - 1.0, 0.0)

    weighted, base_conf = fuse_weighted_average(inputs)
    return round(weighted, 4), round(base_conf * conf_mult, 4)


def fuse_regime_aware(
    inputs:      list[FusionInput],
    regime_prob: float = 0.5,   # bull_prob from regime engine
) -> tuple[float, float]:
    """
    状态感知融合：根据 bull_prob 动态调整各源权重。
    bull市  → 上调 alpha/portfolio 权重，下调 risk 权重
    bear市  → 上调 risk 权重，下调 alpha 权重
    """
    bull = clamp01(regime_prob)
    bear = 1.0 - bull

    source_boost = {
        DataType.MARKET:    1.0,
        DataType.ALPHA:     0.5 + bull,
        DataType.PORTFOLIO: 0.5 + bull * 0.5,
        DataType.EXECUTION: 1.0,
        DataType.RISK:      0.5 + bear,
        DataType.REGIME:    0.3,   # regime信号本身降权，避免循环
    }
    adjusted = []
    for inp in inputs:
        boost = source_boost.get(inp.source, 1.0)
        adjusted.append(FusionInput(
            source     = inp.source,
            symbol     = inp.symbol,
            score      = inp.score,
            confidence = inp.confidence,
            weight     = inp.weight * boost,
            timestamp  = inp.timestamp,
        ))
    return fuse_weighted_average(adjusted)


# ── 主融合入口 ────────────────────────────────────────────────────────

def fuse(
    inputs:      list[FusionInput],
    mode:        FusionMode = FusionMode.WEIGHTED_AVERAGE,
    symbol:      str        = "",
    regime_prob: float      = 0.5,
) -> FusedState:
    """
    执行一次完整融合，返回 FusedState。
    """
    if not inputs:
        return FusedState(
            fusion_id    = f"FU_{uuid.uuid4().hex[:8].upper()}",
            mode         = mode,
            symbol       = symbol,
            unified_score= 0.5,
            confidence   = 0.0,
            n_sources    = 0,
        )

    # 按 source 取分数（多个同类取均值）
    source_scores: dict[DataType, list[float]] = {}
    for inp in inputs:
        source_scores.setdefault(inp.source, []).append(inp.score)
    avg_source: dict[DataType, float] = {
        s: sum(vs) / len(vs) for s, vs in source_scores.items()
    }

    # 融合
    if mode == FusionMode.WEIGHTED_AVERAGE:
        unified, conf = fuse_weighted_average(inputs)
    elif mode == FusionMode.LATEST_WINS:
        unified, conf = fuse_latest_wins(inputs)
    elif mode == FusionMode.CONSENSUS:
        unified, conf = fuse_consensus(inputs)
    elif mode == FusionMode.REGIME_AWARE:
        unified, conf = fuse_regime_aware(inputs, regime_prob)
    else:
        unified, conf = fuse_weighted_average(inputs)

    weights_used = {
        i.source.value: round(i.weight * i.confidence, 4)
        for i in inputs
    }

    return FusedState(
        fusion_id       = f"FU_{uuid.uuid4().hex[:8].upper()}",
        mode            = mode,
        symbol          = symbol,
        timestamp       = datetime.now(),
        market_score    = avg_source.get(DataType.MARKET,    0.5),
        alpha_score     = avg_source.get(DataType.ALPHA,     0.5),
        portfolio_score = avg_source.get(DataType.PORTFOLIO, 0.5),
        execution_score = avg_source.get(DataType.EXECUTION, 0.5),
        risk_score      = avg_source.get(DataType.RISK,      0.5),
        regime_score    = avg_source.get(DataType.REGIME,    0.5),
        unified_score   = unified,
        confidence      = conf,
        n_sources       = len(set(i.source for i in inputs)),
        weights_used    = weights_used,
        sources_present = [i.source.value for i in inputs],
    )
