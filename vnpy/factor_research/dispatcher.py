"""
factor_research/dispatcher.py

FactorResearchEngine — 因子研究工作台调度层。

数据流（当前阶段）：
  Widget → run(params)
    → 阶段1  load() → DataEngine.load_bars()
    → 阶段2  per-symbol overview → tab:overview  (每合约单独发，概览不合并)
    → 阶段3  per-symbol IC → collect → merge_ic → tab:ic + tab:ic_series
    → 阶段4  per-symbol Decay → collect → merge_decay → tab:decay
    → 阶段5  per-symbol Quantile → collect → merge_quantile → tab:quantile
    → put_finished()

多合约策略：
  - 概览 Tab：每合约独立发送，让用户逐一查看各合约数据质量。
  - IC / Decay / Quantile：全部合约算完后取截面均值，发一次合并结果。
    合并后的 vt_symbol = "截面均值（N 合约）"。
  - 单合约时均值化是 pass-through，无额外开销。
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME
from .engine.data_engine import DataEngine
from .engine.ic_engine import IcEngine
from .engine.decay_engine import DecayEngine
from .engine.quantile_engine import QuantileEngine
from .engine.cross_section import merge_ic, merge_decay, merge_quantile
from .event import (
    EVENT_FACTOR_ERROR,
    EVENT_FACTOR_FINISHED,
    EVENT_FACTOR_LOG,
    EVENT_FACTOR_PLOT_READY,
    EVENT_FACTOR_PROGRESS,
)
from .model import FactorParams, IcStats, DecayResult, QuantileResult, LoadResult

if TYPE_CHECKING:
    from .engine.factor_engine import FactorEngine
    from .engine.redundancy_engine import RedundancyEngine
    from .engine.score_engine import ScoreEngine
    from .engine.stability_engine import StabilityEngine
    from .engine.report_engine import ReportEngine


class FactorResearchEngine(BaseEngine):
    """
    因子研究工作台调度引擎。

    DataEngine / IcEngine / DecayEngine / QuantileEngine 构造时立即初始化。
    重计算统一在后台线程执行，不阻塞 Qt 主线程。
    """

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self.data_engine:     DataEngine     = DataEngine()
        self.ic_engine:       IcEngine       = IcEngine()
        self.decay_engine:    DecayEngine    = DecayEngine()
        self.quantile_engine: QuantileEngine = QuantileEngine()

        self.factor_engine:     FactorEngine     | None = None
        self.redundancy_engine: RedundancyEngine | None = None
        self.score_engine:      ScoreEngine      | None = None
        self.stability_engine:  StabilityEngine  | None = None
        self.report_engine:     ReportEngine     | None = None

        self._stop_flag: bool = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ #
    #  公开调度接口
    # ------------------------------------------------------------------ #

    def run(self, params: dict[str, Any] | None = None) -> None:
        """启动因子计算流程（后台线程，不阻塞 Qt）。"""
        if self._thread and self._thread.is_alive():
            self.write_log("计算正在进行中，请等待完成或点击停止")
            return
        self._stop_flag = False
        fp = FactorParams.from_dict(params) if params else FactorParams()
        self._thread = threading.Thread(
            target=self._run_in_thread, args=(fp,), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            self._stop_flag = True
            self.write_log("停止信号已发出，等待当前任务完成…")
        else:
            self.write_log("当前无正在运行的任务")
            self.put_finished()

    def load(self, fp: FactorParams) -> list[LoadResult]:
        results: list[LoadResult] = []
        if not fp.symbols:
            self.write_log("symbols 列表为空，跳过数据加载")
            return results
        total = len(fp.symbols)
        for idx, vt_symbol in enumerate(fp.symbols, 1):
            if self._stop_flag:
                self.write_log("数据加载已中止")
                break
            self.write_log(f"[{idx}/{total}] 加载 {vt_symbol} ...")
            result = self.data_engine.load_bars(
                vt_symbol=vt_symbol,
                start=fp.start,
                end=fp.end,
                frequency=fp.frequency,
            )
            results.append(result)
            self.write_log(f"  {'✓' if result.success else '✗'} {result}")
            self.put_progress(f"数据加载进度：{idx}/{total} ({idx/total:.0%})")
        return results

    def dispatch(self, task: Any | None = None) -> None:
        self.write_log("dispatch() 接口预留，待后续阶段实现")

    def collect(self) -> dict[str, Any]:
        self.write_log("collect() 接口预留，待后续阶段实现")
        return {}

    # ------------------------------------------------------------------ #
    #  后台线程
    # ------------------------------------------------------------------ #

    def _run_in_thread(self, fp: FactorParams) -> None:
        try:
            n_sym = len(fp.symbols)
            name  = fp.factor_name or fp.factor_type or "unknown"
            self.write_log(
                f"开始计算：factor={name}  合约={n_sym}个  "
                f"lag={fp.lag}  n_quantiles={fp.n_quantiles}  "
                f"max_lag={fp.max_lag}  {fp.start} ~ {fp.end}"
            )

            # ── 阶段 1：数据加载 ──────────────────────────────────────
            load_results = self.load(fp)
            ok = sum(1 for r in load_results if r.success)
            self.write_log(
                f"数据加载完成：{ok}/{len(load_results)} 个合约成功"
                if load_results else "无合约需要加载数据"
            )
            if self._stop_flag:
                self.put_finished(); return

            valid_results = [lr for lr in load_results if lr.success]
            momentum_window = self._parse_momentum_window(fp.factor_name)
            factor_name_str = fp.factor_name or f"momentum_{momentum_window}"

            # ── 阶段 2：因子概览（每合约独立发，不合并）─────────────────
            for lr in valid_results:
                if self._stop_flag: break
                df = self.data_engine.get_bars(lr.cache_key)
                if df is None: continue
                summary = DataEngine.compute_overview(lr.vt_symbol, lr.interval, df)
                self.event_engine.put(Event(
                    EVENT_FACTOR_PLOT_READY, {"tab": "overview", "payload": summary}
                ))
                self.write_log(f"概览计算完成：{lr.vt_symbol} {lr.count} bars")

            if self._stop_flag:
                self.put_finished(); return

            # ── 阶段 3：IC 统计 + IC 时序（收集 → 截面均值 → 发一次）──────
            ic_list: list[IcStats] = []
            total_ic = len(valid_results)
            for i, lr in enumerate(valid_results, 1):
                if self._stop_flag: break
                df = self.data_engine.get_bars(lr.cache_key)
                if df is None: continue
                self.put_progress(
                    f"IC 计算：{lr.vt_symbol} [{i}/{total_ic}]"
                )
                ic_stats = self.ic_engine.compute(
                    df, vt_symbol=lr.vt_symbol,
                    factor_name=factor_name_str,
                    momentum_window=momentum_window,
                    lag=fp.lag,
                )
                ic_list.append(ic_stats)
                self.write_log(
                    f"IC [{i}/{total_ic}] {lr.vt_symbol}  "
                    f"IC={ic_stats.ic_mean:.4f}  ICIR={ic_stats.icir:.4f}"
                )

            merged_ic = merge_ic(ic_list)
            if merged_ic is not None:
                self.event_engine.put(Event(
                    EVENT_FACTOR_PLOT_READY, {"tab": "ic", "payload": merged_ic}
                ))
                self.event_engine.put(Event(
                    EVENT_FACTOR_PLOT_READY, {"tab": "ic_series", "payload": merged_ic}
                ))
                self.write_log(
                    f"IC 截面均值（{merged_ic.n_symbols} 合约）  "
                    f"IC={merged_ic.ic_mean:.4f}  ICIR={merged_ic.icir:.4f}"
                )

            # Send per-symbol IC list for correlation / redundancy analysis
            if ic_list:
                self.event_engine.put(Event(
                    EVENT_FACTOR_PLOT_READY,
                    {"tab": "correlation", "payload": ic_list},
                ))

            if self._stop_flag:
                self.put_finished(); return

            # ── 阶段 4：IC Decay（收集 → 截面均值 → 发一次）──────────────
            decay_list: list[DecayResult] = []
            total_decay = len(valid_results)
            for i, lr in enumerate(valid_results, 1):
                if self._stop_flag: break
                df = self.data_engine.get_bars(lr.cache_key)
                if df is None: continue

                def _progress(cur: int, tot: int, sym: str = lr.vt_symbol) -> None:
                    self.put_progress(
                        f"IC Decay：{sym} [{i}/{total_decay}] lag={cur}/{tot}"
                    )

                decay_result = self.decay_engine.compute(
                    df, vt_symbol=lr.vt_symbol,
                    factor_name=factor_name_str,
                    momentum_window=momentum_window,
                    max_lag=fp.max_lag,
                    progress_callback=_progress,
                )
                decay_list.append(decay_result)
                self.write_log(
                    f"IC Decay [{i}/{total_decay}] {lr.vt_symbol}  "
                    f"best_lag={decay_result.best_lag}"
                )

            merged_decay = merge_decay(decay_list)
            if merged_decay is not None:
                self.event_engine.put(Event(
                    EVENT_FACTOR_PLOT_READY, {"tab": "decay", "payload": merged_decay}
                ))
                self.write_log(
                    f"IC Decay 截面均值（{merged_decay.n_symbols} 合约）  "
                    f"best_lag={merged_decay.best_lag}"
                )

            if self._stop_flag:
                self.put_finished(); return

            # ── 阶段 5：分层收益（收集 → 截面均值 → 发一次）──────────────
            q_list: list[QuantileResult] = []
            total_q = len(valid_results)
            for i, lr in enumerate(valid_results, 1):
                if self._stop_flag: break
                df = self.data_engine.get_bars(lr.cache_key)
                if df is None: continue
                self.put_progress(
                    f"分层收益：{lr.vt_symbol} [{i}/{total_q}]"
                )
                q_result = self.quantile_engine.compute(
                    df, vt_symbol=lr.vt_symbol,
                    factor_name=factor_name_str,
                    momentum_window=momentum_window,
                    lag=fp.lag,
                    n_quantiles=fp.n_quantiles,
                )
                q_list.append(q_result)
                self.write_log(
                    f"分层收益 [{i}/{total_q}] {lr.vt_symbol}  "
                    f"单调性={q_result.monotonicity_score:.4f}"
                )

            merged_q = merge_quantile(q_list)
            if merged_q is not None:
                self.event_engine.put(Event(
                    EVENT_FACTOR_PLOT_READY,
                    {"tab": "quantile", "payload": merged_q},
                ))
                self.write_log(
                    f"分层收益截面均值（{merged_q.n_symbols} 合约）  "
                    f"单调性={merged_q.monotonicity_score:.4f}  "
                    f"L-S年化={merged_q.long_short_annualized:.4f}"
                )

            # 阶段 6～N 在此追加

            self.put_finished()

        except Exception as exc:
            self.write_error(f"计算异常：{exc}")

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_momentum_window(factor_name: str) -> int:
        if not factor_name:
            return 20
        parts = factor_name.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])
        return 20

    # ------------------------------------------------------------------ #
    #  事件广播
    # ------------------------------------------------------------------ #

    def write_log(self, msg: str) -> None:
        self.event_engine.put(Event(EVENT_FACTOR_LOG, msg))

    def write_error(self, msg: str) -> None:
        self.event_engine.put(Event(EVENT_FACTOR_ERROR, msg))

    def put_progress(self, data: Any) -> None:
        self.event_engine.put(Event(EVENT_FACTOR_PROGRESS, data))

    def put_finished(self, data: Any = None) -> None:
        self.event_engine.put(Event(EVENT_FACTOR_FINISHED, data))

    # ------------------------------------------------------------------ #
    #  BaseEngine 覆写
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        self._stop_flag = True
        self.data_engine.clear()
        self.write_log("FactorResearchEngine 已关闭")
