"""
execution_engine/dispatcher.py

ExecutionEngine — 交易执行系统主引擎（Phase 2 实现）。

职责：
  - 持有 ExecutionCoreEngine（子引擎编排层）
  - 实现 send_order()：OrderRequest → 执行流水线 → VeighNa 事件
  - 实现 process_event()：监听上游事件（Portfolio/CTA 信号）
  - 桥接 VeighNa EventEngine 与内部纯计算子引擎
"""

from __future__ import annotations

import threading
import traceback

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME
from .event import (
    EVENT_EXECUTION_LOG,
    EVENT_ORDER_UPDATE,
    EVENT_FILL_UPDATE,
    EVENT_EXECUTION_ERROR,
)
from .engine.execution_engine import ExecutionCoreEngine
from .engine.slippage_engine import SlippageConfig, SlippageModel
from .engine.fill_engine import FillConfig
from .engine.cost_engine import CostConfig, CommissionMode
from .model.order_model import Order, OrderRequest
from .model.fill_model import FillRecord
from .model.execution_model import ExecutionRecord
from .model.signal_model import BatchOrderRequest
from .engine.signal_adapter import SignalAdapter
from .event import (
    EVENT_PORTFOLIO_SIGNAL, EVENT_CTA_SIGNAL,
    EVENT_FACTOR_SIGNAL, EVENT_BATCH_ORDER_REQ, EVENT_EXECUTION_DONE,
)


class ExecutionEngine(BaseEngine):
    """
    交易执行系统主引擎（Phase 2 实现）。

    对外接口：
      start()      : 启动引擎，注册子引擎回调
      stop()       : 停止引擎
      send_order() : 接收 OrderRequest，驱动执行流水线
      process_event(): 处理上游事件
    """

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
        engine_name: str = APP_NAME,
    ) -> None:
        super().__init__(main_engine, event_engine, engine_name)

        # 执行核心引擎（纯计算，无 VeighNa 依赖）
        self.core = ExecutionCoreEngine(
            slippage_config=SlippageConfig(
                model=SlippageModel.FIXED,
                tick_size=0.01,
                ticks=1,
            ),
            fill_config=FillConfig(),
            cost_config=CostConfig(
                commission_mode=CommissionMode.RATE_ON_NOTIONAL,
                commission_rate=0.0003,
            ),
        )

        self.signal_adapter = SignalAdapter(min_volume=0.01, lot_size=1.0)
        self._running: bool = False
        self._lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """启动引擎：注册子引擎回调，准备接收信号。"""
        if self._running:
            self.write_log("执行引擎已在运行中。")
            return

        # 注册内部回调 → VeighNa 事件桥接
        self.core.register_callbacks(
            on_order_update     = self._on_order_update,
            on_fill_update      = self._on_fill_update,
            on_execution_record = self._on_execution_record,
        )

        # 注册上游信号事件（Phase 4）
        reg = self.event_engine.register
        reg(EVENT_PORTFOLIO_SIGNAL, self._on_portfolio_signal)
        reg(EVENT_CTA_SIGNAL,       self._on_cta_signal)
        reg(EVENT_FACTOR_SIGNAL,    self._on_factor_signal)
        reg(EVENT_BATCH_ORDER_REQ,  self._on_batch_order)

        self._running = True
        self.write_log("执行引擎已启动。滑点模型=固定  成交模式=立即全成")

    def stop(self) -> None:
        """停止引擎，取消所有活跃订单。"""
        if not self._running:
            return
        with self._lock:
            for order in self.core.order_engine.get_active():
                self.core.order_engine.cancel(order.order_id, reason="engine_stopped")
        # 注销上游信号事件
        unreg = self.event_engine.unregister
        unreg(EVENT_PORTFOLIO_SIGNAL, self._on_portfolio_signal)
        unreg(EVENT_CTA_SIGNAL,       self._on_cta_signal)
        unreg(EVENT_FACTOR_SIGNAL,    self._on_factor_signal)
        unreg(EVENT_BATCH_ORDER_REQ,  self._on_batch_order)

        self._running = False
        self.write_log("执行引擎已停止。")

    def close(self) -> None:
        self.stop()

    # ------------------------------------------------------------------ #
    #  核心接口
    # ------------------------------------------------------------------ #

    def send_order(self, order_req: "OrderRequest | dict") -> str:
        """
        接收执行信号，驱动完整执行流水线。

        Parameters
        ----------
        order_req : OrderRequest 或兼容字典（含 symbol/direction/volume/signal_price）

        Returns
        -------
        str  order_id（成功）或 "" （失败）
        """
        if not self._running:
            self.write_log("[WARN] 引擎未启动，请先点击「启动引擎」。")
            return ""

        # 字典兼容（来自 UI 手动下单）
        if isinstance(order_req, dict):
            try:
                order_req = OrderRequest(
                    symbol       = str(order_req["symbol"]),
                    direction    = str(order_req["direction"]),
                    volume       = float(order_req["volume"]),
                    signal_price = float(order_req["signal_price"]),
                    order_type   = str(order_req.get("order_type", "MARKET")),
                    limit_price  = float(order_req.get("limit_price", 0.0)),
                    source       = str(order_req.get("source", "manual")),
                )
            except (KeyError, ValueError, TypeError) as e:
                self._put_error(f"订单参数错误：{e}")
                return ""

        try:
            with self._lock:
                order, fills, record = self.core.execute(order_req)

            self.write_log(
                f"执行完成 [{order.order_id}] {order.symbol} "
                f"{order.direction} "
                f"成交={order.filled_volume:.2f}/{order.volume:.2f} "
                f"均价={order.avg_fill_price:.4f} "
                f"状态={order.status.value}"
            )
            return order.order_id

        except Exception as exc:
            self._put_error(f"执行出错：{exc}\n{traceback.format_exc()}")
            return ""

    def process_event(self, event: Event) -> None:
        """
        通用事件处理入口（Phase 4）。
        按 event.type 路由到对应处理器。
        """
        if not self._running:
            return
        data = event.data
        if not isinstance(data, dict):
            return
        requests, skipped = self.signal_adapter.from_dict(data)
        if skipped:
            for s in skipped:
                self.write_log(f"[SKIP] {s}")
        self._execute_requests(requests)


    # ------------------------------------------------------------------ #
    #  Phase 4：上游信号处理器
    # ------------------------------------------------------------------ #

    def _on_portfolio_signal(self, event: Event) -> None:
        """Portfolio Engine 调仓信号 → 批量执行。"""
        if not self._running or not isinstance(event.data, dict):
            return
        data = dict(event.data)
        data.setdefault("type", "portfolio")
        requests, skipped = self.signal_adapter.from_portfolio(data)
        if skipped:
            for s in skipped: self.write_log(f"[PORTFOLIO_SKIP] {s}")
        self.write_log(f"[PORTFOLIO] 调仓信号 {len(requests)} 笔")
        self._execute_requests(requests)

    def _on_cta_signal(self, event: Event) -> None:
        """CTA 策略信号 → 单笔执行。"""
        if not self._running or not isinstance(event.data, dict):
            return
        requests, skipped = self.signal_adapter.from_cta(event.data)
        if skipped:
            for s in skipped: self.write_log(f"[CTA_SKIP] {s}")
        self._execute_requests(requests)

    def _on_factor_signal(self, event: Event) -> None:
        """Factor Research 信号 → 批量执行。"""
        if not self._running or not isinstance(event.data, dict):
            return
        data = dict(event.data)
        data.setdefault("type", "factor")
        requests, skipped = self.signal_adapter.from_factor(data)
        if skipped:
            for s in skipped: self.write_log(f"[FACTOR_SKIP] {s}")
        self.write_log(f"[FACTOR] 信号 {len(requests)} 笔")
        self._execute_requests(requests)

    def _on_batch_order(self, event: Event) -> None:
        """批量订单请求 → BatchOrderRequest 执行。"""
        if not self._running:
            return
        batch = event.data
        if isinstance(batch, BatchOrderRequest):
            requests, skipped = self.signal_adapter.from_batch(batch)
            if skipped:
                for s in skipped: self.write_log(f"[BATCH_SKIP] {s}")
            self.write_log(f"[BATCH] {batch.source.value} {len(requests)} 笔")
            self._execute_requests(requests)

    def _execute_requests(self, requests) -> list:
        """批量执行 OrderRequest 列表，返回 order_id 列表。"""
        order_ids = []
        for req in requests:
            oid = self.send_order(req)
            if oid:
                order_ids.append(oid)
        if requests:
            # 发送执行完成反馈事件
            stats = self.core.compute_stats()
            self.event_engine.put(Event(EVENT_EXECUTION_DONE, {
                "batch_count":   len(requests),
                "filled_count":  len(order_ids),
                "avg_fill_rate": stats.avg_fill_rate,
                "total_cost":    self.core.compute_cost_summary().total_cost,
            }))
        return order_ids

    # ------------------------------------------------------------------ #
    #  配置更新（供 UI 调用）
    # ------------------------------------------------------------------ #

    def update_slippage_config(self, config: "SlippageConfig") -> None:
        """更新滑点配置（SlippageTab → dispatcher）。"""
        self.core.update_slippage_config(config)
        self.write_log(
            f"滑点配置已更新：model={config.model.value}  "
            f"ticks={config.ticks}  rate={config.rate:.4%}  "
            f"vol_factor={config.vol_factor:.3f}"
        )

    def update_fill_config(self, config: "FillConfig") -> None:
        """更新成交配置（UI → dispatcher）。"""
        self.core.update_fill_config(config)
        self.write_log(f"成交模式已更新：{config.mode.value}")

    def update_cost_config(self, config: "CostConfig") -> None:
        """更新成本配置（CostTab → dispatcher）。"""
        self.core.update_cost_config(config)
        self.write_log(
            f"成本配置已更新：commission_rate={config.commission_rate:.4%}  "
            f"impact_factor={config.impact_factor:.3f}"
        )

    def get_cost_summary(self):
        """返回成本汇总（供 UI 展示）。"""
        return self.core.compute_cost_summary()

    def get_cost_breakdowns(self):
        """返回各笔成本明细列表。"""
        return self.core.get_cost_breakdowns()

    def get_execution_stats(self):
        """返回执行统计（供 UI 展示）。"""
        return self.core.compute_stats()

    def get_execution_history(self):
        """返回执行记录历史。"""
        return self.core.get_history()

    def get_all_orders(self):
        """返回所有订单（活跃 + 历史）。"""
        return self.core.order_engine.get_all()

    def update_signal_adapter(self, min_volume: float = 0.01,
                              lot_size: float = 1.0) -> None:
        """更新 SignalAdapter 参数（UI 可调用）。"""
        self.signal_adapter.min_volume = min_volume
        self.signal_adapter.lot_size   = lot_size
        self.write_log(f"SignalAdapter 更新：min_vol={min_volume}  lot={lot_size}")

    # ------------------------------------------------------------------ #
    #  内部回调（子引擎 → VeighNa 事件）
    # ------------------------------------------------------------------ #

    def _on_order_update(self, order: "Order") -> None:
        """OrderEngine 状态变更 → EVENT_ORDER_UPDATE。"""
        self.event_engine.put(Event(EVENT_ORDER_UPDATE, order))

    def _on_fill_update(self, fill: "FillRecord") -> None:
        """FillEngine 成交 → EVENT_FILL_UPDATE。"""
        self.event_engine.put(Event(EVENT_FILL_UPDATE, fill))

    def _on_execution_record(self, record: "ExecutionRecord") -> None:
        """执行记录生成 → 日志（含成本）。"""
        self.write_log(
            f"  [记录] {record.symbol} {record.direction} "
            f"滑点={record.slippage:.4f} ({record.slippage_pct:.3%})  "
            f"成本={record.total_cost:.4f} ({record.total_cost_pct:.4%})  "
            f"成交率={record.fill_rate:.1%}"
        )

    def _put_error(self, msg: str) -> None:
        self.event_engine.put(Event(EVENT_EXECUTION_ERROR, msg))
        self.write_log(f"[ERROR] {msg}")

    # ------------------------------------------------------------------ #
    #  日志工具
    # ------------------------------------------------------------------ #

    def write_log(self, msg: str) -> None:
        self.event_engine.put(Event(EVENT_EXECUTION_LOG, msg))
