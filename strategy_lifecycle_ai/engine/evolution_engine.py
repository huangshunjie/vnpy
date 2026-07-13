"""
strategy_lifecycle_ai/engine/evolution_engine.py  (Phase 4)

EvolutionEngine — 策略进化引擎（完整实现）。

实现：
  - evolve()           主进化流水线（自动选型 → 执行 → 记录）
  - mutate()           参数变异
  - adjust_weights()   因子权重调整
  - recombine()        策略重组
  - clone()            强策略克隆
  - get_candidates()   进化候选列表（按进化潜力排名）

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable
import uuid

from ..constant import EvolutionType, DecayLevel, StrategyPhase
from ..model.evolution_model import EvolutionRecord, EvolutionHistory
from ..utils.evolution_utils import (
    mutate_params,
    adjust_factor_weights,
    recombine_strategies,
    clone_strategy,
    select_evolution_type,
    compute_evolution_score,
    evaluate_evolution_success,
    compute_improvement_rate,
    validate_params,
    apply_constraints,
)


class EvolutionEngine:
    """策略进化引擎（Phase 4 完整实现）。"""

    def __init__(
        self,
        log_fn:         Callable | None = None,
        mutation_rate:  float = 0.10,
        clone_rate:     float = 0.05,
        weight_lr:      float = 0.05,
        success_thresh: float = 0.05,
        history_max:    int   = 200,
    ) -> None:
        self._log           = log_fn or (lambda m: None)
        self._mutation_rate = mutation_rate
        self._clone_rate    = clone_rate
        self._weight_lr     = weight_lr
        self._success_thresh = success_thresh
        self._history_max   = history_max

        self._histories:  dict[str, EvolutionHistory] = {}
        self._candidates: dict[str, dict]              = {}   # sid → candidate meta
        self._evolve_count = 0

    # ------------------------------------------------------------------ #
    #  主进化接口
    # ------------------------------------------------------------------ #

    def evolve(
        self,
        strategy_id:   str,
        params:        dict,
        sharpe:        float,
        decay_score:   float,
        live_days:     int,
        win_rate:      float      = 0.5,
        decay_level:   DecayLevel = DecayLevel.NONE,
        weights:       dict | None = None,
        peer_id:       str        = "",
        peer_params:   dict | None = None,
        peer_sharpe:   float      = 0.0,
        trigger_reason: str       = "auto",
        seed:          int | None = None,
    ) -> EvolutionRecord:
        """
        主进化流水线。

        流程：
          1. select_evolution_type() → 决策进化类型
          2. 执行对应进化操作
          3. compute_evolution_score() → 进化潜力评分
          4. 构建 EvolutionRecord
          5. 记录到 EvolutionHistory

        Parameters
        ----------
        strategy_id    : 策略 ID
        params         : 当前策略参数
        sharpe         : 当前 Sharpe
        decay_score    : 当前衰减评分
        live_days      : 运行天数
        win_rate       : 当前胜率
        decay_level    : 当前衰减等级
        weights        : 当前因子权重（可选）
        peer_id        : 重组用的对端策略 ID
        peer_params    : 重组用的对端参数
        peer_sharpe    : 对端 Sharpe
        trigger_reason : 触发原因字符串
        seed           : 随机种子（用于可重现测试）

        Returns
        -------
        EvolutionRecord
        """
        has_strong_peer = bool(peer_params and peer_sharpe > sharpe)

        etype = select_evolution_type(
            sharpe          = sharpe,
            decay_score     = decay_score,
            live_days       = live_days,
            decay_level     = decay_level,
            has_strong_peers = has_strong_peer,
        )

        params_after  = dict(params)
        weights_after = dict(weights) if weights else {}
        peer_used     = ""

        # ── 执行进化操作 ─────────────────────────────────────────────
        if etype == EvolutionType.PARAM_MUTATION:
            params_after = mutate_params(params, self._mutation_rate, seed)

        elif etype == EvolutionType.WEIGHT_ADJUST:
            if weights:
                weights_after = adjust_factor_weights(
                    weights, sharpe, decay_score, self._weight_lr)

        elif etype == EvolutionType.RECOMBINATION:
            if peer_params:
                params_after = recombine_strategies(
                    params, peer_params,
                    ratio = sharpe / (sharpe + peer_sharpe + 1e-9),
                    seed  = seed,
                )
                peer_used = peer_id

        elif etype == EvolutionType.CLONING:
            params_after = clone_strategy(
                params,
                variant_suffix = f"_c{self._evolve_count}",
                mutation_rate  = self._clone_rate,
                seed           = seed,
            )

        # ── 进化潜力评分 ─────────────────────────────────────────────
        evo_score = compute_evolution_score(
            sharpe, decay_score, live_days, win_rate)

        # ── 构建记录 ─────────────────────────────────────────────────
        evo_id = f"EVO_{strategy_id}_{self._evolve_count:04d}"
        record = EvolutionRecord(
            evolution_id   = evo_id,
            strategy_id    = strategy_id,
            evolution_type = etype,
            parent_id      = strategy_id,
            peer_id        = peer_used,
            params_before  = dict(params),
            params_after   = dict(params_after),
            weights_before = dict(weights) if weights else {},
            weights_after  = dict(weights_after),
            trigger_reason = trigger_reason,
            decay_score    = decay_score,
            sharpe_before  = sharpe,
            sharpe_after   = sharpe,    # 进化后 Sharpe 需外部回填
            improvement    = 0.0,
            success        = False,     # 需外部验证后更新
            evolution_score = evo_score,
            evolved_at     = datetime.now(),
        )

        # 更新历史
        if strategy_id not in self._histories:
            self._histories[strategy_id] = EvolutionHistory(
                strategy_id, self._history_max)
        self._histories[strategy_id].append(record)
        self._evolve_count += 1

        self._log(
            f"[EvolutionEngine] {strategy_id}"
            f"  type={etype.value}"
            f"  score={evo_score:.3f}"
            f"  decay={decay_score:.3f}"
            f"  id={evo_id}"
        )
        return record

    # ------------------------------------------------------------------ #
    #  独立操作接口
    # ------------------------------------------------------------------ #

    def mutate(
        self,
        strategy_id: str,
        params:      dict,
        rate:        float | None = None,
        seed:        int | None = None,
    ) -> dict:
        """直接执行参数变异，返回新参数。"""
        return mutate_params(params, rate or self._mutation_rate, seed)

    def adjust_weights(
        self,
        strategy_id: str,
        weights:     dict,
        sharpe:      float,
        decay_score: float,
    ) -> dict:
        """直接执行因子权重调整，返回新权重。"""
        return adjust_factor_weights(weights, sharpe, decay_score, self._weight_lr)

    def recombine(
        self,
        strategy_id: str,
        params_a:    dict,
        params_b:    dict,
        ratio:       float = 0.5,
        seed:        int | None = None,
    ) -> dict:
        """直接执行策略重组，返回新参数。"""
        return recombine_strategies(params_a, params_b, ratio, seed)

    def clone(
        self,
        strategy_id: str,
        params:      dict,
        suffix:      str  = "_clone",
        rate:        float | None = None,
        seed:        int | None = None,
    ) -> dict:
        """直接执行策略克隆，返回新参数。"""
        return clone_strategy(params, suffix, rate or self._clone_rate, seed)

    # ------------------------------------------------------------------ #
    #  进化结果回填（外部验证后调用）
    # ------------------------------------------------------------------ #

    def update_result(
        self,
        evolution_id:  str,
        strategy_id:   str,
        sharpe_after:  float,
    ) -> EvolutionRecord | None:
        """
        回填进化结果（进化后经过验证期得到真实 Sharpe）。

        Parameters
        ----------
        evolution_id  : 进化记录 ID
        strategy_id   : 策略 ID
        sharpe_after  : 验证期后的实际 Sharpe

        Returns
        -------
        EvolutionRecord | None
        """
        h = self._histories.get(strategy_id)
        if h is None:
            return None
        for rec in reversed(h._records):
            if rec.evolution_id == evolution_id:
                rec.sharpe_after = sharpe_after
                rec.improvement  = round(sharpe_after - rec.sharpe_before, 6)
                rec.success      = evaluate_evolution_success(
                    rec.sharpe_before, sharpe_after, self._success_thresh)
                self._log(
                    f"[EvolutionEngine] update_result {evolution_id}"
                    f"  success={rec.success}"
                    f"  improvement={rec.improvement:.4f}"
                )
                return rec
        return None

    # ------------------------------------------------------------------ #
    #  候选策略管理
    # ------------------------------------------------------------------ #

    def register_candidate(
        self,
        strategy_id:  str,
        sharpe:       float,
        decay_score:  float,
        live_days:    int,
        win_rate:     float = 0.5,
        params:       dict | None = None,
    ) -> float:
        """
        注册进化候选策略，计算进化潜力评分。

        Returns
        -------
        float  进化潜力评分 [0,1]
        """
        score = compute_evolution_score(sharpe, decay_score, live_days, win_rate)
        self._candidates[strategy_id] = {
            "strategy_id":  strategy_id,
            "sharpe":       sharpe,
            "decay_score":  decay_score,
            "live_days":    live_days,
            "win_rate":     win_rate,
            "evo_score":    score,
            "params":       dict(params) if params else {},
        }
        return score

    def get_candidates(self, top_n: int = 10) -> list[dict]:
        """
        获取进化候选列表（按进化潜力评分降序）。

        Returns
        -------
        list[dict]  候选策略列表
        """
        sorted_c = sorted(
            self._candidates.values(),
            key=lambda x: x["evo_score"],
            reverse=True,
        )
        return sorted_c[:top_n]

    def get_strong_strategies(
        self,
        min_sharpe: float = 2.0,
        top_n:      int   = 5,
    ) -> list[dict]:
        """
        获取可供重组的强策略列表（高 Sharpe + 低衰减）。
        """
        strong = [
            c for c in self._candidates.values()
            if c["sharpe"] >= min_sharpe and c["decay_score"] < 0.2
        ]
        return sorted(strong, key=lambda x: x["sharpe"], reverse=True)[:top_n]

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_history(
        self,
        strategy_id: str,
        limit: int = 20,
    ) -> list[dict]:
        h = self._histories.get(strategy_id)
        return h.get_records(limit=limit) if h else []

    def get_all_histories(self) -> list[EvolutionHistory]:
        return list(self._histories.values())

    def get_success_rate(self, strategy_id: str) -> float:
        h = self._histories.get(strategy_id)
        return h.success_rate() if h else 0.0

    def get_improvement_series(self, strategy_id: str) -> list[float]:
        h = self._histories.get(strategy_id)
        return h.get_improvement_series() if h else []

    def get_by_type(
        self,
        strategy_id:  str,
        etype:        EvolutionType,
    ) -> list[EvolutionRecord]:
        h = self._histories.get(strategy_id)
        return h.get_by_type(etype) if h else []

    # ------------------------------------------------------------------ #
    #  参数更新
    # ------------------------------------------------------------------ #

    def update_params(self, **kwargs) -> None:
        for k, v in kwargs.items():
            attr = f"_{k}"
            if hasattr(self, attr):
                setattr(self, attr, v)

    # ------------------------------------------------------------------ #
    #  摘要
    # ------------------------------------------------------------------ #

    def summary(self) -> dict:
        total_evolutions = sum(len(h) for h in self._histories.values())
        successful       = sum(
            len(h.get_successful()) for h in self._histories.values())
        return {
            "strategies_with_history": len(self._histories),
            "total_evolutions":        total_evolutions,
            "successful":              successful,
            "success_rate":            round(successful / total_evolutions, 4)
                                       if total_evolutions else 0.0,
            "candidates":              len(self._candidates),
            "phase":                   4,
        }
