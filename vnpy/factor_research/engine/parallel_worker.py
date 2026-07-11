"""
factor_research/engine/parallel_worker.py

ParallelWorker — 多进程并行计算调度层。

架构：
  - 主线程（Qt）调用 run_batch()，内部用 ProcessPoolExecutor 并行处理股票
  - 每个子进程执行 _compute_one_symbol()：纯计算，无 Qt/EventEngine 依赖
  - 子进程结果通过 Future.result() 回收到主调线程，再由 dispatcher 发 Event
  - stop_flag 通过闭包传入，每批次 Future 提交前检查

设计约束：
  - 子进程函数必须是模块级 top-level 函数（pickle 要求）
  - DataFrame 通过 pickle 序列化传入子进程（ProcessPoolExecutor 默认）
  - 子进程不得持有任何 Qt 对象引用
  - Windows 下必须在 if __name__ == "__main__" 保护下启动进程池；
    本模块在 dispatcher 后台线程中调用，dispatcher 线程已由主进程启动，
    无需额外保护，但子进程 spawn 时会重新 import 本模块，因此模块级代码
    必须是安全的（无副作用）。

进程数策略：
  max_workers = min(cpu_count, 8, len(symbols))
  不超过 8 防止内存压力（每进程约 50~100MB）
"""

from __future__ import annotations

import os
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from .ic_engine import IcEngine
from .decay_engine import DecayEngine
from .quantile_engine import QuantileEngine
from ..model import DecayResult, IcStats, QuantileResult


# ------------------------------------------------------------------ #
#  子进程计算参数（pickle 友好的纯数据容器）
# ------------------------------------------------------------------ #

@dataclass
class SymbolTask:
    """单个股票的计算任务参数，pickle 序列化传入子进程。"""
    vt_symbol:        str
    factor_name:      str
    momentum_window:  int
    lag:              int
    n_quantiles:      int
    max_lag:          int


@dataclass
class SymbolResult:
    """单个股票的计算结果，从子进程返回主进程。"""
    vt_symbol:   str
    ic_stats:    IcStats        | None
    decay:       DecayResult    | None
    quantile:    QuantileResult | None
    error:       str            = ""

    @property
    def success(self) -> bool:
        return self.error == "" and self.ic_stats is not None


# ------------------------------------------------------------------ #
#  子进程入口函数（必须是 top-level，pickle 可序列化）
# ------------------------------------------------------------------ #

def _compute_one_symbol(
    df: "pd.DataFrame",
    task: SymbolTask,
) -> SymbolResult:
    """
    子进程中对单只股票执行全量计算：IC + Decay + Quantile。

    使用 compute_fast() 向量化接口，比原始接口快 10~20 倍。
    发生任何异常时返回 error 字段，不抛出（防止子进程崩溃影响整批）。
    """
    try:
        ic_engine      = IcEngine()
        decay_engine   = DecayEngine()
        quantile_engine = QuantileEngine()

        ic_stats = ic_engine.compute_fast(
            df,
            vt_symbol=task.vt_symbol,
            factor_name=task.factor_name,
            momentum_window=task.momentum_window,
            lag=task.lag,
        )

        decay = decay_engine.compute_fast(
            df,
            vt_symbol=task.vt_symbol,
            factor_name=task.factor_name,
            momentum_window=task.momentum_window,
            max_lag=task.max_lag,
        )

        quantile = quantile_engine.compute(
            df,
            vt_symbol=task.vt_symbol,
            factor_name=task.factor_name,
            momentum_window=task.momentum_window,
            lag=task.lag,
            n_quantiles=task.n_quantiles,
        )

        return SymbolResult(
            vt_symbol=task.vt_symbol,
            ic_stats=ic_stats,
            decay=decay,
            quantile=quantile,
        )

    except Exception:
        return SymbolResult(
            vt_symbol=task.vt_symbol,
            ic_stats=None,
            decay=None,
            quantile=None,
            error=traceback.format_exc(),
        )


# ------------------------------------------------------------------ #
#  ParallelWorker
# ------------------------------------------------------------------ #

class ParallelWorker:
    """
    多进程并行计算调度器。

    使用方法：
        worker = ParallelWorker(max_workers=4)
        results = worker.run_batch(
            df_map,        # {vt_symbol: DataFrame}
            tasks,         # {vt_symbol: SymbolTask}
            stop_flag_fn,  # () -> bool，返回 True 时中止
            progress_cb,   # (done, total, vt_symbol) -> None
        )
    """

    def __init__(self, max_workers: int | None = None) -> None:
        cpu = os.cpu_count() or 1
        self._max_workers = min(max_workers or cpu, 8)

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def run_batch(
        self,
        df_map:       dict[str, "pd.DataFrame"],
        tasks:        dict[str, SymbolTask],
        stop_flag_fn: Callable[[], bool],
        progress_cb:  Callable[[int, int, str], None] | None = None,
    ) -> list[SymbolResult]:
        """
        并行计算一批股票。

        参数：
            df_map       : {vt_symbol -> DataFrame}（已由 DataEngine 加载）
            tasks        : {vt_symbol -> SymbolTask}
            stop_flag_fn : 返回 True 时停止提交新任务，等待已提交任务完成
            progress_cb  : (done_count, total, current_symbol) -> None

        返回：
            list[SymbolResult]，顺序与提交顺序一致（内部用 as_completed 收割）
        """
        symbols = list(tasks.keys())
        total   = len(symbols)
        results: list[SymbolResult] = []

        if total == 0:
            return results

        # Windows spawn 模式下，ProcessPoolExecutor 在后台线程中需要
        # 显式指定 mp_context，确保使用 spawn 而非 fork
        import multiprocessing
        ctx = multiprocessing.get_context("spawn")

        with ProcessPoolExecutor(
            max_workers=self._max_workers,
            mp_context=ctx,
        ) as executor:
            future_to_sym: dict[Future, str] = {}

            for sym in symbols:
                if stop_flag_fn():
                    break
                df   = df_map.get(sym)
                task = tasks.get(sym)
                if df is None or task is None:
                    continue
                future = executor.submit(_compute_one_symbol, df, task)
                future_to_sym[future] = sym

            done = 0
            for future in as_completed(future_to_sym):
                sym = future_to_sym[future]
                done += 1
                try:
                    result: SymbolResult = future.result(timeout=120)
                except Exception as exc:
                    result = SymbolResult(
                        vt_symbol=sym,
                        ic_stats=None,
                        decay=None,
                        quantile=None,
                        error=str(exc),
                    )
                results.append(result)
                if progress_cb is not None:
                    progress_cb(done, total, sym)

        return results
