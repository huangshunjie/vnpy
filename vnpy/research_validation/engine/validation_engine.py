"""
research_validation/engine/validation_engine.py

ValidationEngine — 核心验证编排引擎（Phase 5 实现）。

职责：
  - 协调 WalkForwardEngine + OOSEngine + RegimeEngine + StabilityEngine + BiasEngine
  - 管理验证任务生命周期（带停止信号）
  - 汇总各子引擎结果到 ValidationResult
"""

from __future__ import annotations

import threading
from datetime import datetime

from .walkforward_engine import WalkForwardEngine
from .oos_engine         import OOSEngine
from .regime_engine      import RegimeEngine
from .stability_engine   import StabilityEngine
from .bias_engine        import BiasEngine
from ..model.result_model import ValidationResult
from ..model.validation_model import ValidationParams
from ..constant import ValidationStatus


class ValidationEngine:
    """核心验证编排引擎（Phase 5）。"""

    def __init__(self) -> None:
        self.wf_engine        = WalkForwardEngine()
        self.oos_engine       = OOSEngine()
        self.regime_engine    = RegimeEngine()
        self.stability_engine = StabilityEngine()
        self.bias_engine      = BiasEngine()
        self._stop_event: threading.Event | None = None

    def set_stop_event(self, stop_event: threading.Event) -> None:
        self._stop_event = stop_event

    def _should_stop(self) -> bool:
        return self._stop_event is not None and self._stop_event.is_set()

    # ------------------------------------------------------------------ #
    #  主编排入口
    # ------------------------------------------------------------------ #

    def run(
        self,
        params:    ValidationParams,
        factor_cs: list[dict[str, float]],
        return_cs: list[dict[str, float]],
        dates:     list,
        progress_cb=None,
    ) -> ValidationResult:
        """执行完整验证流程（Phase 5：WF + OOS + Regime + Stability + Bias）。"""
        result = ValidationResult(
            factor_name = params.factor_name,
            status      = ValidationStatus.RUNNING,
        )

        def _p(pct: float, msg: str) -> None:
            if progress_cb:
                progress_cb(pct, msg)

        # ── Walk Forward ────────────────────────────────────────────────
        if params.run_walkforward:
            if self._should_stop():
                result.status = ValidationStatus.CANCELLED
                return result
            _p(0.05, "Walk Forward：配置滚动窗口...")
            self.wf_engine.set_windows(
                train=params.train_window,
                test=params.test_window,
                step=params.step_size,
            )
            self.wf_engine.use_rank_ic = False
            _p(0.08, "Walk Forward：开始滚动验证...")
            try:
                wf_results, wf_summary = self.wf_engine.run(
                    factor_cs, return_cs, dates
                )
                result.walkforward_results = wf_results
                result.wf_summary = wf_summary
                _p(0.28,
                   f"Walk Forward 完成：{wf_summary.n_windows} 窗口  "
                   f"avg_test_IC={wf_summary.avg_test_ic:.4f}  "
                   f"overfit={wf_summary.overfit_score:.1f}")
            except Exception as exc:
                _p(0.28, f"[WARN] Walk Forward 失败：{exc}")

        # ── OOS Testing ─────────────────────────────────────────────────
        if params.run_oos:
            if self._should_stop():
                result.status = ValidationStatus.CANCELLED
                return result
            _p(0.30, "OOS Testing：切分样本内/样本外...")
            self.oos_engine.set_split(params.oos_ratio)
            self.oos_engine.use_rank_ic = False
            try:
                oos_result = self.oos_engine.run(factor_cs, return_cs, dates)
                result.oos_result = oos_result
                _p(0.46,
                   f"OOS 完成：IS_IC={oos_result.is_ic:.4f}  "
                   f"OOS_IC={oos_result.oos_ic:.4f}  "
                   f"overfit={oos_result.overfit_ratio:.2f}")
            except Exception as exc:
                _p(0.46, f"[WARN] OOS Testing 失败：{exc}")

        # ── Regime Detection ────────────────────────────────────────────
        if params.run_regime:
            if self._should_stop():
                result.status = ValidationStatus.CANCELLED
                return result
            _p(0.48, "Regime Detection：识别市场状态...")
            self.regime_engine.set_lookback(params.regime_lookback)
            try:
                market_rets = RegimeEngine.estimate_market_return_from_cs(return_cs)
                regime_summary = self.regime_engine.run(
                    factor_cs=factor_cs,
                    market_rets=market_rets,
                    dates=dates,
                    return_cs=return_cs,
                )
                result.regime_summary = regime_summary
                best = regime_summary.best_regime
                _p(0.62,
                   f"Regime 完成：Bull={regime_summary.bull_pct:.0%}  "
                   f"Bear={regime_summary.bear_pct:.0%}  "
                   f"Sideways={regime_summary.sideways_pct:.0%}"
                   + (f"  最佳={best.label} IC={best.ic_mean:+.4f}" if best else ""))
            except Exception as exc:
                _p(0.62, f"[WARN] Regime Detection 失败：{exc}")

        # ── Stability Testing ───────────────────────────────────────────
        if params.run_stability:
            if self._should_stop():
                result.status = ValidationStatus.CANCELLED
                return result
            _p(0.64, "Stability Testing：计算 Rolling IC / 衰减...")
            self.stability_engine.set_window(params.stability_window)
            self.stability_engine.use_rank_ic = False
            try:
                stab_summary = self.stability_engine.run(factor_cs, return_cs, dates)
                result.stability_summary = stab_summary
                _p(0.80,
                   f"Stability 完成：{stab_summary.stability_level}  "
                   f"评分={stab_summary.stability_score:.1f}  "
                   f"半衰期={stab_summary.ic_decay_halflife:.1f}期  "
                   f"lag1_AC={stab_summary.lag1_autocorr:+.3f}")
            except Exception as exc:
                _p(0.80, f"[WARN] Stability Testing 失败：{exc}")

        # ── Bias Detection ──────────────────────────────────────────────
        if params.run_bias:
            if self._should_stop():
                result.status = ValidationStatus.CANCELLED
                return result
            _p(0.82, "Bias Detection：检测前视偏差 / 数据泄露 / 幸存者偏差...")
            self.bias_engine.reset()
            try:
                bias_summary = self.bias_engine.run(
                    factor_cs=factor_cs,
                    return_cs=return_cs,
                    dates=dates,
                )
                result.bias_summary = bias_summary
                status_str = "PASS" if bias_summary.passed else "FAIL"
                _p(0.96,
                   f"Bias 完成：{status_str}  "
                   f"偏差评分={bias_summary.bias_score:.1f}  "
                   f"Critical={bias_summary.n_critical}  "
                   f"Total={bias_summary.n_total}")
            except Exception as exc:
                _p(0.96, f"[WARN] Bias Detection 失败：{exc}")

        # ── 综合评分 ────────────────────────────────────────────────────
        result.overall_score = self._calc_overall_score(result)
        result.is_real_alpha = result.overall_score >= 60.0
        result.status        = ValidationStatus.COMPLETED
        result.computed_at   = datetime.now()

        _p(1.0,
           f"验证完成：综合评分={result.overall_score:.1f}  "
           f"Alpha={'真实' if result.is_real_alpha else '可疑'}")
        return result

    def reset(self) -> None:
        self.wf_engine.reset()
        self.oos_engine.reset()
        self.regime_engine.reset()
        self.stability_engine.reset()
        self.bias_engine.reset()

    # ------------------------------------------------------------------ #
    #  综合评分（Phase 5 最终版本）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _calc_overall_score(result: ValidationResult) -> float:
        """
        综合 Alpha 真实性评分（0~100）。

        Phase 5 权重分配：
          Walk Forward  25 分
          OOS IC        25 分
          Regime        20 分
          Stability     15 分
          Bias 惩罚    -15 分（偏差越严重扣越多）
        """
        score = 0.0

        # ── Walk Forward（0~25）─────────────────────────────────────────
        wf = getattr(result, "wf_summary", None)
        if wf is not None:
            if wf.avg_test_ic > 0.02:
                score += 10.0
            elif wf.avg_test_ic > 0:
                score += 5.0
            score += min(8.0, max(0.0, wf.test_ic_ir * 8.0))
            score -= wf.overfit_score * 0.07
            score = max(0.0, score)

        # ── OOS（0~25）──────────────────────────────────────────────────
        oos = result.oos_result
        if oos is not None:
            if oos.oos_ic > 0.02:
                score += 12.0
            elif oos.oos_ic > 0:
                score += 6.0
            of = oos.overfit_ratio
            if 0 < of < float("inf"):
                if of <= 1.5:
                    score += 8.0
                elif of <= 3.0:
                    score += 4.0

        # ── Regime（0~20）───────────────────────────────────────────────
        rs = getattr(result, "regime_summary", None)
        if rs is not None:
            valid = [r for r in rs.all_results if r.sample_count >= 5]
            if valid:
                pos = sum(1 for r in valid if r.ic_mean > 0)
                rscore = (pos / len(valid)) * 20.0
                if sum(1 for r in valid if r.is_significant) >= 1:
                    rscore = min(20.0, rscore + 5.0)
                score += rscore

        # ── Stability（0~15）────────────────────────────────────────────
        stab = getattr(result, "stability_summary", None)
        if stab is not None:
            score += stab.stability_score / 100.0 * 15.0

        # ── Bias 惩罚（0~-15）───────────────────────────────────────────
        bias = getattr(result, "bias_summary", None)
        if bias is not None:
            score -= bias.bias_score / 100.0 * 15.0

        return round(min(100.0, max(0.0, score)), 1)
