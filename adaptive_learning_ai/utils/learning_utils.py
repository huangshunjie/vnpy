"""
adaptive_learning_ai/utils/learning_utils.py  (Phase 3)

学习工具函数。

- 从反馈记录提取调整信号
- 信号聚合 → 模式识别
- 置信度 / 紧迫度 / 学习速度计算
"""
from __future__ import annotations
import math
import uuid
from ..constant import FeedbackType, AdaptationTarget
from ..model.feedback_model import FeedbackRecord
from ..model.learning_model  import LearningSignal, LearningPattern


# ── 反馈类型 → 自适应目标 映射 ─────────────────────────────────────────
_FEEDBACK_TO_TARGET: dict[FeedbackType, AdaptationTarget] = {
    FeedbackType.EXECUTION_SLIPPAGE:   AdaptationTarget.EXECUTION_PARAMS,
    FeedbackType.STRATEGY_PERFORMANCE: AdaptationTarget.STRATEGY_ALLOCATION,
    FeedbackType.PORTFOLIO_DRIFT:      AdaptationTarget.PORTFOLIO_WEIGHTS,
    FeedbackType.RISK_VIOLATION:       AdaptationTarget.RISK_THRESHOLDS,
    FeedbackType.ALPHA_DECAY:          AdaptationTarget.ALPHA_WEIGHTS,
    FeedbackType.REGIME_MISMATCH:      AdaptationTarget.STRATEGY_ALLOCATION,
}

# ── 调整方向规则（偏差为负 → 下调；偏差为正 → 上调，按类型区分） ─────────
def _direction(deviation_pct: float, fb_type: FeedbackType) -> int:
    """
    +1 建议上调目标参数
    -1 建议下调目标参数
     0 中性
    """
    if abs(deviation_pct) < 1e-6:
        return 0
    # 对于执行滑点 / 风险违规 / Alpha衰减：实际 > 预期 → 下调
    downward_types = {
        FeedbackType.EXECUTION_SLIPPAGE,
        FeedbackType.RISK_VIOLATION,
        FeedbackType.ALPHA_DECAY,
    }
    if fb_type in downward_types:
        return -1 if deviation_pct > 0 else +1
    # 对于策略绩效：实际 < 预期（负偏差）→ 下调
    if fb_type == FeedbackType.STRATEGY_PERFORMANCE:
        return -1 if deviation_pct < 0 else +1
    # 组合漂移 / 状态错配：按绝对方向
    return +1 if deviation_pct > 0 else -1


# ── 核心：从单条反馈记录提取学习信号 ──────────────────────────────────
def extract_signal(record: FeedbackRecord) -> LearningSignal:
    """
    从 FeedbackRecord 提取 LearningSignal。

    调整量公式：
      adjustment_pct = -direction × severity × signal_strength × scaling_factor
    """
    ft      = record.feedback_type
    target  = _FEEDBACK_TO_TARGET.get(ft, AdaptationTarget.EXECUTION_PARAMS)
    direct  = _direction(record.deviation_pct, ft)

    # 按目标类型设置缩放系数
    scale_map = {
        AdaptationTarget.EXECUTION_PARAMS:   0.02,   # 执行参数微调
        AdaptationTarget.STRATEGY_ALLOCATION:0.05,   # 策略分配中等调整
        AdaptationTarget.PORTFOLIO_WEIGHTS:  0.03,
        AdaptationTarget.RISK_THRESHOLDS:    0.10,   # 风险阈值较大调整
        AdaptationTarget.ALPHA_WEIGHTS:      0.04,
    }
    scale = scale_map.get(target, 0.03)

    adj_pct = -direct * record.severity * record.signal_strength * scale
    adj_val = adj_pct  # 对于权重类目标，调整量即百分比

    confidence = min(record.signal_strength * (1.0 + record.severity * 0.5), 1.0)
    urgency    = record.severity * (1.0 if ft == FeedbackType.RISK_VIOLATION else 0.7)

    return LearningSignal(
        signal_id          = f"SIG_{uuid.uuid4().hex[:8].upper()}",
        source_feedback_id = record.record_id,
        feedback_type      = ft,
        target             = target,
        adjustment_value   = round(adj_val, 8),
        adjustment_pct     = round(adj_pct, 8),
        confidence         = round(min(confidence, 1.0), 4),
        urgency            = round(min(urgency,    1.0), 4),
        entity_id          = record.strategy_id or record.symbol,
        dimension          = target.value,
        direction          = direct,
        reason             = record.reason,
    )


def extract_signals(records: list[FeedbackRecord]) -> list[LearningSignal]:
    """批量提取信号。"""
    return [extract_signal(r) for r in records]


# ── 信号聚合 → 模式识别 ───────────────────────────────────────────────
def aggregate_signals(
    signals:    list[LearningSignal],
    min_count:  int   = 2,
    min_consistency: float = 0.6,
) -> list[LearningPattern]:
    """
    将同类信号（同 feedback_type × target）聚合为 LearningPattern。

    min_count:       至少 N 条信号才形成模式
    min_consistency: 同向信号比例下限
    """
    # 分组
    groups: dict[tuple, list[LearningSignal]] = {}
    for s in signals:
        key = (s.feedback_type, s.target)
        groups.setdefault(key, []).append(s)

    patterns: list[LearningPattern] = []
    for (ft, tgt), grp in groups.items():
        if len(grp) < min_count:
            continue

        n         = len(grp)
        avg_adj   = sum(s.adjustment_pct  for s in grp) / n
        avg_conf  = sum(s.confidence      for s in grp) / n
        avg_urg   = sum(s.urgency         for s in grp) / n

        # 一致性：同向信号比例
        dominant  = max(
            sum(1 for s in grp if s.direction > 0),
            sum(1 for s in grp if s.direction < 0),
        )
        consistency = dominant / n if n > 0 else 0.0
        if consistency < min_consistency:
            continue

        # 模式强度
        log_boost = math.log1p(n) / math.log1p(20)
        strength  = avg_conf * consistency * min(log_boost, 1.0)

        # 最终建议调整量（按置信度加权平均）
        total_conf = sum(s.confidence for s in grp) or 1.0
        rec_delta  = sum(s.adjustment_pct * s.confidence for s in grp) / total_conf

        entity_ids = list({s.entity_id for s in grp if s.entity_id})

        patterns.append(LearningPattern(
            pattern_id        = f"PAT_{uuid.uuid4().hex[:6].upper()}",
            feedback_type     = ft,
            target            = tgt,
            n_signals         = n,
            avg_adjustment    = round(avg_adj,    6),
            avg_confidence    = round(avg_conf,   4),
            avg_urgency       = round(avg_urg,    4),
            consistency       = round(consistency,4),
            pattern_strength  = round(strength,  4),
            recommended_delta = round(rec_delta,  6),
            entity_ids        = entity_ids,
        ))

    patterns.sort(key=lambda p: p.pattern_strength, reverse=True)
    return patterns


# ── 学习速度 ──────────────────────────────────────────────────────────
def compute_learning_velocity(
    cycle_signal_counts: list[int],
    window: int = 5,
) -> float:
    """
    学习速度 [0, 1]。

    基于最近 window 个周期的信号数量趋势。
    上升趋势 → 接近 1.0；下降趋势 → 接近 0.0；平稳 → 0.5。
    """
    if len(cycle_signal_counts) < 2:
        return 0.5
    recent = cycle_signal_counts[-window:]
    n = len(recent)
    if n < 2:
        return 0.5
    # 线性回归斜率（归一化）
    mean_x = (n - 1) / 2
    mean_y = sum(recent) / n
    num    = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(recent))
    den    = sum((i - mean_x) ** 2 for i in range(n))
    if den < 1e-9:
        return 0.5
    slope  = num / den
    max_y  = max(recent) or 1.0
    norm   = slope / max_y        # 归一化斜率
    return round(min(max(0.5 + norm * 2, 0.0), 1.0), 4)


# ── 高置信度信号过滤 ───────────────────────────────────────────────────
def filter_high_confidence(
    signals:   list[LearningSignal],
    threshold: float = 0.7,
) -> list[LearningSignal]:
    return [s for s in signals if s.confidence >= threshold]


def top_urgent_signals(
    signals:   list[LearningSignal],
    n:         int = 5,
) -> list[LearningSignal]:
    return sorted(signals, key=lambda s: s.urgency, reverse=True)[:n]
