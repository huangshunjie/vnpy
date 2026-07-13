"""
data_intelligence_ai/utils/quality_utils.py  (Phase 3)

数据质量检查工具函数。

- 缺失值检测
- 异常值检测（Z-score / IQR）
- 延迟检测
- 一致性检测
- 数据漂移检测（均值漂移 + 方差比 + 近似KS）
- 质量评分计算
"""
from __future__ import annotations
import math
import uuid
from datetime import datetime, timedelta
from ..constant import QualityStatus
from ..model.quality_model import QualityIssue, QualityReport, DriftReport


# ── 缺失值检测 ────────────────────────────────────────────────────────

def check_missing(
    value:        float | None,
    feature_name: str,
    symbol:       str,
) -> QualityIssue | None:
    """检测 None / NaN / Inf。"""
    if value is None:
        return QualityIssue(
            issue_id    = f"ISS_{uuid.uuid4().hex[:6].upper()}",
            status      = QualityStatus.MISSING,
            field       = feature_name,
            description = f"{symbol}/{feature_name}: value is None",
            severity    = 1.0,
            value       = 0.0,
            threshold   = 0.0,
        )
    if math.isnan(value) or math.isinf(value):
        return QualityIssue(
            issue_id    = f"ISS_{uuid.uuid4().hex[:6].upper()}",
            status      = QualityStatus.MISSING,
            field       = feature_name,
            description = f"{symbol}/{feature_name}: value is NaN/Inf",
            severity    = 1.0,
            value       = 0.0,
            threshold   = 0.0,
        )
    return None


# ── 异常值检测 ────────────────────────────────────────────────────────

def check_outlier_zscore(
    value:        float,
    history:      list[float],
    feature_name: str,
    symbol:       str,
    z_threshold:  float = 3.5,
) -> QualityIssue | None:
    """Z-score 异常值检测。"""
    if len(history) < 5:
        return None
    mu    = sum(history) / len(history)
    sigma = math.sqrt(sum((x - mu) ** 2 for x in history) / len(history))
    if sigma < 1e-10:
        return None
    z = abs(value - mu) / sigma
    if z > z_threshold:
        severity = min((z - z_threshold) / z_threshold, 1.0)
        return QualityIssue(
            issue_id    = f"ISS_{uuid.uuid4().hex[:6].upper()}",
            status      = QualityStatus.OUTLIER,
            field       = feature_name,
            description = f"{symbol}/{feature_name}: z={z:.2f} > {z_threshold}",
            severity    = round(severity, 4),
            value       = value,
            threshold   = z_threshold,
        )
    return None


def check_outlier_iqr(
    value:        float,
    history:      list[float],
    feature_name: str,
    symbol:       str,
    k:            float = 2.5,
) -> QualityIssue | None:
    """IQR 异常值检测。"""
    if len(history) < 5:
        return None
    sorted_h = sorted(history)
    n        = len(sorted_h)
    q1       = sorted_h[n // 4]
    q3       = sorted_h[3 * n // 4]
    iqr      = q3 - q1
    if iqr < 1e-10:
        return None
    lo, hi = q1 - k * iqr, q3 + k * iqr
    if value < lo or value > hi:
        dist   = max(abs(value - lo), abs(value - hi))
        severity = min(dist / (k * iqr), 1.0)
        return QualityIssue(
            issue_id    = f"ISS_{uuid.uuid4().hex[:6].upper()}",
            status      = QualityStatus.OUTLIER,
            field       = feature_name,
            description = f"{symbol}/{feature_name}: IQR outlier [{lo:.4f},{hi:.4f}]",
            severity    = round(severity, 4),
            value       = value,
            threshold   = k,
        )
    return None


# ── 延迟检测 ──────────────────────────────────────────────────────────

def check_delay(
    timestamp:      datetime,
    feature_name:   str,
    symbol:         str,
    max_delay_secs: float = 300.0,
) -> QualityIssue | None:
    """检测特征时间戳是否超过最大允许延迟。"""
    age_secs = (datetime.now() - timestamp).total_seconds()
    if age_secs > max_delay_secs:
        severity = min(age_secs / (max_delay_secs * 5), 1.0)
        return QualityIssue(
            issue_id    = f"ISS_{uuid.uuid4().hex[:6].upper()}",
            status      = QualityStatus.DELAYED,
            field       = feature_name,
            description = f"{symbol}/{feature_name}: age={age_secs:.0f}s > {max_delay_secs:.0f}s",
            severity    = round(severity, 4),
            value       = age_secs,
            threshold   = max_delay_secs,
        )
    return None


# ── 一致性检测 ────────────────────────────────────────────────────────

def check_consistency(
    value:        float,
    related:      dict[str, float],   # {feature_name: value} 关联特征
    feature_name: str,
    symbol:       str,
    rules:        list[tuple[str, str, float]] | None = None,
) -> list[QualityIssue]:
    """
    一致性检查：验证特征值与关联特征满足业务规则。

    rules: [(related_feature, operator, threshold), ...]
    operator: "lt" / "gt" / "eq" / "range"

    示例: [("hist_vol", "lt", 1.0)] 表示 value < hist_vol * 1.0
    """
    if not rules:
        return []
    issues = []
    for rel_name, op, thresh in rules:
        rel_val = related.get(rel_name)
        if rel_val is None:
            continue
        violated = False
        if   op == "lt"    and not (value < rel_val * thresh):
            violated = True
        elif op == "gt"    and not (value > rel_val * thresh):
            violated = True
        elif op == "range" and not (-thresh <= value - rel_val <= thresh):
            violated = True
        if violated:
            issues.append(QualityIssue(
                issue_id    = f"ISS_{uuid.uuid4().hex[:6].upper()}",
                status      = QualityStatus.INCONSISTENT,
                field       = feature_name,
                description = f"{symbol}/{feature_name} inconsistent with {rel_name}: "
                              f"op={op} thresh={thresh}",
                severity    = 0.6,
                value       = value,
                threshold   = thresh,
            ))
    return issues


# ── 综合质量评分 ──────────────────────────────────────────────────────

def compute_quality_score(issues: list[QualityIssue]) -> float:
    """
    综合质量评分 [0, 100]。

    每个问题按严重程度扣分：
      severity >= 0.9  → -30
      severity >= 0.6  → -15
      else             → -5
    """
    score = 100.0
    for issue in issues:
        if issue.severity >= 0.9:
            score -= 30.0
        elif issue.severity >= 0.6:
            score -= 15.0
        else:
            score -= 5.0
    return round(max(score, 0.0), 2)


def derive_status(issues: list[QualityIssue]) -> QualityStatus:
    """从问题列表推断总体状态。"""
    if not issues:
        return QualityStatus.CLEAN
    statuses = {i.status for i in issues}
    if QualityStatus.MISSING       in statuses: return QualityStatus.MISSING
    if QualityStatus.OUTLIER       in statuses: return QualityStatus.OUTLIER
    if QualityStatus.DELAYED       in statuses: return QualityStatus.DELAYED
    if QualityStatus.INCONSISTENT  in statuses: return QualityStatus.INCONSISTENT
    return QualityStatus.UNKNOWN


# ── 一次性全量检查 ────────────────────────────────────────────────────

def run_quality_check(
    value:          float | None,
    timestamp:      datetime,
    feature_name:   str,
    symbol:         str,
    history:        list[float] | None = None,
    related:        dict[str, float] | None = None,
    rules:          list[tuple[str, str, float]] | None = None,
    z_threshold:    float = 3.5,
    max_delay_secs: float = 300.0,
) -> QualityReport:
    """
    对单个特征值执行完整质量检查：
      1. 缺失值
      2. Z-score 异常值（有历史数据时）
      3. IQR 异常值（有历史数据时）
      4. 延迟
      5. 一致性
    """
    report = QualityReport(
        report_id    = f"QR_{uuid.uuid4().hex[:8].upper()}",
        symbol       = symbol,
        feature_name = feature_name,
    )

    # 1. missing
    miss = check_missing(value, feature_name, symbol)
    if miss:
        report.add_issue(miss)
        report.status = QualityStatus.MISSING
        report.score  = 0.0
        return report   # 有缺失直接返回，后续检查无意义

    assert value is not None
    history = history or []

    # 2. outlier (z-score)
    z_issue = check_outlier_zscore(value, history, feature_name, symbol, z_threshold)
    if z_issue:
        report.add_issue(z_issue)

    # 3. outlier (IQR)
    iqr_issue = check_outlier_iqr(value, history, feature_name, symbol)
    if iqr_issue and not z_issue:   # 避免重复报告
        report.add_issue(iqr_issue)

    # 4. delay
    delay_issue = check_delay(timestamp, feature_name, symbol, max_delay_secs)
    if delay_issue:
        report.add_issue(delay_issue)

    # 5. consistency
    if related and rules:
        for ci in check_consistency(value, related, feature_name, symbol, rules):
            report.add_issue(ci)

    report.status = derive_status(report.issues)
    report.score  = compute_quality_score(report.issues)
    return report


# ── 数据漂移检测 ──────────────────────────────────────────────────────

def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mu    = sum(values) / len(values)
    sigma = math.sqrt(sum((x - mu) ** 2 for x in values) / len(values))
    return mu, sigma


def _approx_ks(hist: list[float], curr: list[float]) -> float:
    """
    近似 KS 统计量（不依赖 scipy）。
    比较两个分布的累积分布函数最大差值。
    """
    if not hist or not curr:
        return 0.0
    all_vals = sorted(set(hist + curr))
    n_h, n_c = len(hist), len(curr)
    hist_set  = sorted(hist)
    curr_set  = sorted(curr)
    max_diff  = 0.0
    for v in all_vals:
        cdf_h = sum(1 for x in hist_set if x <= v) / n_h
        cdf_c = sum(1 for x in curr_set if x <= v) / n_c
        max_diff = max(max_diff, abs(cdf_h - cdf_c))
    return round(max_diff, 4)


def detect_drift(
    feature_name:    str,
    symbol:          str,
    hist_values:     list[float],
    curr_values:     list[float],
    drift_threshold: float = 0.3,
) -> DriftReport:
    """
    检测特征值分布漂移。

    综合漂移得分 = 0.4 × mean_drift_norm + 0.3 × std_ratio_dev + 0.3 × ks
    """
    h_mu, h_std = _mean_std(hist_values)
    c_mu, c_std = _mean_std(curr_values)

    # mean drift (normalized by hist_std)
    if h_std > 1e-10:
        mean_drift = abs(c_mu - h_mu) / h_std
    else:
        mean_drift = abs(c_mu - h_mu)

    # std ratio deviation from 1.0
    std_ratio     = (c_std / h_std) if h_std > 1e-10 else 1.0
    std_ratio_dev = abs(std_ratio - 1.0)

    # approx KS
    ks = _approx_ks(hist_values, curr_values)

    # composite drift score
    drift_score = round(
        0.4 * min(mean_drift / 3.0, 1.0)
        + 0.3 * min(std_ratio_dev, 1.0)
        + 0.3 * ks,
        4)

    return DriftReport(
        report_id       = f"DR_{uuid.uuid4().hex[:8].upper()}",
        feature_name    = feature_name,
        symbol          = symbol,
        hist_mean       = round(h_mu,     6),
        hist_std        = round(h_std,    6),
        curr_mean       = round(c_mu,     6),
        curr_std        = round(c_std,    6),
        mean_drift      = round(mean_drift,   4),
        std_ratio       = round(std_ratio,    4),
        ks_statistic    = ks,
        drift_score     = drift_score,
        is_drifted      = drift_score > drift_threshold,
        drift_threshold = drift_threshold,
    )
