"""
quant_os/engine/event_bus.py

EventBus — Quant OS 全局事件总线（Phase 2 实现）。

职责：
  - 作为 OS 级事件的统一路由层（在 VeighNa EventEngine 之上）
  - 支持按 event_type 订阅 / 取消订阅
  - 支持通配符订阅（前缀匹配，如 "eQuantOS.*"）
  - 记录事件历史（最近 N 条，供 Log Tab 展示）
  - 统计各类型事件计数

❌ 不允许直接调用模块业务逻辑
❌ 路由仅通过回调函数，不持有模块引用
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import Callable


class EventRecord:
    """单条事件历史记录。"""

    __slots__ = ("ts", "event_type", "data")

    def __init__(self, event_type: str, data: dict) -> None:
        self.ts:         datetime = datetime.now()
        self.event_type: str      = event_type
        self.data:       dict     = data

    def to_line(self) -> str:
        ts_str = str(self.ts)[:19]
        return f"[{ts_str}] {self.event_type}  {self.data}"


class EventBus:
    """
    Quant OS 全局事件总线（Phase 2）。

    使用方式：
        bus = EventBus(max_history=500)
        bus.subscribe("eQuantOS.module.registered", my_callback)
        bus.publish("eQuantOS.module.registered", {"name": "FactorResearch"})
    """

    def __init__(self, max_history: int = 500) -> None:
        self._lock = threading.Lock()

        # {event_type: [callback, ...]}
        self._subscribers:   dict[str, list[Callable]] = defaultdict(list)

        # 通配符订阅（前缀匹配）：{prefix: [callback, ...]}
        self._wildcard_subs: dict[str, list[Callable]] = defaultdict(list)

        # 事件历史
        self._history:       deque[EventRecord] = deque(maxlen=max_history)

        # 事件计数
        self._counters:      dict[str, int]     = defaultdict(int)

        # 总发布数
        self._total: int = 0

    # ------------------------------------------------------------------ #
    #  订阅 / 取消订阅
    # ------------------------------------------------------------------ #

    def subscribe(
        self,
        event_type: str,
        callback:   Callable,
    ) -> None:
        """
        订阅指定事件类型。

        Parameters
        ----------
        event_type : 精确事件类型字符串，或以 "*" 结尾的通配符前缀
                     例：
                       "eQuantOS.module.registered"  ← 精确匹配
                       "eQuantOS.module.*"            ← 前缀通配
        callback   : 接收 (event_type: str, data: dict) 的回调函数
        """
        with self._lock:
            if event_type.endswith("*"):
                prefix = event_type[:-1]
                if callback not in self._wildcard_subs[prefix]:
                    self._wildcard_subs[prefix].append(callback)
            else:
                if callback not in self._subscribers[event_type]:
                    self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """取消订阅。"""
        with self._lock:
            if event_type.endswith("*"):
                prefix = event_type[:-1]
                lst = self._wildcard_subs.get(prefix, [])
            else:
                lst = self._subscribers.get(event_type, [])
            if callback in lst:
                lst.remove(callback)

    # ------------------------------------------------------------------ #
    #  发布
    # ------------------------------------------------------------------ #

    def publish(self, event_type: str, data: dict | None = None) -> None:
        """
        发布事件到总线，同步调用所有匹配的订阅者。

        Parameters
        ----------
        event_type : 事件类型字符串
        data       : 事件数据 payload（None 将转为空 dict）
        """
        payload = data or {}

        with self._lock:
            # 记录历史
            self._history.append(EventRecord(event_type, payload))
            self._counters[event_type] += 1
            self._total += 1

            # 精确匹配订阅者
            exact_cbs = list(self._subscribers.get(event_type, []))

            # 通配符匹配订阅者
            wildcard_cbs: list[Callable] = []
            for prefix, cbs in self._wildcard_subs.items():
                if event_type.startswith(prefix):
                    wildcard_cbs.extend(cbs)

        # 在锁外回调，避免死锁
        for cb in exact_cbs + wildcard_cbs:
            try:
                cb(event_type, payload)
            except Exception:
                pass   # 单个订阅者异常不影响其他订阅者

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_history(
        self,
        event_type: str | None = None,
        limit:      int        = 100,
    ) -> list[EventRecord]:
        """
        获取事件历史记录。

        Parameters
        ----------
        event_type : None = 全部，否则过滤指定类型
        limit      : 最多返回条数（从最新开始）
        """
        with self._lock:
            records = list(self._history)

        if event_type:
            records = [r for r in records if r.event_type == event_type]

        return records[-limit:]

    def get_stats(self) -> dict:
        """返回事件统计信息。"""
        with self._lock:
            return {
                "total":    self._total,
                "counters": dict(self._counters),
            }

    @property
    def total_published(self) -> int:
        return self._total

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()
            self._counters.clear()
            self._total = 0

    def subscriber_count(self, event_type: str) -> int:
        """返回指定事件类型的订阅者数量。"""
        with self._lock:
            return len(self._subscribers.get(event_type, []))
