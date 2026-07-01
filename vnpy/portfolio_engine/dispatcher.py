"""
portfolio_engine/dispatcher.py

PortfolioEngine — Portfolio Engine 调度层（BaseEngine 实现）。

职责：
  - 作为 VeighNa MainEngine 管理的 BaseEngine 子类
  - 持有所有子引擎实例（AllocationEngine / PerformanceEngine 等）
  - 接收 UI 的 run(params) 指令，在后台线程中协调数据加载与计算
  - 把计算结果以 Event 的形式发回 UI

数据流（Phase 2 实现）：
  run(params)
    → thread: _run_in_thread(params)
        → DatabaseLoader.load() per slot
        → AllocationEngine.compute()
        → PerformanceEngine.compute()
        → event_engine.put(EVENT_PORTFOLIO_UPDATE, payload)

Phase 1：
  - 引擎初始化完整（子引擎全部实例化）
  - run() / stop() 骨架就绪
  - _run_in_thread() 为 NotImplementedError（Phase 2 实现）
"""

from __future__ import annotations

import threading

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME
from .datasource.database_loader import DatabaseLoader
from .engine.allocation_engine import AllocationEngine
from .engine.attribution_engine import AttributionEngine
from .engine.performance_engine import PerformanceEngine
from .engine.portfolio_engine import PortfolioStateEngine
from .engine.rebalance_engine import RebalanceEngine
from .engine.risk_engine import RiskEngine
from .engine.factor_bridge import FactorBridge
from .event import (
    EVENT_PORTFOLIO_LOG,
    EVENT_PORTFOLIO_UPDATE,
    EVENT_PORTFOLIO_RISK,
    EVENT_PORTFOLIO_REBALANCE,
)


class PortfolioEngine(BaseEngine):
    """
    Portfolio Engine 调度层。

    VeighNa 会通过 main_engine.get_engine(APP_NAME) 返回本实例，
    PortfolioEngineWidget 持有该引用以调用 run() / stop()。
    """

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        # 数据入口（唯一）
        self.db_loader = DatabaseLoader()

        # 子引擎（全部实例化，Phase 2/3 逐步实现）
        self.portfolio_state  = PortfolioStateEngine()
        self.allocation_engine = AllocationEngine()
        self.performance_engine = PerformanceEngine()
        self.risk_engine       = RiskEngine()
        self.rebalance_engine  = RebalanceEngine()
        self.attribution_engine = AttributionEngine()
        self.factor_bridge     = FactorBridge()

        # 运行控制
        self._thread: threading.Thread | None = None
        self._stop_flag: bool = False

    # ------------------------------------------------------------------ #
    #  主接口（Phase 2 实现 _run_in_thread）
    # ------------------------------------------------------------------ #

    def run(self, params: dict) -> None:
        """
        在后台线程中执行组合构建流程。

        Parameters
        ----------
        params : dict，来自 LeftPanel.collect_params()
            {
              "portfolio_name": str,
              "benchmark_symbol": str,
              "start": date,
              "end": date,
              "weight_method": WeightMethod,
              "rebalance_freq": RebalanceFreq,
              "slots": list[dict],   # [{"name", "symbol", "type"}, ...]
            }
        """
        if self._thread and self._thread.is_alive():
            self.write_log("当前有任务正在运行，请等待完成或点击停止。")
            return

        self._stop_flag = False
        self._thread = threading.Thread(
            target=self._run_in_thread,
            args=(params,),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """请求停止当前运行中的后台线程。"""
        self._stop_flag = True
        self.write_log("停止信号已发送，等待当前步骤完成…")

    # ------------------------------------------------------------------ #
    #  后台线程主体（Phase 2 实现）
    # ------------------------------------------------------------------ #

    def _run_in_thread(self, params: dict) -> None:
        """後台線程：資料載入 → 權重計算 → 績效統計 → 發 Event（Phase 2）。"""
        import pandas as pd
        import traceback
        from .model.portfolio_model import Portfolio, StrategySlot
        from .constant import StrategyType
        from .utils.math_utils import returns_from_nav

        try:
            portfolio_name = params.get("portfolio_name", "Portfolio_1")
            weight_method  = params["weight_method"]
            rebalance_freq = params["rebalance_freq"]
            start          = params["start"]
            end            = params["end"]
            benchmark_sym  = params.get("benchmark_symbol", "")
            slot_dicts     = params.get("slots", [])

            portfolio = Portfolio(
                name=portfolio_name,
                weight_method=weight_method,
                rebalance_freq=rebalance_freq,
                start=start,
                end=end,
                benchmark_symbol=benchmark_sym,
            )
            for sd in slot_dicts:
                portfolio.add_slot(StrategySlot(
                    name=sd["name"],
                    symbols=[sd["symbol"]] if sd.get("symbol") else [],
                    strategy_type=sd.get("type", StrategyType.CUSTOM),
                ))

            self.portfolio_state.set_portfolio(portfolio)
            self.rebalance_engine.clear_history()
            self.write_log(f"组合已构建：{portfolio_name}（{portfolio.n_slots} 个槽位）")

            if self._stop_flag:
                self.write_log("已停止。"); self._put_idle(); return

            # ── 阶段 2：逐槽位加载数据 ────────────────────────────────
            returns_map: dict[str, pd.Series] = {}
            for slot in portfolio.slots:
                if self._stop_flag:
                    break
                if not slot.symbols:
                    self.write_log(f"槽位 {slot.name!r} 未指定合约，跳过。")
                    continue
                sym = slot.symbols[0]
                self.write_log(f"加载数据：{slot.name} → {sym}")
                try:
                    df = self.db_loader.load(sym, start, end, interval="daily")
                    if df is None or df.empty:
                        self.write_log(f"  {sym} 无数据，跳过。"); continue
                    ret = df["close"].pct_change().dropna()
                    returns_map[slot.name] = ret
                    self.write_log(f"  {sym} OK  {len(ret)} 条")
                except Exception as e:
                    self.write_log(f"  {sym} 加载失败：{e}")

            if self._stop_flag:
                self.write_log("已停止。"); self._put_idle(); return

            if not returns_map:
                self.write_log("无有效收益率数据，运行终止。")
                self._put_idle(); return

            # ── 阶段 3：权重分配 ──────────────────────────────────────
            self.write_log(f"计算权重（方法：{weight_method.value}）…")
            allocation = self.allocation_engine.compute(portfolio, returns_map)
            self.portfolio_state.update_allocation(allocation)

            if not allocation.is_valid:
                self.write_log("权重计算失败，运行终止。")
                self._put_idle(); return

            w_str = "  ".join(f"{k}={v:.3f}" for k, v in allocation.weights.items())
            self.write_log(f"权重：{w_str}")

            if self._stop_flag:
                self.write_log("已停止。"); self._put_idle(); return

            # ── 阶段 4：绩效统计 ──────────────────────────────────────
            self.write_log("计算组合绩效…")
            performance = self.performance_engine.compute(
                portfolio, allocation, returns_map
            )
            self.portfolio_state.update_performance(performance)

            if performance.is_valid:
                self.write_log(
                    f"绩效：年化={performance.annual_return:.2%}  "
                    f"Sharpe={performance.sharpe_ratio:.2f}  "
                    f"MDD={performance.max_drawdown:.2%}"
                )
            else:
                self.write_log("绩效计算返回无效结果（数据不足）。")

            # ── 阶段 5：调仓历史扫描 ──────────────────────────────────
            self._simulate_rebalance(portfolio, allocation)

            if self._stop_flag:
                self.write_log("已停止。"); self._put_idle(); return

            # ── 阶段 6：发送 EVENT_PORTFOLIO_UPDATE ──────────────────
            payload = {
                "portfolio":         portfolio,
                "allocation":        allocation,
                "performance":       performance,
                "rebalance_history": self.rebalance_engine.get_history(),
                "returns_map":       returns_map,
            }
            self.event_engine.put(Event(EVENT_PORTFOLIO_UPDATE, payload))
            # ── 阶段 7：风险 + 归因 → EVENT_PORTFOLIO_RISK ──────────────
            if self._stop_flag:
                self.write_log("已停止。"); self._put_idle(); return

            self.write_log("计算风险暴露与回撤归因…")
            self.write_log("Computing risk & attribution...")
            try:
                risk_exposure = self.risk_engine.compute(
                    portfolio=portfolio,
                    nav_series=performance.nav_series,
                    returns_map=returns_map,
                    weights=allocation.weights,
                    benchmark_returns=None,
                )
                attribution = self.attribution_engine.compute(
                    portfolio=portfolio,
                    allocation=allocation,
                    nav_series=performance.nav_series,
                    returns_map=returns_map,
                )
                risk_payload = {
                    "risk":        risk_exposure,
                    "attribution": attribution,
                }
                self.event_engine.put(Event(EVENT_PORTFOLIO_RISK, risk_payload))
                beta_val = risk_exposure.portfolio_beta
                self.write_log(
                    f"Risk: Beta={'nan' if beta_val != beta_val else f'{beta_val:.3f}'}  "
                    f"MDD period="
                    f"{risk_exposure.drawdown_start.strftime('%Y-%m-%d') if risk_exposure.drawdown_start else 'N/A'}"
                    f" ~ "
                    f"{risk_exposure.drawdown_end.strftime('%Y-%m-%d') if risk_exposure.drawdown_end else 'N/A'}"
                )
            except Exception as e:
                self.write_log(f"Risk/attribution warning (non-critical): {e}")
            self.write_log("✓ 运行完成，结果已发送至 UI。")

        except Exception as exc:
            self.write_log(f"运行出错：{exc}")
            self.write_log(traceback.format_exc())
        finally:
            self._put_idle()

    def _simulate_rebalance(self, portfolio, allocation) -> None:
        """按调仓频率在历史净值上扫描，记录每次触发节点（静态权重）。"""
        perf = self.portfolio_state.get_performance()
        if perf is None or perf.nav_series is None or perf.nav_series.empty:
            return
        prev_w: dict[str, float] = {}
        last_dt = None
        for dt in perf.nav_series.index:
            cur = dt.to_pydatetime() if hasattr(dt, "to_pydatetime") else dt
            if self.rebalance_engine.should_rebalance(
                portfolio.rebalance_freq, last_dt, cur
            ):
                self.rebalance_engine.record(
                    triggered_at=cur,
                    prev_weights=dict(prev_w),
                    new_weights=dict(allocation.weights),
                    reason="scheduled",
                )
                prev_w  = dict(allocation.weights)
                last_dt = cur

    def _put_idle(self) -> None:
        """通知 UI 恢复 idle 状态。"""
        self.event_engine.put(Event(EVENT_PORTFOLIO_LOG, "__IDLE__"))

    # ------------------------------------------------------------------ #
    #  日志工具
    # ------------------------------------------------------------------ #

    def write_log(self, msg: str) -> None:
        """发送日志事件到 UI 日志栏。"""
        self.event_engine.put(Event(EVENT_PORTFOLIO_LOG, msg))

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """VeighNa 关闭时调用，确保后台线程安全退出。"""
        self.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
