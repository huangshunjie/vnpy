"""
research_validation/engine.py

ResearchValidationEngine — Research Validation System 主引擎（Phase 1 骨架）。

职责：
  - 作为 VeighNa MainEngine 管理的 BaseEngine 子类
  - 持有所有子验证引擎实例
  - 接收 UI 的 run_validation(params) 指令，在后台线程中协调验证流程
  - 把验证结果以 Event 形式发回 UI

Phase 1：
  - 引擎初始化完整（子引擎全部实例化为 stub）
  - run_validation() / stop() 骨架就绪
  - 所有分析逻辑禁止实现（Phase 2+ 填充）
"""

from __future__ import annotations

import threading

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME, ValidationStatus
from .event import (
    EVENT_VALIDATION_START,
    EVENT_VALIDATION_PROGRESS,
    EVENT_VALIDATION_RESULT,
    EVENT_VALIDATION_ERROR,
    EVENT_VALIDATION_LOG,
    EVENT_VALIDATION_CANCEL,
)
from .engine.validation_engine import ValidationEngine
from .engine.walkforward_engine import WalkForwardEngine
from .engine.oos_engine import OOSEngine
from .engine.regime_engine import RegimeEngine
from .engine.stability_engine import StabilityEngine
from .engine.bias_engine import BiasEngine
from .datasource.database_loader    import DatabaseLoader
from .engine.validation_engine      import ValidationEngine as CoreValidationEngine
from .model.validation_model        import ValidationParams


class ResearchValidationEngine(BaseEngine):
    """
    Research Validation System 主引擎（dispatcher 层）。

    VeighNa 通过 main_engine.get_engine(APP_NAME) 返回本实例，
    ValidationWidget 持有该引用以调用 run_validation() / stop()。

    ❌ Phase 1：禁止任何分析逻辑，全部为 stub。
    """

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        # 子引擎（Phase 2+ 实现分析逻辑）
        self.validation_engine  = ValidationEngine()
        self.walkforward_engine = WalkForwardEngine()
        self.oos_engine         = OOSEngine()
        self.regime_engine      = RegimeEngine()
        self.stability_engine   = StabilityEngine()
        self.bias_engine        = BiasEngine()

        # 数据接口
        self.db_loader = DatabaseLoader()

        # 运行状态
        self._status: ValidationStatus = ValidationStatus.IDLE
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        # Phase 2: 外部注入数据（来自 Factor Research / DatabaseManager）
        self._injected_data = None
        self._last_result   = None

    # ------------------------------------------------------------------ #
    #  BaseEngine 生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        """引擎初始化（MainEngine 启动时调用）。"""
        self.write_log("Research Validation System 初始化完成（Phase 1）。")

    def close(self) -> None:
        """引擎关闭（MainEngine 退出时调用）。"""
        self.stop()
        self.write_log("Research Validation System 已关闭。")

    # ------------------------------------------------------------------ #
    #  公开接口（Phase 1 骨架）
    # ------------------------------------------------------------------ #

    def run_validation(self, params: dict) -> None:
        """
        启动验证任务（后台线程）。

        Phase 1：仅记录日志，不执行任何分析。
        Phase 2+：在后台线程中依次调用各子引擎。

        Parameters
        ----------
        params : dict
            验证参数，格式由 ValidationParams（Phase 2）定义。
        """
        if self._status == ValidationStatus.RUNNING:
            self.write_log("[WARN] 验证任务正在运行，请先停止。")
            return

        self._stop_event.clear()
        self._status = ValidationStatus.RUNNING
        self.dispatch_event(EVENT_VALIDATION_START, params)
        self.write_log(f"验证任务启动（参数：{params}）。")

        self._thread = threading.Thread(
            target=self._run_in_thread,
            args=(params,),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """停止当前验证任务。"""
        if self._status != ValidationStatus.RUNNING:
            return
        self._stop_event.set()
        self._status = ValidationStatus.CANCELLED
        self.dispatch_event(EVENT_VALIDATION_CANCEL, "user_cancelled")
        self.write_log("验证任务已取消。")

    def get_status(self) -> ValidationStatus:
        """返回当前验证状态。"""
        return self._status

    # ------------------------------------------------------------------ #
    #  内部执行（Phase 1：stub，Phase 2+ 填充）
    # ------------------------------------------------------------------ #

    def _run_in_thread(self, params: dict) -> None:
        """后台线程入口（Phase 2 实现：Walk Forward + OOS）。"""
        try:
            self._publish_progress(0.0, "验证任务启动...")

            vp = ValidationParams(
                factor_name     = str(params.get("factor_name",    "unknown")),
                train_window    = int(params.get("train_window",   252)),
                test_window     = int(params.get("test_window",    63)),
                step_size       = int(params.get("step_size",      21)),
                oos_ratio       = float(params.get("oos_ratio",    0.3)),
                run_walkforward = bool(params.get("run_walkforward", True)),
                run_oos         = bool(params.get("run_oos",         True)),
                run_regime      = bool(params.get("run_regime",      True)),
                run_stability   = bool(params.get("run_stability",   True)),
                run_bias        = bool(params.get("run_bias",        True)),
                regime_lookback = int(params.get("regime_lookback",  60)),
            )

            if self._stop_event.is_set():
                self._status = ValidationStatus.CANCELLED
                return

            self._publish_progress(0.05, "加载因子/收益数据...")
            factor_cs, return_cs, dates = self._load_data(vp)

            if self._stop_event.is_set():
                self._status = ValidationStatus.CANCELLED
                return

            core = CoreValidationEngine()
            core.set_stop_event(self._stop_event)

            result = core.run(
                params      = vp,
                factor_cs   = factor_cs,
                return_cs   = return_cs,
                dates       = dates,
                progress_cb = self._publish_progress,
            )

            self._last_result = result
            self._status = ValidationStatus.COMPLETED
            self.dispatch_event(EVENT_VALIDATION_RESULT, result)
            self.write_log(
                f"[完成] 综合评分={result.overall_score:.1f}  "
                f"Alpha={'真实' if result.is_real_alpha else '可疑'}"
            )

        except Exception as exc:
            import traceback
            self._status = ValidationStatus.FAILED
            self.dispatch_event(EVENT_VALIDATION_ERROR, {
                "error":     str(exc),
                "traceback": traceback.format_exc(),
            })
            self.write_log(f"[ERROR] 验证任务失败：{exc}")

    def _publish_progress(self, progress: float, message: str) -> None:
        self.dispatch_event(
            EVENT_VALIDATION_PROGRESS,
            {"progress": progress, "message": message},
        )

    # ------------------------------------------------------------------ #
    #  事件发布
    # ------------------------------------------------------------------ #

    def dispatch_event(self, event_type: str, data) -> None:
        """统一事件发布入口。"""
        self.event_engine.put(Event(event_type, data))

    def write_log(self, msg: str) -> None:
        """发布日志事件。"""
        self.dispatch_event(EVENT_VALIDATION_LOG, msg)

    # ------------------------------------------------------------------ #
    #  Phase 2: 数据接口
    # ------------------------------------------------------------------ #

    def _load_data(
        self,
        params: 'ValidationParams',
    ) -> tuple:
        """
        加载因子 / 收益截面数据。

        优先使用 set_data() 注入的数据；若未注入，生成合成演示数据
        （真实情况由 Factor Research / DatabaseManager 提供）。
        """
        if self._injected_data is not None:
            return self._injected_data

        # 合成演示数据：正态因子 + 弱相关收益（IC ≈ 0.05）
        import random
        from datetime import date, timedelta
        random.seed(42)
        symbols   = [f"S{i:04d}" for i in range(100)]
        n_periods = params.train_window + params.test_window + params.step_size * 3
        base_date = date(2020, 1, 1)
        dates_    = [base_date + timedelta(days=i) for i in range(n_periods)]

        factor_cs_, return_cs_ = [], []
        for _ in range(n_periods):
            fv = {s: random.gauss(0.0, 1.0) for s in symbols}
            rv = {s: 0.05 * fv[s] + random.gauss(0.0, 1.0) for s in symbols}
            factor_cs_.append(fv)
            return_cs_.append(rv)

        self.write_log(
            f"[数据] 使用合成演示数据：{n_periods} 期  {len(symbols)} 个标的"
        )
        return factor_cs_, return_cs_, dates_

    def set_data(
        self,
        factor_cs: list,
        return_cs: list,
        dates:     list,
    ) -> None:
        """
        外部注入真实数据（来自 Factor Research / DatabaseManager）。
        注入后 _load_data() 将直接使用，不再生成合成数据。
        """
        self._injected_data = (factor_cs, return_cs, dates)
        n = len(factor_cs[0]) if factor_cs else 0
        self.write_log(
            f"[数据] 已注入 {len(dates)} 期数据  {n} 个标的"
        )

    def clear_data(self) -> None:
        """清除注入数据，恢复合成演示模式。"""
        self._injected_data = None

    def get_last_result(self):
        """返回最近一次验证结果（ValidationResult | None）。"""
        return self._last_result
