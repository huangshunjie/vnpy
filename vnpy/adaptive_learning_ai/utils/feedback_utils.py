"""
adaptive_learning_ai/utils/feedback_utils.py  (Phase 2)

反馈处理工具函数。

- 偏差计算 / 严重程度评估 / 信号强度提取
- 各类反馈的标准化处理
- 批次统计聚合
"""
from __future__ import annotations
import math
import uuid
from ..constant import FeedbackType


# ──────────────────────────────────────────────────────────────────────
#  偏差与严重程度
# ──────────────────────────────────────────────────────────────────────

def compute_deviation(decision: float, actual: float) -> tuple[float, float]:
    """
    计算绝对偏差和百分比偏差。
    Returns (deviation, deviation_pct)
    """
    deviation = actual - decision
    if abs(decision) < 1e-9:
        deviation_pct = 0.0 if abs(deviation) < 1e-9 else 1.0
    else:
        deviation_pct = deviation / abs(decision)
    return round(deviation, 8), round(deviation_pct, 6)


def compute_severity(
    deviation_pct: float,
    feedback_type: FeedbackType,
) -> float:
    """
    根据偏差百分比和反馈类型计算严重程度 [0, 1]。

    不同类型有不同的严重程度阈值：
      EXECUTION_SLIPPAGE   : 5bp → 0.5, 20bp → 1.0
      STRATEGY_PERFORMANCE : 5% → 0.5, 20% → 1.0
      PORTFOLIO_DRIFT      : 3% → 0.5, 15% → 1.0
      RISK_VIOLATION       : 直接为 1.0
      ALPHA_DECAY          : 10% → 0.5, 30% → 1.0
      REGIME_MISMATCH      : 固定 0.8
    """
    abs_dev = abs(deviation_pct)

    if feedback_type == FeedbackType.RISK_VIOLATION:
        return 1.0
    if feedback_type == FeedbackType.REGIME_MISMATCH:
        return 0.8

    # (mid_threshold, max_threshold) → linearly mapped to [0,1]
    thresholds = {
        FeedbackType.EXECUTION_SLIPPAGE:   (0.0005, 0.002),   # 5bp, 20bp
        FeedbackType.STRATEGY_PERFORMANCE: (0.05,   0.20),
        FeedbackType.PORTFOLIO_DRIFT:      (0.03,   0.15),
        FeedbackType.ALPHA_DECAY:          (0.10,   0.30),
    }
    lo, hi = thresholds.get(feedback_type, (0.05, 0.20))
    severity = min(abs_dev / max(hi, 1e-9), 1.0)
    return round(max(severity, 0.0), 4)


def compute_signal_strength(
    severity:       float,
    n_recent:       int,
    consistency:    float = 0.5,
) -> float:
    """
    学习信号强度 [0, 1]。

    公式：strength = severity × log_factor × consistency
    log_factor = log(1 + n_recent) / log(1 + 50)  — 样本量衰减
    consistency: 同方向偏差比例 [0, 1]
    """
    log_factor  = math.log1p(min(n_recent, 50)) / math.log1p(50)
    strength    = severity * log_factor * consistency
    return round(min(strength, 1.0), 4)


# ──────────────────────────────────────────────────────────────────────
#  标准化反馈构建
# ──────────────────────────────────────────────────────────────────────

def make_execution_feedback(
    decision_price:  float,
    actual_price:    float,
    symbol:          str   = "",
    strategy_id:     str   = "",
    n_recent:        int   = 1,
) -> dict:
    """构建执行滑点反馈字典（供 FeedbackEngine 接收）。"""
    dev, dev_pct = compute_deviation(decision_price, actual_price)
    severity     = compute_severity(dev_pct, FeedbackType.EXECUTION_SLIPPAGE)
    signal       = compute_signal_strength(severity, n_recent)
    return {
        "record_id":      f"FB_{uuid.uuid4().hex[:8].upper()}",
        "feedback_type":  FeedbackType.EXECUTION_SLIPPAGE,
        "source_module":  "execution_intelligence",
        "decision_value": decision_price,
        "actual_value":   actual_price,
        "deviation":      dev,
        "deviation_pct":  dev_pct,
        "reason":         f"price slippage {dev_pct:.4%}",
        "severity":       severity,
        "signal_strength":signal,
        "symbol":         symbol,
        "strategy_id":    strategy_id,
    }


def make_strategy_feedback(
    expected_return:  float,
    actual_return:    float,
    strategy_id:      str   = "",
    n_recent:         int   = 1,
) -> dict:
    """构建策略绩效反馈字典。"""
    dev, dev_pct = compute_deviation(expected_return, actual_return)
    severity     = compute_severity(dev_pct, FeedbackType.STRATEGY_PERFORMANCE)
    signal       = compute_signal_strength(severity, n_recent)
    return {
        "record_id":      f"FB_{uuid.uuid4().hex[:8].upper()}",
        "feedback_type":  FeedbackType.STRATEGY_PERFORMANCE,
        "source_module":  "strategy_lifecycle",
        "decision_value": expected_return,
        "actual_value":   actual_return,
        "deviation":      dev,
        "deviation_pct":  dev_pct,
        "reason":         f"strategy return deviation {dev_pct:.2%}",
        "severity":       severity,
        "signal_strength":signal,
        "strategy_id":    strategy_id,
    }


def make_portfolio_feedback(
    target_weight:  float,
    actual_weight:  float,
    symbol:         str   = "",
    n_recent:       int   = 1,
) -> dict:
    """构建组合漂移反馈字典。"""
    dev, dev_pct = compute_deviation(target_weight, actual_weight)
    severity     = compute_severity(abs(dev_pct), FeedbackType.PORTFOLIO_DRIFT)
    signal       = compute_signal_strength(severity, n_recent)
    return {
        "record_id":      f"FB_{uuid.uuid4().hex[:8].upper()}",
        "feedback_type":  FeedbackType.PORTFOLIO_DRIFT,
        "source_module":  "portfolio_engine",
        "decision_value": target_weight,
        "actual_value":   actual_weight,
        "deviation":      dev,
        "deviation_pct":  dev_pct,
        "reason":         f"portfolio drift {abs(dev_pct):.2%}",
        "severity":       severity,
        "signal_strength":signal,
        "symbol":         symbol,
    }


def make_risk_feedback(
    risk_limit:    float,
    actual_risk:   float,
    strategy_id:   str   = "",
) -> dict:
    """构建风险违规反馈字典（严重程度固定为 1.0）。"""
    dev, dev_pct = compute_deviation(risk_limit, actual_risk)
    return {
        "record_id":      f"FB_{uuid.uuid4().hex[:8].upper()}",
        "feedback_type":  FeedbackType.RISK_VIOLATION,
        "source_module":  "risk_engine",
        "decision_value": risk_limit,
        "actual_value":   actual_risk,
        "deviation":      dev,
        "deviation_pct":  dev_pct,
        "reason":         f"risk limit breached: {actual_risk:.4f} > {risk_limit:.4f}",
        "severity":       1.0,
        "signal_strength":1.0,
        "strategy_id":    strategy_id,
    }


def make_alpha_feedback(
    expected_ic:  float,
    actual_ic:    float,
    alpha_id:     str   = "",
    n_recent:     int   = 1,
) -> dict:
    """构建 Alpha 衰减反馈字典。"""
    dev, dev_pct = compute_deviation(expected_ic, actual_ic)
    severity     = compute_severity(abs(dev_pct), FeedbackType.ALPHA_DECAY)
    signal       = compute_signal_strength(severity, n_recent, consistency=0.8)
    return {
        "record_id":      f"FB_{uuid.uuid4().hex[:8].upper()}",
        "feedback_type":  FeedbackType.ALPHA_DECAY,
        "source_module":  "alpha_factory",
        "decision_value": expected_ic,
        "actual_value":   actual_ic,
        "deviation":      dev,
        "deviation_pct":  dev_pct,
        "reason":         f"alpha IC decay {dev_pct:.2%}",
        "severity":       severity,
        "signal_strength":signal,
        "strategy_id":    alpha_id,
    }


# ──────────────────────────────────────────────────────────────────────
#  批次统计
# ──────────────────────────────────────────────────────────────────────

def aggregate_feedback(records: list[dict]) -> dict:
    """
    聚合一批反馈记录，返回统计摘要。
    """
    if not records:
        return {"n": 0, "avg_severity": 0.0, "avg_signal": 0.0,
                "type_counts": {}, "high_severity_pct": 0.0}

    n             = len(records)
    avg_sev       = sum(r.get("severity",       0.0) for r in records) / n
    avg_sig       = sum(r.get("signal_strength", 0.0) for r in records) / n
    high_sev_cnt  = sum(1 for r in records if r.get("severity", 0.0) > 0.7)
    counts: dict[str, int] = {}
    for r in records:
        ft = r.get("feedback_type", "")
        k  = ft.value if hasattr(ft, "value") else str(ft)
        counts[k] = counts.get(k, 0) + 1

    return {
        "n":                n,
        "avg_severity":     round(avg_sev,              4),
        "avg_signal":       round(avg_sig,              4),
        "high_severity_pct":round(high_sev_cnt / n,     4),
        "type_counts":      counts,
    }
