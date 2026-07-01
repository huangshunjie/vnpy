"""
research_validation/engine/bias_engine.py

BiasEngine — 偏差检测引擎（Phase 5 实现）。

检测项目：
  1. Look-ahead Bias   — 因子时间戳 vs 收益时间戳违规检测
  2. Data Leakage      — 训练/测试集数据隔离验证
  3. Survivorship Bias — Universe 稳定性风险提示
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..utils.time_split_utils import validate_no_lookahead


@dataclass
class BiasWarning:
    """单条偏差检测警告。"""
    bias_type:   str = ""
    severity:    str = "warning"  # "warning" | "critical"
    description: str = ""
    detail:      str = ""
    period:      int = -1

    @property
    def is_critical(self) -> bool:
        return self.severity == "critical"

    def to_line(self) -> str:
        sev = "[CRITICAL]" if self.is_critical else "[WARN    ]"
        loc = f" 期={self.period}" if self.period >= 0 else ""
        return f"  {sev} [{self.bias_type:15s}]{loc}  {self.description}"


@dataclass
class BiasSummary:
    """偏差检测汇总结果。"""
    warnings:          list[BiasWarning] = field(default_factory=list)
    lookahead_count:   int   = 0
    leakage_count:     int   = 0
    survivorship_risk: bool  = False
    bias_score:        float = 0.0
    passed:            bool  = True

    @property
    def critical_warnings(self) -> list[BiasWarning]:
        return [w for w in self.warnings if w.is_critical]

    @property
    def n_critical(self) -> int:
        return len(self.critical_warnings)

    @property
    def n_total(self) -> int:
        return len(self.warnings)

    def to_text(self) -> str:
        lines = [
            "  偏差检测报告",
            "  " + "─" * 58,
            f"  总体评级  : {'PASS' if self.passed else 'FAIL'}  "
            f"偏差评分={self.bias_score:.1f}/100（越低越好）",
            f"  Critical : {self.n_critical} 条",
            f"  Warning  : {self.n_total - self.n_critical} 条",
            f"  Look-ahead 违规  : {self.lookahead_count} 处",
            f"  Data Leakage 风险: {self.leakage_count} 处",
            f"  Survivorship 风险: {'是' if self.survivorship_risk else '否'}",
            "  " + "─" * 58,
        ]
        if not self.warnings:
            lines.append("  未检测到偏差问题。")
        else:
            for w in self.warnings:
                lines.append(w.to_line())
                if w.detail:
                    lines.append(f"        -> {w.detail}")
        lines.append("  " + "─" * 58)
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  BiasEngine
# ─────────────────────────────────────────────────────────────────────────────

class BiasEngine:
    """偏差检测引擎（Phase 5 实现）。"""

    MIN_LAG: int = 1
    SURVIVORSHIP_THRESHOLD: float = 0.20
    LEAKAGE_ZERO_VAR_THRESHOLD: float = 1e-10

    def __init__(self) -> None:
        self._warnings: list[BiasWarning] = []

    def reset(self) -> None:
        self._warnings.clear()

    def run(
        self,
        factor_cs: list,
        return_cs: list,
        dates:     list,
        *,
        factor_timestamps: list | None = None,
        return_timestamps: list | None = None,
        train_end_idx:     int | None  = None,
    ) -> BiasSummary:
        """执行全部偏差检测。"""
        self._warnings.clear()
        n = len(dates)

        # look-ahead 检测仅在用户显式提供时间戳时执行
        # 若使用日期序列代理，末尾复用会产生假阳性，跳过
        if factor_timestamps is not None and return_timestamps is not None:
            la_count = self._check_lookahead(factor_timestamps, return_timestamps)
        else:
            la_count = 0
        lk_count = self._check_data_leakage(
            factor_cs, train_end_idx=train_end_idx or int(n * 0.7),
        )
        surv_risk = self._check_survivorship(factor_cs)
        self._check_zero_variance(factor_cs)
        self._check_alignment(factor_cs, return_cs)

        bias_score = self._calc_bias_score()
        passed = (
            not any(w.is_critical for w in self._warnings)
            and bias_score < 30.0
        )
        return BiasSummary(
            warnings          = list(self._warnings),
            lookahead_count   = la_count,
            leakage_count     = lk_count,
            survivorship_risk = surv_risk,
            bias_score        = bias_score,
            passed            = passed,
        )

    # ---- Look-ahead -------------------------------------------------------

    def _check_lookahead(self, factor_ts: list, return_ts: list) -> int:
        violations = 0
        n = min(len(factor_ts), len(return_ts))
        for i in range(n):
            ft, rt = factor_ts[i], return_ts[i]
            if not validate_no_lookahead(ft, rt, lag=self.MIN_LAG):
                violations += 1
                if violations <= 5:
                    self._warnings.append(BiasWarning(
                        bias_type   = "look_ahead",
                        severity    = "critical",
                        description = f"前视偏差：收益时间早于因子时间",
                        detail      = f"factor_ts={ft}  return_ts={rt}",
                        period      = i,
                    ))
        if violations > 5:
            self._warnings.append(BiasWarning(
                bias_type   = "look_ahead",
                severity    = "critical",
                description = f"前视偏差：共 {violations} 处违规（已显示前 5 条）",
                detail      = "建议检查因子数据生成流程的时间戳一致性",
            ))
        return violations

    # ---- Data Leakage -----------------------------------------------------

    def _check_data_leakage(self, factor_cs: list, *, train_end_idx: int) -> int:
        n = len(factor_cs)
        if train_end_idx >= n or train_end_idx < 1:
            return 0
        leaks = 0

        # 训练集末5期快照
        train_snaps = set()
        for i in range(max(0, train_end_idx - 5), train_end_idx):
            snap = tuple(sorted((k, round(v, 6)) for k, v in factor_cs[i].items()))
            train_snaps.add(snap)

        for i in range(train_end_idx, n):
            snap = tuple(sorted((k, round(v, 6)) for k, v in factor_cs[i].items()))
            if snap in train_snaps:
                leaks += 1
                if leaks <= 3:
                    self._warnings.append(BiasWarning(
                        bias_type   = "data_leakage",
                        severity    = "critical",
                        description = f"数据泄露：测试期 {i} 因子截面与训练集完全相同",
                        detail      = f"train_end={train_end_idx}  test_period={i}",
                        period      = i,
                    ))

        # 测试集零方差检测
        zero_var = sum(
            1 for i in range(train_end_idx, n)
            if self._cross_var(factor_cs[i]) < self.LEAKAGE_ZERO_VAR_THRESHOLD
        )
        if zero_var > 0:
            sev = "critical" if zero_var > (n - train_end_idx) * 0.1 else "warning"
            self._warnings.append(BiasWarning(
                bias_type   = "data_leakage",
                severity    = sev,
                description = f"因子截面方差异常：{zero_var} 期测试集截面方差接近零",
                detail      = "可能存在因子数据未更新或计算错误",
            ))
            leaks += zero_var
        return leaks

    # ---- Survivorship -----------------------------------------------------

    def _check_survivorship(self, factor_cs: list) -> bool:
        if len(factor_cs) < 2:
            return False
        first = set(factor_cs[0])
        last  = set(factor_cs[-1])
        added, removed = last - first, first - last
        rate = (len(added) + len(removed)) / max(len(first), 1)
        if rate > self.SURVIVORSHIP_THRESHOLD:
            sev = "critical" if rate > 0.5 else "warning"
            self._warnings.append(BiasWarning(
                bias_type   = "survivorship",
                severity    = sev,
                description = f"幸存者偏差风险：Universe 变化率 {rate:.1%}（+{len(added)}/-{len(removed)}）",
                detail      = "建议使用包含退市标的的完整 Universe",
            ))
            return True
        # 中间抽查
        n = len(factor_cs)
        step = max(1, n // 10)
        prev = first
        max_diff = 0.0
        for i in range(step, n, step):
            curr = set(factor_cs[i])
            diff = len(prev.symmetric_difference(curr)) / max(len(prev), 1)
            max_diff = max(max_diff, diff)
            prev = curr
        if max_diff > 0.3:
            self._warnings.append(BiasWarning(
                bias_type   = "survivorship",
                severity    = "warning",
                description = f"Universe 单期最大变化率 {max_diff:.1%}",
                detail      = "建议检查标的进出时间点是否与因子计算一致",
            ))
            return True
        return False

    # ---- 额外检测 ----------------------------------------------------------

    def _check_zero_variance(self, factor_cs: list) -> None:
        zeros = [i for i, fc in enumerate(factor_cs)
                 if self._cross_var(fc) < self.LEAKAGE_ZERO_VAR_THRESHOLD]
        if zeros:
            pct = len(zeros) / max(len(factor_cs), 1)
            self._warnings.append(BiasWarning(
                bias_type   = "other",
                severity    = "critical" if pct > 0.1 else "warning",
                description = f"数据质量：{len(zeros)} 期（{pct:.1%}）因子截面方差为零",
                detail      = "建议检查因子计算逻辑，确认截面内存在差异",
            ))

    def _check_alignment(self, factor_cs: list, return_cs: list) -> None:
        mismatches = []
        for i, (fc, rc) in enumerate(zip(factor_cs, return_cs)):
            if len(fc) == 0:
                continue
            cov = len(set(fc) & set(rc)) / len(fc)
            if cov < 0.5:
                mismatches.append((i, cov))
        if mismatches:
            worst = min(c for _, c in mismatches)
            self._warnings.append(BiasWarning(
                bias_type   = "other",
                severity    = "critical" if worst < 0.3 else "warning",
                description = f"数据对齐：{len(mismatches)} 期因子/收益标的匹配率 < 50%（最低 {worst:.1%}）",
                detail      = "建议确认因子与价格数据使用相同的标的代码体系",
            ))

    # ---- 便捷接口 ----------------------------------------------------------

    def check_lookahead_series(self, factor_ts: list, return_ts: list) -> list[dict]:
        return [
            {"period": i, "factor_ts": ft, "return_ts": rt,
             "message": f"期 {i}：return_ts={rt} <= factor_ts={ft}"}
            for i, (ft, rt) in enumerate(zip(factor_ts, return_ts))
            if not validate_no_lookahead(ft, rt, lag=self.MIN_LAG)
        ]

    def get_warnings(self) -> list[BiasWarning]:
        return list(self._warnings)

    # ---- 工具 --------------------------------------------------------------

    @staticmethod
    def _cross_var(fc: dict) -> float:
        vals = list(fc.values())
        if len(vals) < 2:
            return 0.0
        mean = sum(vals) / len(vals)
        return sum((v - mean) ** 2 for v in vals) / len(vals)

    @staticmethod
    def _shift_dates(dates: list, lag: int) -> list:
        if not dates or lag <= 0:
            return list(dates)
        return list(dates[lag:]) + [dates[-1]] * lag

    def _calc_bias_score(self) -> float:
        score = sum(25.0 if w.is_critical else 10.0 for w in self._warnings)
        return min(100.0, score)
