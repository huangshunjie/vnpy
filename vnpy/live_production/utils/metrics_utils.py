"""
live_production/utils/metrics_utils.py

滚动窗口指标计算工具（Phase 5）。

职责：
  - RollingWindow: 固定容量的滚动窗口，支持均值/最大/最小/百分位计算
  - RateCounter: 单位时间事件计数（成功率、拒绝率等）
  - LatencyTracker: 延迟样本采集

❌ 无 IO，无网络，无线程，纯计算
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Sequence


class RollingWindow:
    """固定容量滚动窗口，支持常用统计量。"""

    def __init__(self, maxlen: int = 60) -> None:
        self._buf: deque[float] = deque(maxlen=maxlen)
        self._maxlen = maxlen

    def push(self, value: float) -> None:
        self._buf.append(value)

    def mean(self) -> float:
        if not self._buf:
            return 0.0
        return sum(self._buf) / len(self._buf)

    def max(self) -> float:
        return max(self._buf) if self._buf else 0.0

    def min(self) -> float:
        return min(self._buf) if self._buf else 0.0

    def latest(self) -> float:
        return self._buf[-1] if self._buf else 0.0

    def percentile(self, p: float) -> float:
        """Calculate p-th percentile (0-100), nearest-rank."""
        if not self._buf:
            return 0.0
        sorted_vals = sorted(self._buf)
        n   = len(sorted_vals)
        idx = max(0, min(n - 1, int(p / 100.0 * n + 0.4999)))
        return sorted_vals[idx]


    def to_list(self) -> list[float]:
        return list(self._buf)

    def __len__(self) -> int:
        return len(self._buf)

    def clear(self) -> None:
        self._buf.clear()


class RateCounter:
    """
    滑动时间窗口成功率计数器。

    记录 (timestamp, success: bool) 对，
    计算最近 window_seconds 内的成功率。
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._events: deque[tuple[float, bool]] = deque()

    def record(self, success: bool) -> None:
        now = datetime.now().timestamp()
        self._events.append((now, success))
        self._evict(now)

    def rate(self) -> float:
        """返回近 window_seconds 内的成功率（0.0-1.0）。"""
        now = datetime.now().timestamp()
        self._evict(now)
        if not self._events:
            return 1.0
        ok = sum(1 for _, s in self._events if s)
        return ok / len(self._events)

    def total(self) -> int:
        now = datetime.now().timestamp()
        self._evict(now)
        return len(self._events)

    def _evict(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()


class LatencyTracker:
    """
    延迟样本追踪器。

    record_latency(ms) 记录一个延迟样本，
    提供均值 / P95 / P99 / 最新值查询。
    """

    def __init__(self, maxlen: int = 120) -> None:
        self._win = RollingWindow(maxlen=maxlen)

    def record(self, latency_ms: float) -> None:
        self._win.push(max(0.0, latency_ms))

    @property
    def mean_ms(self) -> float:
        return round(self._win.mean(), 2)

    @property
    def p95_ms(self) -> float:
        return round(self._win.percentile(95), 2)

    @property
    def p99_ms(self) -> float:
        return round(self._win.percentile(99), 2)

    @property
    def latest_ms(self) -> float:
        return round(self._win.latest(), 2)

    @property
    def max_ms(self) -> float:
        return round(self._win.max(), 2)

    def to_dict(self) -> dict:
        return {
            "mean_ms":   self.mean_ms,
            "p95_ms":    self.p95_ms,
            "p99_ms":    self.p99_ms,
            "latest_ms": self.latest_ms,
            "max_ms":    self.max_ms,
        }


def compute_health_score(
    latency_ms:         float,
    order_success_rate: float,
    data_delay_s:       float,
    heartbeat_ok:       bool,
) -> float:
    """
    综合健康分数（0.0 - 1.0，越高越健康）。

    权重：
      心跳正常    40%（二元）
      订单成功率  30%
      行情延迟    20%（<1s full, >10s zero）
      网关延迟    10%（<50ms full, >500ms zero）
    """
    hb_score  = 1.0 if heartbeat_ok else 0.0

    order_score = max(0.0, min(1.0, order_success_rate))

    # data_delay: 0s->1.0, 1s->0.9, 10s->0.0
    if data_delay_s <= 1.0:
        data_score = 1.0
    elif data_delay_s >= 10.0:
        data_score = 0.0
    else:
        data_score = 1.0 - (data_delay_s - 1.0) / 9.0

    # latency: 0ms->1.0, 50ms->1.0, 500ms->0.0
    if latency_ms <= 50:
        lat_score = 1.0
    elif latency_ms >= 500:
        lat_score = 0.0
    else:
        lat_score = 1.0 - (latency_ms - 50) / 450.0

    score = (
        hb_score    * 0.40
        + order_score * 0.30
        + data_score  * 0.20
        + lat_score   * 0.10
    )
    return round(score, 4)