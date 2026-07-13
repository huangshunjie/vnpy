"""
adaptive_learning_ai/utils/adaptation_utils.py  (Phase 4)

自适应参数更新工具函数。

- 三种自适应规则：performance_driven / regime_aware / decay_triggered
- 三种更新策略：replace / blend / incremental
- 从 LearningPattern 生成 AdaptationProposal
"""
from __future__ import annotations
import uuid
from ..constant import AdaptationTarget, UpdateStrategy, FeedbackType
from ..model.learning_model  import LearningPattern
from ..model.adaptation_model import AdaptationProposal

# ── 规则选择 ──────────────────────────────────────────────────────────

def select_rule(
    target:  AdaptationTarget,
    pattern: LearningPattern,
) -> str:
    """
    根据目标类型和模式属性选择自适应规则。

    performance_driven : 策略绩效/Alpha衰减 触发
    regime_aware       : 状态切换触发
    decay_triggered    : 执行效率/组合漂移 触发
    """
    if pattern.feedback_type in (
        FeedbackType.STRATEGY_PERFORMANCE,
        FeedbackType.ALPHA_DECAY,
    ):
        return "performance_driven"
    if pattern.feedback_type == FeedbackType.REGIME_MISMATCH:
        return "regime_aware"
    return "decay_triggered"


def select_update_strategy(
    target:     AdaptationTarget,
    urgency:    float,
    confidence: float,
) -> UpdateStrategy:
    """
    根据目标类型、紧迫度和置信度选择更新策略。

    高紧迫度(>0.8) + 高置信度(>0.7) → REPLACE
    中等置信度(>0.5)                  → BLEND
    低置信度                          → INCREMENTAL
    风险阈值目标                       → 强制 BLEND（保守）
    """
    if target == AdaptationTarget.RISK_THRESHOLDS:
        return UpdateStrategy.BLEND
    if urgency > 0.8 and confidence > 0.7:
        return UpdateStrategy.REPLACE
    if confidence > 0.5:
        return UpdateStrategy.BLEND
    return UpdateStrategy.INCREMENTAL


def select_priority(urgency: float, confidence: float) -> int:
    """1=高, 2=中, 3=低"""
    if urgency >= 0.8 or confidence >= 0.85:
        return 1
    if urgency >= 0.5 or confidence >= 0.6:
        return 2
    return 3


# ── 更新量计算 ────────────────────────────────────────────────────────

def compute_new_value(
    current:         float,
    delta_pct:       float,
    strategy:        UpdateStrategy,
    blend_factor:    float = 0.3,
    increment_step:  float = 0.01,
) -> tuple[float, float]:
    """
    根据更新策略计算新值和实际 delta。

    Returns (new_value, actual_delta)
    """
    if strategy == UpdateStrategy.REPLACE:
        new_val = current * (1.0 + delta_pct)
    elif strategy == UpdateStrategy.BLEND:
        raw     = current * (1.0 + delta_pct)
        new_val = current + blend_factor * (raw - current)
    elif strategy == UpdateStrategy.INCREMENTAL:
        sign    = 1 if delta_pct >= 0 else -1
        new_val = current + sign * increment_step
    else:  # ROLLBACK — 保持不变（由 UpdateEngine 处理实际回滚）
        new_val = current

    actual_delta = new_val - current
    return round(new_val, 8), round(actual_delta, 8)


# ── 核心：LearningPattern → AdaptationProposal ─────────────────────

def pattern_to_proposal(
    pattern:       LearningPattern,
    current_value: float = 0.0,
    entity_id:     str   = "",
    dimension:     str   = "",
    blend_factor:  float = 0.3,
) -> AdaptationProposal:
    """
    将 LearningPattern 转化为 AdaptationProposal。
    """
    target   = pattern.target
    rule     = select_rule(target, pattern)
    strategy = select_update_strategy(
        target, pattern.avg_urgency, pattern.avg_confidence)
    priority = select_priority(pattern.avg_urgency, pattern.avg_confidence)

    new_val, actual_delta = compute_new_value(
        current_value, pattern.recommended_delta, strategy, blend_factor)

    delta_pct = (actual_delta / abs(current_value)
                 if abs(current_value) > 1e-9 else 0.0)

    eid = entity_id or (pattern.entity_ids[0] if pattern.entity_ids else "")

    return AdaptationProposal(
        proposal_id     = f"PROP_{uuid.uuid4().hex[:8].upper()}",
        target          = target,
        update_strategy = strategy,
        source_pattern  = pattern.pattern_id,
        entity_id       = eid,
        dimension       = dimension or target.value,
        current_value   = current_value,
        proposed_value  = new_val,
        delta           = actual_delta,
        delta_pct       = round(delta_pct, 6),
        confidence      = pattern.avg_confidence,
        urgency         = pattern.avg_urgency,
        priority        = priority,
        rule            = rule,
        feedback_type   = pattern.feedback_type,
        approved        = False,
    )


def patterns_to_proposals(
    patterns:       list[LearningPattern],
    current_values: dict[str, float] | None = None,
    blend_factor:   float = 0.3,
) -> list[AdaptationProposal]:
    """
    批量将 LearningPattern 列表转化为 AdaptationProposal 列表。

    current_values: {entity_id: current_value}  可选，默认使用 1.0
    """
    cv = current_values or {}
    proposals = []
    for p in patterns:
        eid  = p.entity_ids[0] if p.entity_ids else p.target.value
        base = cv.get(eid, 1.0)
        proposals.append(
            pattern_to_proposal(p, base, eid, p.target.value, blend_factor))
    proposals.sort(key=lambda x: x.priority)
    return proposals


# ── 约束检查 ──────────────────────────────────────────────────────────

MAX_SINGLE_DELTA = 0.20   # 单次最大调整 20%
MIN_VALUE        = 0.001  # 参数最小值（防止归零）


def apply_constraints(proposal: AdaptationProposal) -> AdaptationProposal:
    """
    对 proposal 施加安全约束：
    - 单次调整上限 MAX_SINGLE_DELTA
    - 参数最小值 MIN_VALUE
    """
    cur  = proposal.current_value
    prop = proposal.proposed_value

    # 限制调整幅度
    if cur != 0:
        actual_pct = (prop - cur) / abs(cur)
        if abs(actual_pct) > MAX_SINGLE_DELTA:
            capped = cur * (1.0 + MAX_SINGLE_DELTA * (1 if actual_pct > 0 else -1))
            proposal.proposed_value = round(capped, 8)
            proposal.delta          = round(capped - cur, 8)
            proposal.delta_pct      = round(MAX_SINGLE_DELTA * (
                1 if actual_pct > 0 else -1), 6)

    # 确保不低于最小值
    if proposal.proposed_value < MIN_VALUE:
        proposal.proposed_value = MIN_VALUE
        proposal.delta          = round(MIN_VALUE - cur, 8)

    return proposal
