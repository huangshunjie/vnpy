"""
alpha_factory_2/dispatcher.py

AlphaFactoryEngine — 顶层引擎（Phase 1 Stub）。

作为 VeighNa BaseEngine 子类，桥接 MainEngine / EventEngine
与内部 FactoryEngine 内核。

Phase 1：仅实现 init / start / stop / generate_alpha / score_alpha / dispatch_event。
❌ 禁止任何交易逻辑。
"""

from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME
from .engine.factory_engine import FactoryEngine
from .model.alpha_model import AlphaSignal
from .model.score_model import AlphaScore


class AlphaFactoryEngine(BaseEngine):
    """
    Alpha Factory 2.0 顶层引擎（Phase 1）。

    职责：
      - 作为 VeighNa MainEngine 的子引擎注册入口
      - 持有 FactoryEngine 内核实例
      - 代理 init / start / stop / generate_alpha / score_alpha
      - Phase 2-5 逐步暴露子引擎接口
    """

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._engine: FactoryEngine | None = None

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        """初始化内核。"""
        if self._engine is None:
            self._engine = FactoryEngine(
                event_put_fn=self.event_engine.put
            )
        self._engine.init()

    def start(self) -> None:
        """启动系统。"""
        if self._engine is None:
            self.init()
        self._engine.start()

    def stop(self) -> None:
        """停止系统。"""
        if self._engine is None:
            return
        self._engine.stop()

    # ------------------------------------------------------------------ #
    #  Alpha 生产接口
    # ------------------------------------------------------------------ #

    def generate_alpha(
        self,
        factors:    list[str] | None = None,
        alpha_type: str = "linear_combo",
        **kwargs,
    ) -> AlphaSignal | None:
        """
        生成一个 Alpha 信号。
        Phase 1: 返回 None（stub）。
        Phase 2 实现真实生成逻辑。
        """
        if self._engine is None:
            self.init()
        return self._engine.generate_alpha(
            factors=factors, alpha_type=alpha_type, **kwargs
        )

    def score_alpha(self, alpha_id: str) -> AlphaScore | None:
        """
        对指定 Alpha 评分。
        Phase 1: 返回全零评分（stub）。
        Phase 3 实现真实评分。
        """
        if self._engine is None:
            return None
        return self._engine.score_alpha(alpha_id)

    # ------------------------------------------------------------------ #
    #  事件分发
    # ------------------------------------------------------------------ #

    def dispatch_event(
        self,
        event_type: str,
        data:       dict | None = None,
    ) -> None:
        """向全局事件总线分发事件。"""
        if self._engine is None:
            self.init()
        self._engine.dispatch_event(event_type, data or {})

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def factory_engine(self) -> FactoryEngine | None:
        return self._engine

    # ------------------------------------------------------------------ #
    #  Alpha 生成接口（Phase 2）
    # ------------------------------------------------------------------ #

    def batch_generate(
        self,
        n:              int,
        factors:        list[str] | None = None,
        alpha_type:     str = "random",
        weight_method:  str = "dirichlet",
        allow_negative: bool = False,
    ) -> list:
        """批量生成 n 个 Alpha 候选（Phase 2）。"""
        if self._engine is None:
            self.init()
        return self._engine.batch_generate(
            n=n, factors=factors,
            alpha_type=alpha_type,
            weight_method=weight_method,
            allow_negative=allow_negative,
        )

    def list_available_factors(self) -> list[str]:
        """列出可用因子列表。"""
        if self._engine is None:
            self.init()
        return self._engine._factor_loader.list_available_factors()

    def get_generator_summary(self) -> dict:
        """返回生成器状态摘要。"""
        if self._engine is None:
            return {}
        return self._engine.generator_engine.summary()

    def list_alphas(self) -> list:
        """返回所有已生成 Alpha 的快照列表（to_dict）。"""
        if self._engine is None:
            return []
        return [a.to_dict() for a in self._engine._alphas.values()]

    # ------------------------------------------------------------------ #
    #  Alpha 评分接口（Phase 3）
    # ------------------------------------------------------------------ #

    def batch_score(self, alpha_ids: list[str] | None = None) -> list:
        """批量评分。alpha_ids=None 则对所有未评分 Alpha 评分。"""
        if self._engine is None:
            self.init()
        return self._engine.batch_score(alpha_ids)

    def score_alpha(self, alpha_id: str):
        """对单个 Alpha 评分。"""
        if self._engine is None:
            self.init()
        return self._engine.score_alpha(alpha_id)

    def get_score_ranking(self, top_n: int = 50) -> list:
        """返回按 total_score 降序排列的评分列表。"""
        if self._engine is None:
            return []
        return self._engine.get_score_ranking(top_n=top_n)

    def get_scoring_summary(self) -> dict:
        """返回评分引擎状态摘要。"""
        if self._engine is None:
            return {}
        return self._engine.scoring_engine.summary()

    def list_scores(self) -> list:
        """返回所有已评分 Alpha 的评分字典列表。"""
        if self._engine is None:
            return []
        return [s.to_dict() for s in self._engine._scores.values()]

    # ------------------------------------------------------------------ #
    #  Alpha 筛选接口（Phase 4）
    # ------------------------------------------------------------------ #

    def screen_alphas(self, alpha_ids: list[str] | None = None) -> tuple:
        """筛选已评分 Alpha，返回 (passed, rejected)。"""
        if self._engine is None:
            self.init()
        return self._engine.screen_alphas(alpha_ids)

    def run_full_pipeline(
        self,
        n:              int  = 10,
        factors:        list[str] | None = None,
        alpha_type:     str  = "random",
        weight_method:  str  = "dirichlet",
        allow_negative: bool = False,
    ) -> dict:
        """全流水线：生成 → 评分 → 筛选（Phase 4）。"""
        if self._engine is None:
            self.init()
        return self._engine.run_full_pipeline(
            n=n, factors=factors, alpha_type=alpha_type,
            weight_method=weight_method, allow_negative=allow_negative,
        )

    def update_screening_thresholds(self, **kwargs) -> None:
        """动态更新筛选阈值，如 update_screening_thresholds(ic_min=0.03)。"""
        if self._engine:
            self._engine.update_screening_thresholds(**kwargs)

    def get_screening_summary(self) -> dict:
        """返回筛选引擎状态摘要。"""
        if self._engine is None:
            return {}
        return self._engine.screening_engine.summary()

    def get_screening_records(self, limit: int = 200) -> list:
        """返回最近 limit 条筛选记录。"""
        if self._engine is None:
            return []
        return self._engine.screening_engine.get_screening_records(limit)

    def get_retire_records(self, limit: int = 100) -> list:
        """返回退役记录列表。"""
        if self._engine is None:
            return []
        return self._engine.screening_engine.get_retire_records(limit)

    def get_screening_thresholds(self) -> dict:
        """返回当前筛选阈值。"""
        if self._engine is None:
            return {}
        return self._engine.screening_engine.get_thresholds()

    # ------------------------------------------------------------------ #
    #  Alpha 生命周期接口（Phase 5）
    # ------------------------------------------------------------------ #

    def promote_to_live(self, alpha_ids: list[str] | None = None) -> list[str]:
        """将 SCREENED Alpha 推进到 LIVE 状态。"""
        if self._engine is None:
            self.init()
        return self._engine.promote_to_live(alpha_ids)

    def auto_evaluate_all(self) -> dict:
        """对所有 LIVE / DEGRADED Alpha 执行自动迁移评估。"""
        if self._engine is None:
            self.init()
        return self._engine.auto_evaluate_all()

    def run_full_pipeline_v2(
        self,
        n:              int  = 10,
        factors:        list[str] | None = None,
        alpha_type:     str  = "random",
        weight_method:  str  = "dirichlet",
        allow_negative: bool = False,
        auto_live:      bool = True,
    ) -> dict:
        """五阶段完整流水线：生成→评分→筛选→LIVE→自动退役。"""
        if self._engine is None:
            self.init()
        return self._engine.run_full_pipeline_v2(
            n=n, factors=factors, alpha_type=alpha_type,
            weight_method=weight_method,
            allow_negative=allow_negative,
            auto_live=auto_live,
        )

    def get_lifecycle_summary(self) -> dict:
        """返回生命周期状态分布摘要。"""
        if self._engine is None:
            return {}
        return self._engine.get_lifecycle_summary()

    def get_alpha_timeline(self, alpha_id: str) -> list:
        """返回单个 Alpha 的迁移时间轴。"""
        if self._engine is None:
            return []
        return self._engine.get_alpha_timeline(alpha_id)

    def update_lifecycle_thresholds(self, **kwargs) -> None:
        """动态更新生命周期自动迁移阈值。"""
        if self._engine:
            self._engine.update_lifecycle_thresholds(**kwargs)

    def list_live_alphas(self) -> list:
        """返回所有 LIVE 状态的 Alpha 字典列表。"""
        if self._engine is None:
            return []
        from .constant import AlphaStatus as _AS
        lcs = self._engine.lifecycle_engine.list_by_status(_AS.LIVE)
        return [
            self._engine._alphas[lc.alpha_id].to_dict()
            for lc in lcs
            if lc.alpha_id in self._engine._alphas
        ]

    def get_summary(self) -> dict:
        if self._engine is None:
            return {"app": APP_NAME, "status": "not_initialized"}
        s = self._engine.get_summary()
        # 补充 dispatcher 层字段，保持与其他引擎摘要一致
        s.setdefault("state",  "running")
        s.setdefault("health", "unknown")
        return s
