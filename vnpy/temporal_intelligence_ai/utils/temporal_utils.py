"""
temporal_intelligence_ai/utils/temporal_utils.py

时间验证工具函数。

核心职责：
  1. 预测误差计算（MAE / RMSE / MAPE / Bias / Direction Accuracy）
  2. Alpha 衰减对齐验证（验证衰减预测与实际 Alpha 失效的对齐程度）
  3. 记忆有效性验证（验证 ACF 结构预测的信号持续性）
  4. Temporal Health Score 综合评分

所有函数只使用历史已实现数据，无前瞻偏差。
"""
from __future__ import annotations

import math
from typing import List, Optional

from ..model.validation_model import (
    ValidationRecord,
    ValidationResult,
    ValidationMetrics,
)


# ── 误差计算 ─────────────────────────────────────────────────────────

def compute_errors(
    records: List[ValidationRecord],
) -> List[ValidationResult]:
    """
    对所有已实现记录计算误差指标。

    只处理 is_realized=True 的记录，跳过未到期记录。
    """
    results: List[ValidationResult] = []
    for rec in records:
        if not rec.is_realized or rec.realized is None:
            continue
        err    = rec.realized - rec.predicted
        abs_e  = abs(err)
        sq_e   = err ** 2
        pct_e  = (abs_e / abs(rec.predicted)) if rec.predicted != 0 else 0.0
        d_hit  = (rec.predicted >= 0) == (rec.realized >= 0)
        results.append(ValidationResult(
            record_id    = rec.record_id,
            error        = round(err, 8),
            abs_error    = round(abs_e, 8),
            sq_error     = round(sq_e, 8),
            pct_error    = round(pct_e, 6),
            direction_hit = d_hit,
        ))
    return results


def compute_mae(results: List[ValidationResult]) -> float:
    if not results:
        return 0.0
    return sum(r.abs_error for r in results) / len(results)


def compute_rmse(results: List[ValidationResult]) -> float:
    if not results:
        return 0.0
    return math.sqrt(sum(r.sq_error for r in results) / len(results))


def compute_mape(results: List[ValidationResult]) -> float:
    valid = [r for r in results if r.pct_error < 1e6]
    if not valid:
        return 0.0
    return sum(r.pct_error for r in valid) / len(valid)


def compute_bias(results: List[ValidationResult]) -> float:
    """系统性偏差（正 = 高估，负 = 低估）。"""
    if not results:
        return 0.0
    return sum(r.error for r in results) / len(results)


def compute_direction_accuracy(results: List[ValidationResult]) -> float:
    if not results:
        return 0.0
    hits = sum(1 for r in results if r.direction_hit)
    return hits / len(results)


# ── 衰减对齐验证 ──────────────────────────────────────────────────────

def compute_decay_alignment(
    predicted_strengths: List[float],
    realized_performance: List[float],
    min_threshold: float = 0.05,
) -> tuple[float, float]:
    """
    验证 Alpha 衰减预测与实际表现的对齐程度。

    对齐方式：
      - 找到衰减预测首次低于 min_threshold 的 bar（预测到期点）
      - 找到实际性能首次低于 min_threshold 的 bar（实际到期点）
      - 对齐度 = 1 - |预测到期 - 实际到期| / max(预测到期, 实际到期)
      - 领先时间 = 实际到期 - 预测到期（正值 = 衰减预测领先）

    Returns:
        (alignment_score, lead_time_bars)
    """
    n = min(len(predicted_strengths), len(realized_performance))
    if n < 2:
        return 0.0, 0.0

    pred_expiry   = n
    actual_expiry = n

    for i, s in enumerate(predicted_strengths[:n]):
        if s <= min_threshold:
            pred_expiry = i
            break

    for i, s in enumerate(realized_performance[:n]):
        if s <= min_threshold:
            actual_expiry = i
            break

    denom = max(pred_expiry, actual_expiry)
    if denom == 0:
        return 1.0, 0.0

    alignment = 1.0 - abs(pred_expiry - actual_expiry) / denom
    lead_time  = float(actual_expiry - pred_expiry)

    return round(max(0.0, alignment), 6), round(lead_time, 2)


# ── 记忆有效性验证 ────────────────────────────────────────────────────

def compute_memory_validity(
    predicted_acf: List[float],
    realized_acf:  List[float],
    significant_lags: List[int],
) -> float:
    """
    验证 ACF 结构预测（时间依赖预测）与实际自相关的匹配程度。

    在显著滞后阶上计算预测 ACF 与实际 ACF 的平均余弦相似度。

    Returns:
        memory_validity [0, 1]
    """
    if not significant_lags or not predicted_acf or not realized_acf:
        return 0.0

    n = min(len(predicted_acf), len(realized_acf))
    hits = []
    for lag in significant_lags:
        if lag >= n:
            continue
        p = predicted_acf[lag - 1] if lag - 1 < len(predicted_acf) else 0.0
        r = realized_acf[lag - 1]  if lag - 1 < len(realized_acf)  else 0.0
        # 余弦相似度（符号一致 + 幅度接近）
        if abs(p) < 1e-8 and abs(r) < 1e-8:
            hits.append(1.0)
        elif abs(p) < 1e-8 or abs(r) < 1e-8:
            hits.append(0.0)
        else:
            denom = abs(p) + abs(r)
            sim   = 1.0 - abs(p - r) / denom
            hits.append(max(0.0, sim))

    return round(sum(hits) / len(hits), 6) if hits else 0.0


# ── Temporal Health Score ─────────────────────────────────────────────

def compute_temporal_health(
    direction_acc:    float,
    decay_alignment:  float,
    memory_validity:  float,
    n_realized:       int,
    bias:             float,
    weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
) -> float:
    """
    综合 Temporal Health Score [0, 100]。

    组成：
      - 方向准确率（40%）
      - 衰减对齐度（35%）
      - 记忆有效性（25%）

    额外惩罚：
      - 样本量不足（n < 10）：乘以 n/10
      - 系统性偏差过大（|bias| > 0.05）：扣分

    Args:
        direction_acc:   方向准确率 [0, 1]
        decay_alignment: 衰减对齐度 [0, 1]
        memory_validity: 记忆有效性 [0, 1]
        n_realized:      已实现样本数
        bias:            系统性偏差
        weights:         三项权重（和为 1）
    """
    w_d, w_a, w_m = weights
    base = (w_d * direction_acc + w_a * decay_alignment + w_m * memory_validity)

    # 样本量惩罚
    sample_factor = min(1.0, n_realized / 10.0) if n_realized < 10 else 1.0

    # 偏差惩罚（|bias| > 0.05 时线性扣减，最多扣 20 分）
    bias_penalty = min(0.20, max(0.0, (abs(bias) - 0.05) / 0.25))

    score = base * sample_factor * 100.0 - bias_penalty * 100.0
    return round(max(0.0, min(100.0, score)), 2)


# ── 综合验证指标 ──────────────────────────────────────────────────────

def build_validation_metrics(
    records:              List[ValidationRecord],
    decay_predicted:      Optional[List[float]] = None,
    decay_realized:       Optional[List[float]] = None,
    acf_predicted:        Optional[List[float]] = None,
    acf_realized:         Optional[List[float]] = None,
    significant_acf_lags: Optional[List[int]]   = None,
) -> ValidationMetrics:
    """
    综合计算所有验证指标，返回 ValidationMetrics。

    Args:
        records:              所有 ValidationRecord
        decay_predicted:      衰减预测强度序列
        decay_realized:       实际 Alpha 性能序列
        acf_predicted:        预测 ACF 序列
        acf_realized:         实际 ACF 序列
        significant_acf_lags: 显著滞后阶列表
    """
    n_total    = len(records)
    realized   = [r for r in records if r.is_realized]
    n_realized = len(realized)

    results = compute_errors(realized)

    mae  = compute_mae(results)
    rmse = compute_rmse(results)
    mape = compute_mape(results)
    bias = compute_bias(results)
    d_acc = compute_direction_accuracy(results)

    decay_align = 0.0
    lead_time   = 0.0
    if decay_predicted and decay_realized:
        decay_align, lead_time = compute_decay_alignment(
            decay_predicted, decay_realized)

    mem_validity = 0.0
    if acf_predicted and acf_realized and significant_acf_lags:
        mem_validity = compute_memory_validity(
            acf_predicted, acf_realized, significant_acf_lags)

    health = compute_temporal_health(
        direction_acc   = d_acc,
        decay_alignment = decay_align,
        memory_validity = mem_validity,
        n_realized      = n_realized,
        bias            = bias,
    )

    horizon_acc: dict[str, float] = {}
    for h in [1, 5, 10, 20]:
        h_recs = [r for r in realized if r.horizon_bars == h]
        if h_recs:
            h_res = compute_errors(h_recs)
            horizon_acc[f"h{h}"] = round(compute_direction_accuracy(h_res), 4)

    return ValidationMetrics(
        n_records       = n_total,
        n_realized      = n_realized,
        mae             = round(mae, 8),
        rmse            = round(rmse, 8),
        mape            = round(mape, 6),
        bias            = round(bias, 8),
        direction_acc   = round(d_acc, 4),
        decay_alignment = round(decay_align, 4),
        decay_lead_time = round(lead_time, 2),
        memory_validity = round(mem_validity, 4),
        horizon_accuracy = horizon_acc,
        temporal_health  = health,
    )
