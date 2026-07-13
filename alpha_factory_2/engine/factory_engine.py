"""
alpha_factory_2/engine/factory_engine.py

FactoryEngine — Alpha Factory 2.0 内核（Phase 1 Stub）。

持有 5 个子引擎占位符，Phase 2-5 逐步填充：
  - generator_engine   : GeneratorEngine   Phase 2
  - scoring_engine     : ScoringEngine     Phase 3
  - screening_engine   : ScreeningEngine   Phase 4
  - lifecycle_engine   : LifecycleEngine   Phase 5
  - portfolio_builder  : (reserved)        Phase 5+

❌ 禁止任何交易逻辑
❌ 禁止直接调用 Execution / Portfolio / Risk
✔  仅通过 EventEngine 广播事件
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import AlphaStatus, APP_NAME
from ..event import (
    EVENT_ALPHA_GENERATED,
    EVENT_ALPHA_SCORED,
    EVENT_ALPHA_SCREENED,
    EVENT_ALPHA_REJECTED,
    EVENT_ALPHA_LIVE,
    EVENT_ALPHA_RETIRED,
)
from ..model.alpha_model import AlphaSignal
from ..model.score_model import AlphaScore
from ..model.lifecycle_model import AlphaLifecycle
from .generator_engine  import GeneratorEngine
from .scoring_engine    import ScoringEngine
from .screening_engine  import ScreeningEngine
from .lifecycle_engine  import LifecycleEngine


class FactoryEngine:
    """
    Alpha Factory 内核（Phase 1）。

    Phase 1: 仅骨架，所有子引擎均为 stub 实例。
    Phase 2: GeneratorEngine 接入真实因子组合逻辑。
    Phase 3: ScoringEngine 接入 IC/RankIC/Stability 评分。
    Phase 4: ScreeningEngine 接入阈值筛选 + 自动淘汰。
    Phase 5: LifecycleEngine 接入状态机 + 自动迁移。
    """

    def __init__(self, event_put_fn: Callable) -> None:
        self._put        = event_put_fn
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None

        # 子引擎（Phase 1: 所有均为 stub 实例）
        from ..datasource.factor_loader import FactorLoader
        self._factor_loader    = FactorLoader()
        self.generator_engine  = GeneratorEngine(
            factor_loader = self._factor_loader,
            log_fn        = self._log,
        )
        from ..datasource.validation_loader import ValidationLoader
        self._validation_loader = ValidationLoader(
            factor_loader=self._factor_loader
        )
        self.scoring_engine    = ScoringEngine(
            validation_loader = self._validation_loader,
            factor_loader     = self._factor_loader,
            log_fn            = self._log,
        )
        self.screening_engine  = ScreeningEngine(log_fn=self._log)
        from .lifecycle_engine import LifecycleThresholds
        self.lifecycle_engine  = LifecycleEngine(
            thresholds = LifecycleThresholds(),
            log_fn     = self._log,
        )
        self.portfolio_builder = None   # Phase 5+ 预留

        # Alpha 注册表
        self._alphas: dict[str, AlphaSignal] = {}
        self._scores: dict[str, AlphaScore]  = {}

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        """初始化内核。"""
        self._log(f"[FactoryEngine] init()  app={APP_NAME}")

    def start(self) -> None:
        """启动内核。"""
        self._started_at = datetime.now()
        self._log("[FactoryEngine] start()")
        self._publish(EVENT_ALPHA_GENERATED, {"action": "start"})

    def stop(self) -> None:
        """停止内核。"""
        self._stopped_at = datetime.now()
        self._log("[FactoryEngine] stop()")

    # ------------------------------------------------------------------ #
    #  Alpha 生产流水线（Phase 1: stub 流程）
    # ------------------------------------------------------------------ #

    def generate_alpha(
        self,
        factors:    list[str] | None = None,
        alpha_type: str = "linear_combo",
        **kwargs,
    ) -> AlphaSignal | None:
        """
        生成一个 Alpha 信号（Phase 1: 返回 None）。
        Phase 2 实现真实生成逻辑。
        """
        from ..constant import AlphaType
        try:
            atype = AlphaType(alpha_type)
        except ValueError:
            atype = AlphaType.LINEAR_COMBO

        alpha = self.generator_engine.generate(
            factors    = factors if factors else None,
            alpha_type = atype,
            **kwargs,
        )

        self._alphas[alpha.alpha_id] = alpha
        self.lifecycle_engine.register(alpha)
        self._publish(EVENT_ALPHA_GENERATED, alpha.to_dict())
        self._log(f"[FactoryEngine] generated {alpha.alpha_id}")
        return alpha

    def batch_generate(
        self,
        n:              int,
        factors:        list[str] | None = None,
        alpha_type:     str = "random",
        weight_method:  str = "dirichlet",
        allow_negative: bool = False,
    ) -> list[AlphaSignal]:
        """
        批量生成 n 个 Alpha 候选（Phase 2）。
        """
        from ..constant import AlphaType
        try:
            atype = AlphaType(alpha_type)
        except ValueError:
            atype = AlphaType.RANDOM

        alphas = self.generator_engine.batch_generate(
            n              = n,
            factors        = factors,
            alpha_type     = atype,
            weight_method  = weight_method,
            allow_negative = allow_negative,
        )
        for alpha in alphas:
            self._alphas[alpha.alpha_id] = alpha
            self.lifecycle_engine.register(alpha)
            self._publish(EVENT_ALPHA_GENERATED, alpha.to_dict())
        self._log(
            f"[FactoryEngine] batch_generate: {len(alphas)} alphas generated"
        )
        return alphas

    def score_alpha(self, alpha_id: str) -> AlphaScore | None:
        """
        对指定 Alpha 评分（Phase 1: 返回全零评分）。
        Phase 3 实现真实评分。
        """
        alpha = self._alphas.get(alpha_id)
        if alpha is None:
            self._log(f"[FactoryEngine] score_alpha: {alpha_id} not found")
            return None

        score = self.scoring_engine.score(alpha)
        self._scores[alpha_id] = score
        alpha.status = AlphaStatus.SCORED
        self.lifecycle_engine.transition(
            alpha_id, AlphaStatus.SCORED, "scored by ScoringEngine"
        )
        self._publish(EVENT_ALPHA_SCORED, score.to_dict())
        self._log(
            f"[FactoryEngine] scored {alpha_id}"  
            f"  IC={score.ic:.4f}  IR={score.stability:.3f}"
            f"  total={score.total_score:.4f}"
        )
        return score

    # ------------------------------------------------------------------ #
    #  事件分发
    # ------------------------------------------------------------------ #

    def batch_score(
        self,
        alpha_ids: list[str] | None = None,
    ) -> list:
        """
        批量评分（Phase 3）。
        alpha_ids=None 则对所有未评分 Alpha 评分。
        """
        if alpha_ids is None:
            targets = [
                a for a in self._alphas.values()
                if a.alpha_id not in self._scores
            ]
        else:
            targets = [
                self._alphas[aid]
                for aid in alpha_ids
                if aid in self._alphas
            ]

        scores = self.scoring_engine.batch_score(targets)
        for score in scores:
            self._scores[score.alpha_id] = score
            if score.alpha_id in self._alphas:
                self._alphas[score.alpha_id].status = AlphaStatus.SCORED
            self.lifecycle_engine.transition(
                score.alpha_id, AlphaStatus.SCORED, "batch scored"
            )
            self._publish(EVENT_ALPHA_SCORED, score.to_dict())

        self._log(
            f"[FactoryEngine] batch_score: {len(scores)} scored"
        )
        return scores

    def get_score_ranking(self, top_n: int = 50) -> list:
        """
        返回按 total_score 降序排列的评分列表（Phase 3）。
        """
        scores = list(self._scores.values())
        return self.scoring_engine.top_n(scores, n=top_n)

    # ------------------------------------------------------------------ #
    #  Screening 流水线（Phase 4）
    # ------------------------------------------------------------------ #

    def screen_alphas(
        self,
        alpha_ids: list[str] | None = None,
    ) -> tuple[list[AlphaSignal], list[AlphaSignal]]:
        """
        对已评分 Alpha 执行筛选（Phase 4）。
        alpha_ids=None 则筛选所有已评分但未筛选的 Alpha。

        Returns
        -------
        (passed_list, rejected_list)
        """
        if alpha_ids is None:
            candidates = [
                a for a in self._alphas.values()
                if a.alpha_id in self._scores
                and a.status == AlphaStatus.SCORED
            ]
        else:
            candidates = [
                self._alphas[aid]
                for aid in alpha_ids
                if aid in self._alphas
            ]

        scores = [self._scores[a.alpha_id] for a in candidates
                  if a.alpha_id in self._scores]

        passed, rejected = self.screening_engine.batch_screen(
            candidates, scores
        )

        for alpha in passed:
            alpha.status = AlphaStatus.SCREENED
            self.lifecycle_engine.transition(
                alpha.alpha_id, AlphaStatus.SCREENED, "passed screening"
            )
            self._publish(EVENT_ALPHA_SCREENED, alpha.to_dict())

        for alpha in rejected:
            alpha.status = AlphaStatus.REJECTED
            self.lifecycle_engine.transition(
                alpha.alpha_id, AlphaStatus.REJECTED, "failed screening"
            )
            self._publish(EVENT_ALPHA_REJECTED, alpha.to_dict())

        self._log(
            f"[FactoryEngine] screen_alphas: "
            f"passed={len(passed)}  rejected={len(rejected)}"
        )
        return passed, rejected

    def run_full_pipeline(
        self,
        n:              int  = 10,
        factors:        list[str] | None = None,
        alpha_type:     str  = "random",
        weight_method:  str  = "dirichlet",
        allow_negative: bool = False,
    ) -> dict:
        """
        全流水线：生成 → 评分 → 筛选（Phase 4）。

        Returns
        -------
        dict  containing passed / rejected / scores
        """
        alphas  = self.batch_generate(n=n, factors=factors,
                                      alpha_type=alpha_type,
                                      weight_method=weight_method,
                                      allow_negative=allow_negative)
        ids     = [a.alpha_id for a in alphas]
        scores  = self.batch_score(alpha_ids=ids)
        passed, rejected = self.screen_alphas(alpha_ids=ids)

        # 退役检查
        retired_ids: list[str] = []
        for alpha in passed:
            sc = self._scores.get(alpha.alpha_id)
            if sc and self.screening_engine.check_retirement(
                alpha.alpha_id, sc
            ):
                alpha.status = AlphaStatus.RETIRED
                self.lifecycle_engine.transition(
                    alpha.alpha_id, AlphaStatus.RETIRED, "auto retired"
                )
                self._publish(EVENT_ALPHA_RETIRED, alpha.to_dict())
                retired_ids.append(alpha.alpha_id)

        self._log(
            f"[FactoryEngine] full_pipeline: "
            f"generated={len(alphas)}  scored={len(scores)}  "
            f"passed={len(passed)}  rejected={len(rejected)}  "
            f"retired={len(retired_ids)}"
        )
        return {
            "generated": len(alphas),
            "scored":    len(scores),
            "passed":    [a.to_dict() for a in passed],
            "rejected":  [a.to_dict() for a in rejected],
            "retired":   retired_ids,
        }

    def update_screening_thresholds(self, **kwargs) -> None:
        """动态更新筛选阈值（Phase 4）。"""
        self.screening_engine.update_thresholds(**kwargs)

    # ------------------------------------------------------------------ #
    #  Lifecycle 管理（Phase 5）
    # ------------------------------------------------------------------ #

    def promote_to_live(
        self,
        alpha_ids: list[str] | None = None,
    ) -> list[str]:
        """
        将通过筛选的 Alpha 推进到 LIVE 状态（Phase 5）。
        alpha_ids=None 则处理所有 SCREENED 状态的 Alpha。
        """
        if alpha_ids is None:
            targets = [
                lc.alpha_id
                for lc in self.lifecycle_engine.list_by_status(
                    AlphaStatus.SCREENED
                )
            ]
        else:
            targets = alpha_ids

        promoted: list[str] = []
        for aid in targets:
            sc = self._scores.get(aid)
            al = self._alphas.get(aid)
            if al is None:
                continue
            if sc is not None:
                result = self.lifecycle_engine.auto_evaluate(al, sc)
                if result == AlphaStatus.LIVE:
                    al.status = AlphaStatus.LIVE
                    self._publish(EVENT_ALPHA_LIVE, al.to_dict())
                    promoted.append(aid)
            else:
                if self.lifecycle_engine.transition(
                    aid, AlphaStatus.LIVE, "manual promote"
                ):
                    al.status = AlphaStatus.LIVE
                    self._publish(EVENT_ALPHA_LIVE, al.to_dict())
                    promoted.append(aid)

        self._log(f"[FactoryEngine] promote_to_live: {len(promoted)} alphas")
        return promoted

    def auto_evaluate_all(self) -> dict:
        """
        对所有 LIVE / DEGRADED 状态的 Alpha 执行自动迁移评估（Phase 5）。

        Returns
        -------
        dict  {live, degraded, retired} 各状态变化数量
        """
        targets = (
            self.lifecycle_engine.list_by_status(AlphaStatus.LIVE)
            + self.lifecycle_engine.list_by_status(AlphaStatus.DEGRADED)
        )
        counters = {"live": 0, "degraded": 0, "retired": 0}

        for lc in targets:
            al = self._alphas.get(lc.alpha_id)
            sc = self._scores.get(lc.alpha_id)
            if al is None or sc is None:
                continue
            new_status = self.lifecycle_engine.auto_evaluate(al, sc)
            if new_status is not None:
                al.status = new_status
                key = new_status.value
                if key in counters:
                    counters[key] += 1
                if new_status == AlphaStatus.LIVE:
                    self._publish(EVENT_ALPHA_LIVE, al.to_dict())
                elif new_status == AlphaStatus.RETIRED:
                    self._publish(EVENT_ALPHA_RETIRED, al.to_dict())

        self._log(
            f"[FactoryEngine] auto_evaluate_all: {counters}"
        )
        return counters

    def run_full_pipeline_v2(
        self,
        n:              int  = 10,
        factors:        list[str] | None = None,
        alpha_type:     str  = "random",
        weight_method:  str  = "dirichlet",
        allow_negative: bool = False,
        auto_live:      bool = True,
    ) -> dict:
        """
        完整五阶段流水线（Phase 5）：
          生成 → 评分 → 筛选 → 促进 LIVE → 自动评估退役
        """
        result = self.run_full_pipeline(
            n=n, factors=factors, alpha_type=alpha_type,
            weight_method=weight_method,
            allow_negative=allow_negative,
        )
        promoted: list[str] = []
        if auto_live:
            promoted = self.promote_to_live()
        eval_result = self.auto_evaluate_all()
        result["promoted"]    = promoted
        result["auto_eval"]   = eval_result
        return result

    def get_lifecycle_summary(self) -> dict:
        """返回生命周期完整摘要（Phase 5）。"""
        return self.lifecycle_engine.summary()

    def get_alpha_timeline(self, alpha_id: str) -> list:
        """返回单个 Alpha 的迁移时间轴（Phase 5）。"""
        return self.lifecycle_engine.get_timeline(alpha_id)

    def update_lifecycle_thresholds(self, **kwargs) -> None:
        """动态更新生命周期自动迁移阈值（Phase 5）。"""
        self.lifecycle_engine.update_thresholds(**kwargs)

    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        """向全局事件总线分发事件。"""
        self._publish(event_type, data or {})

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def uptime_seconds(self) -> float:
        if self._started_at is None:
            return 0.0
        end = self._stopped_at or datetime.now()
        return (end - self._started_at).total_seconds()

    def get_summary(self) -> dict:
        lc_summ = self.lifecycle_engine.summary()
        ge_summ = self.generator_engine.summary()
        return {
            "app":       APP_NAME,
            "uptime":    round(self.uptime_seconds, 1),
            "alphas":    len(self._alphas),
            "scores":    len(self._scores),
            "lifecycle": lc_summ,
            "generator": ge_summ,
            "scoring":   self.scoring_engine.summary(),
            "screening":  self.screening_engine.summary(),
            "lifecycle":  self.lifecycle_engine.summary(),
        }

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _publish(self, event_type: str, data: dict) -> None:
        from vnpy.event import Event
        e      = Event(event_type)
        e.data = data
        self._put(e)

    def _log(self, msg: str) -> None:
        self._publish("eAlphaFactory.log", {"message": msg})
