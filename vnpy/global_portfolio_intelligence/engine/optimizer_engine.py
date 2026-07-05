"""
global_portfolio_intelligence/engine/optimizer_engine.py  (Phase 3)

OptimizerEngine — 跨模块联合优化器。

优化循环：
  Alpha → Strategy → Portfolio → Execution → Feedback → Re-optimize

优化维度：
  1. Alpha weights       (n_alpha 维)
  2. Strategy allocation (n_strategy 维)
  3. Portfolio weights   (n_asset 维)
  4. Capital distribution(n_strategy 维)
  5. Execution intensity (n_strategy 维)
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import OptimizationMode
from ..model.allocation_model import CrossModuleState, OptimizationResult
from ..utils.optimization_utils import (
    project_to_simplex, equal_weights, risk_parity_weights,
    projected_gradient_ascent, compute_cross_module_score, has_converged,
)
from ..utils.objective_utils import compute_unified_objective


class OptimizerEngine:
    """跨模块联合优化器（Phase 3 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log      = log_fn or (lambda m: None)
        self._mode     = OptimizationMode.BALANCED
        self._results:  list[OptimizationResult] = []
        self._state:    CrossModuleState = CrossModuleState()

        # 子系统评分缓存（由外部更新）
        self._alpha_scores:    list[float] = []
        self._strategy_scores: list[float] = []
        self._portfolio_scores:list[float] = []

    def init(self)  -> None: self._log("[OptimizerEngine] init()")
    def start(self) -> None: self._log("[OptimizerEngine] start()")
    def stop(self)  -> None: self._log("[OptimizerEngine] stop()")

    def set_mode(self, mode: OptimizationMode) -> None:
        self._mode = mode
        self._log(f"[OptimizerEngine] mode -> {mode.value}")

    # ── external score feeds ─────────────────────────────────────────
    def update_alpha_scores(self, scores: list[float]) -> None:
        self._alpha_scores = list(scores)

    def update_strategy_scores(self, scores: list[float]) -> None:
        self._strategy_scores = list(scores)

    def update_portfolio_scores(self, scores: list[float]) -> None:
        self._portfolio_scores = list(scores)

    # ── core optimization ────────────────────────────────────────────
    def optimize(
        self,
        n_alpha:    int = 3,
        n_strategy: int = 4,
        n_asset:    int = 5,
        lr:         float = 0.05,
        n_iter:     int   = 30,
        alpha_ids:    list[str] | None = None,
        strategy_ids: list[str] | None = None,
        asset_ids:    list[str] | None = None,
    ) -> OptimizationResult:
        """
        执行一轮跨模块联合优化。

        优化流程：
          1. 初始化等权向量
          2. 构建联合目标函数（调用 compute_cross_module_score）
          3. 投影梯度上升（simplex 约束）
          4. 更新 CrossModuleState
          5. 返回 OptimizationResult
        """
        run_id    = f"OPT_{uuid.uuid4().hex[:8].upper()}"
        started   = datetime.now()

        # --- 初始权重 (等权) ---
        aw0 = equal_weights(n_alpha)
        sw0 = equal_weights(n_strategy)
        pw0 = equal_weights(n_asset)
        cd0 = equal_weights(n_strategy)
        ei0 = [0.7] * n_strategy          # 默认执行力度 0.7

        # --- 评分缓存（若未提供则用等分 50）---
        a_sc = (self._alpha_scores[:n_alpha]
                + [50.0] * n_alpha)[:n_alpha]
        s_sc = (self._strategy_scores[:n_strategy]
                + [50.0] * n_strategy)[:n_strategy]
        p_sc = (self._portfolio_scores[:n_asset]
                + [50.0] * n_asset)[:n_asset]

        # --- 初始评分 ---
        init_result = compute_cross_module_score(
            aw0, sw0, pw0, cd0, ei0, a_sc, s_sc, p_sc)
        initial_score = init_result["composite"]

        # --- 联合参数向量：[alpha | strategy | portfolio | capital | exec] ---
        x0 = aw0 + sw0 + pw0 + cd0 + ei0
        dims = [n_alpha, n_strategy, n_asset, n_strategy, n_strategy]
        total = sum(dims)

        def _split(x):
            parts = []
            idx = 0
            for d in dims:
                parts.append(x[idx:idx+d])
                idx += d
            return parts

        def _objective(x):
            if len(x) < total:
                return 0.0
            aw, sw, pw, cd, ei = _split(x)
            r = compute_cross_module_score(aw, sw, pw, cd, ei, a_sc, s_sc, p_sc)
            return r["composite"] / 100.0   # normalize to [0,1] for gradient

        # --- 优化（alpha/strategy/portfolio/capital 分量约束在单纯形上）---
        # exec_intensity 不约束在单纯形，保持 [0,1] clamp
        def _constrained_obj(x):
            # project alpha, strategy, portfolio, capital blocks
            parts = _split(x)
            new_parts = [
                project_to_simplex(parts[0]),
                project_to_simplex(parts[1]),
                project_to_simplex(parts[2]),
                project_to_simplex(parts[3]),
                [min(max(v, 0.0), 1.0) for v in parts[4]],
            ]
            xp = []
            for p in new_parts:
                xp.extend(p)
            return _objective(xp)

        best_x, obj_hist = projected_gradient_ascent(
            _constrained_obj, x0,
            lr=lr, n_iter=n_iter,
            constrained=False,   # handled internally above
        )

        # --- 提取最优权重 ---
        parts = _split(best_x)
        best_aw  = project_to_simplex(parts[0])
        best_sw  = project_to_simplex(parts[1])
        best_pw  = project_to_simplex(parts[2])
        best_cd  = project_to_simplex(parts[3])
        best_ei  = [min(max(v, 0.0), 1.0) for v in parts[4]]

        # --- 最终评分 ---
        final_result = compute_cross_module_score(
            best_aw, best_sw, best_pw, best_cd, best_ei, a_sc, s_sc, p_sc)
        final_score = final_result["composite"]

        converged = has_converged([v * 100 for v in obj_hist], window=5)

        self._state = CrossModuleState(
            alpha_weights      = best_aw,
            strategy_allocs    = best_sw,
            portfolio_weights  = best_pw,
            capital_dist       = best_cd,
            exec_intensity     = best_ei,
            alpha_ids          = alpha_ids    or [f"A{i}" for i in range(n_alpha)],
            strategy_ids       = strategy_ids or [f"S{i}" for i in range(n_strategy)],
            asset_ids          = asset_ids    or [f"P{i}" for i in range(n_asset)],
            composite_score    = final_score,
            alpha_score        = final_result["alpha_score"],
            strategy_score     = final_result["strategy_score"],
            portfolio_score    = final_result["portfolio_score"],
            execution_score    = final_result["execution_score"],
            capital_score      = final_result["capital_score"],
            mode               = self._mode,
            iterations         = len(obj_hist),
            converged          = converged,
            obj_history        = [round(v * 100, 4) for v in obj_hist],
            updated_at         = datetime.now(),
        )

        result = OptimizationResult(
            run_id        = run_id,
            mode          = self._mode,
            state         = self._state,
            initial_score = initial_score,
            final_score   = final_score,
            improvement   = round(final_score - initial_score, 4),
            n_iterations  = len(obj_hist),
            converged     = converged,
            started_at    = started,
            completed_at  = datetime.now(),
        )
        self._results.append(result)

        self._log(
            f"[OptimizerEngine] run {run_id}: "
            f"mode={self._mode.value} "
            f"iter={len(obj_hist)} converged={converged} "
            f"score: {initial_score:.2f} -> {final_score:.2f} "
            f"(+{final_score-initial_score:.2f})"
        )
        return result

    # ── feedback re-optimize ─────────────────────────────────────────
    def reoptimize_from_feedback(
        self,
        realized_alpha_scores:    list[float],
        realized_strategy_scores: list[float],
        realized_portfolio_scores:list[float],
        **kwargs,
    ) -> OptimizationResult:
        """
        基于实现反馈重新优化（闭环）。
        用实现值更新评分缓存，然后重新运行 optimize()。
        """
        self.update_alpha_scores(realized_alpha_scores)
        self.update_strategy_scores(realized_strategy_scores)
        self.update_portfolio_scores(realized_portfolio_scores)
        return self.optimize(
            n_alpha    = len(realized_alpha_scores),
            n_strategy = len(realized_strategy_scores),
            n_asset    = len(realized_portfolio_scores),
            **kwargs,
        )

    # ── risk parity mode ─────────────────────────────────────────────
    def risk_parity_optimize(
        self,
        strategy_vols: list[float],
        asset_vols:    list[float],
    ) -> CrossModuleState:
        """风险平价模式：按逆波动率分配权重。"""
        sw = risk_parity_weights(strategy_vols)
        pw = risk_parity_weights(asset_vols)
        n_s, n_a = len(sw), len(pw)
        ei = [0.7] * n_s
        cd = equal_weights(n_s)
        aw = equal_weights(max(n_s, 1))

        s_sc = (self._strategy_scores[:n_s] + [50.0]*n_s)[:n_s]
        p_sc = (self._portfolio_scores[:n_a] + [50.0]*n_a)[:n_a]
        a_sc = [50.0] * len(aw)

        r = compute_cross_module_score(aw, sw, pw, cd, ei, a_sc, s_sc, p_sc)

        self._state = CrossModuleState(
            alpha_weights     = aw,
            strategy_allocs   = sw,
            portfolio_weights = pw,
            capital_dist      = cd,
            exec_intensity    = ei,
            composite_score   = r["composite"],
            alpha_score       = r["alpha_score"],
            strategy_score    = r["strategy_score"],
            portfolio_score   = r["portfolio_score"],
            execution_score   = r["execution_score"],
            capital_score     = r["capital_score"],
            mode              = OptimizationMode.STABILITY,
            iterations        = 1,
            converged         = True,
        )
        self._log(f"[OptimizerEngine] risk_parity: score={r['composite']:.2f}")
        return self._state

    # ── query ────────────────────────────────────────────────────────
    def get_state(self) -> CrossModuleState:
        return self._state

    def get_results(self, n: int = 20) -> list[OptimizationResult]:
        return self._results[-n:]

    def summary(self) -> dict:
        runs = len(self._results)
        best = max((r.final_score for r in self._results), default=0.0)
        last = self._results[-1] if self._results else None
        return {
            "phase":         3,
            "status":        "active",
            "mode":          self._mode.value,
            "total_runs":    runs,
            "best_score":    round(best, 2),
            "last_score":    round(last.final_score, 2) if last else 0.0,
            "last_iter":     last.n_iterations if last else 0,
            "last_converged":last.converged if last else False,
        }
