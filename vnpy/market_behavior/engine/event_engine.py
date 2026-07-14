"""
market_behavior/engine/event_engine.py
Phase 3: 价格事件检测引擎
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..constant import EventType, ContinuousType
from ..model.behavior_event import BehaviorEvent
from ..model.candle import CandleBar
from ..utils.calculator import consecutive_count, max_consecutive_count


def _new_event(symbol, event_type, dt, **kwargs) -> BehaviorEvent:
    return BehaviorEvent(
        event_id=uuid.uuid4().hex[:12],
        symbol=symbol,
        event_type=event_type,
        dt=dt,
        **kwargs,
    )


class EventDetectEngine:
    """价格事件检测引擎 (Phase 3)。"""

    DEFAULT_CFG: Dict[str, Any] = {
        "near_limit_ratio":   0.95,
        "big_rise_pct":       5.0,
        "big_fall_pct":       5.0,
        "big_rise_count":     1,
        "big_fall_count":     1,
        "big_rise_window":    10,
        "big_fall_window":    10,
        "cont_rise_days":     3,
        "cont_fall_days":     3,
        "cont_high_days":     3,
        "cont_low_days":      3,
        "vol_ma_window":      20,
        "vol_up_ratio":       1.5,
        "vol_down_ratio":     0.7,
        "cont_vol_up_days":   3,
        "cont_vol_down_days": 3,
        "gap_up_ratio":       0.02,
        "gap_down_ratio":     0.02,
        "limit_up_window":    10,
        "limit_down_window":  10,
        "limit_up_count":     1,
        "limit_down_count":   1,
    }

    def __init__(self, log_fn=None, main_engine=None, dispatch_fn=None):
        self._log         = log_fn or print
        self._main_engine = main_engine
        self._dispatch    = dispatch_fn
        self._running     = False
        self._cfg         = dict(self.DEFAULT_CFG)
        self._candle_buf  = None
        self._detect_count = 0

    def set_main_engine(self, engine):
        self._main_engine = engine

    def set_dispatch(self, fn):
        self._dispatch = fn

    def set_candle_buffer(self, buf):
        self._candle_buf = buf

    def configure(self, **kwargs):
        self._cfg.update(kwargs)

    def init(self):
        self._log("[EventDetectEngine] init()")

    def start(self):
        self._running = True
        self._log("[EventDetectEngine] start()")

    def stop(self):
        self._running = False
        self._log("[EventDetectEngine] stop()")

    def summary(self) -> dict:
        return {
            "engine":   "EventDetectEngine",
            "status":   "running" if self._running else "stopped",
            "detected": self._detect_count,
        }


    # ── 主检测入口 ────────────────────────────────────────────────────

    def detect(self, symbol: str, n_bars: int = 60) -> List[BehaviorEvent]:
        """对 symbol 最近 n_bars 根K线做全量事件扫描。"""
        if not self._candle_buf:
            return []
        bars = self._candle_buf.get(symbol, n_bars)
        if not bars:
            return []
        latest = bars[-1]
        events: List[BehaviorEvent] = []
        events += self._detect_limit(bars, latest)
        events += self._detect_near_limit(bars, latest)
        events += self._detect_gap(bars, latest)
        events += self._detect_big_move(bars, latest)
        events += self._detect_continuous_rise_fall(bars, latest)
        events += self._detect_continuous_high_low(bars, latest)
        events += self._detect_continuous_volume(bars, latest)
        self._detect_count += len(events)
        for ev in events:
            self._emit_event(ev)
        return events

    def detect_bar(self, bar: CandleBar) -> List[BehaviorEvent]:
        """流式模式：收到新K线后立即检测。"""
        if self._candle_buf:
            self._candle_buf.push(bar)
        return self.detect(bar.symbol)

    # ── 1. 涨跌停 ─────────────────────────────────────────────────────

    def _detect_limit(self, bars, latest) -> List[BehaviorEvent]:
        events = []
        lu_win = self._cfg["limit_up_window"]
        ld_win = self._cfg["limit_down_window"]
        lu_thr = self._cfg["limit_up_count"]
        ld_thr = self._cfg["limit_down_count"]
        lu_count = sum(1 for b in bars[-lu_win:] if b.is_limit_up)
        ld_count = sum(1 for b in bars[-ld_win:] if b.is_limit_down)
        if latest.is_limit_up and lu_count >= lu_thr:
            events.append(_new_event(
                latest.symbol, EventType.LIMIT_UP, latest.dt,
                window=lu_win, count=lu_count,
                threshold=latest.limit_pct, value=latest.change_pct,
            ))
        if latest.is_limit_down and ld_count >= ld_thr:
            events.append(_new_event(
                latest.symbol, EventType.LIMIT_DOWN, latest.dt,
                window=ld_win, count=ld_count,
                threshold=latest.limit_pct, value=latest.change_pct,
            ))
        return events

    # ── 2. 接近涨跌停 ─────────────────────────────────────────────────

    def _detect_near_limit(self, bars, latest) -> List[BehaviorEvent]:
        events = []
        ratio = self._cfg["near_limit_ratio"]
        lp    = latest.limit_pct
        if latest.change_pct >= lp * ratio and not latest.is_limit_up and latest.change_pct > 0:
            events.append(_new_event(
                latest.symbol, EventType.NEAR_LIMIT_UP, latest.dt,
                threshold=lp * ratio, value=latest.change_pct,
            ))
        if latest.change_pct <= -lp * ratio and not latest.is_limit_down and latest.change_pct < 0:
            events.append(_new_event(
                latest.symbol, EventType.NEAR_LIMIT_DOWN, latest.dt,
                threshold=-lp * ratio, value=latest.change_pct,
            ))
        return events

    # ── 3. 跳空 ───────────────────────────────────────────────────────

    def _detect_gap(self, bars, latest) -> List[BehaviorEvent]:
        events = []
        if len(bars) < 2:
            return events
        prev = bars[-2]
        gu_r = self._cfg["gap_up_ratio"]
        gd_r = self._cfg["gap_down_ratio"]
        # 跳空高开：今开 > 昨收 * (1 + ratio)
        if latest.open > prev.close * (1 + gu_r):
            gap_pct = (latest.open - prev.close) / prev.close * 100
            events.append(_new_event(
                latest.symbol, EventType.GAP_UP, latest.dt,
                threshold=gu_r * 100, value=round(gap_pct, 4),
            ))
        # 跳空低开：今开 < 昨收 * (1 - ratio)
        if prev.close > 0 and latest.open < prev.close * (1 - gd_r):
            gap_pct = (prev.close - latest.open) / prev.close * 100
            events.append(_new_event(
                latest.symbol, EventType.GAP_DOWN, latest.dt,
                threshold=gd_r * 100, value=round(gap_pct, 4),
            ))
        return events

    # ── 4. 大涨 / 大跌 ───────────────────────────────────────────────

    def _detect_big_move(self, bars, latest) -> List[BehaviorEvent]:
        events = []
        rise_thr = self._cfg["big_rise_pct"]
        fall_thr = self._cfg["big_fall_pct"]
        rise_cnt = self._cfg["big_rise_count"]
        fall_cnt = self._cfg["big_fall_count"]
        rise_win = self._cfg["big_rise_window"]
        fall_win = self._cfg["big_fall_window"]

        n_rise = sum(1 for b in bars[-rise_win:] if b.change_pct >= rise_thr)
        if n_rise >= rise_cnt:
            events.append(_new_event(
                latest.symbol, EventType.RISE_PCT, latest.dt,
                window=rise_win, count=n_rise,
                threshold=rise_thr, value=latest.change_pct,
            ))

        n_fall = sum(1 for b in bars[-fall_win:] if b.change_pct <= -fall_thr)
        if n_fall >= fall_cnt:
            events.append(_new_event(
                latest.symbol, EventType.FALL_PCT, latest.dt,
                window=fall_win, count=n_fall,
                threshold=-fall_thr, value=latest.change_pct,
            ))
        return events

    # ── 5. 连续上涨 / 连续下跌 ───────────────────────────────────────

    def _detect_continuous_rise_fall(self, bars, latest) -> List[BehaviorEvent]:
        events = []
        min_rise = self._cfg["cont_rise_days"]
        min_fall = self._cfg["cont_fall_days"]

        rise_flags = [bars[i].close > bars[i-1].close for i in range(1, len(bars))]
        cont_rise  = consecutive_count(rise_flags)
        if cont_rise >= min_rise:
            events.append(_new_event(
                latest.symbol, EventType.RISE_PCT, latest.dt,
                continuous_type=ContinuousType.RISE,
                days=cont_rise, window=cont_rise, count=cont_rise,
                threshold=float(min_rise), value=float(cont_rise),
            ))

        fall_flags = [bars[i].close < bars[i-1].close for i in range(1, len(bars))]
        cont_fall  = consecutive_count(fall_flags)
        if cont_fall >= min_fall:
            events.append(_new_event(
                latest.symbol, EventType.FALL_PCT, latest.dt,
                continuous_type=ContinuousType.FALL,
                days=cont_fall, window=cont_fall, count=cont_fall,
                threshold=float(min_fall), value=float(cont_fall),
            ))
        return events

    # ── 6. 连续创新高 / 连续创新低 ───────────────────────────────────

    def _detect_continuous_high_low(self, bars, latest) -> List[BehaviorEvent]:
        events = []
        min_high = self._cfg["cont_high_days"]
        min_low  = self._cfg["cont_low_days"]

        high_flags = []
        for i in range(1, len(bars)):
            prev_max = max(b.close for b in bars[:i])
            high_flags.append(bars[i].close > prev_max)
        cont_high = consecutive_count(high_flags)
        if cont_high >= min_high:
            events.append(_new_event(
                latest.symbol, EventType.RISE_PCT, latest.dt,
                continuous_type=ContinuousType.NEW_HIGH,
                days=cont_high, window=cont_high, count=cont_high,
                threshold=float(min_high), value=float(cont_high),
            ))

        low_flags = []
        for i in range(1, len(bars)):
            prev_min = min(b.close for b in bars[:i])
            low_flags.append(bars[i].close < prev_min)
        cont_low = consecutive_count(low_flags)
        if cont_low >= min_low:
            events.append(_new_event(
                latest.symbol, EventType.FALL_PCT, latest.dt,
                continuous_type=ContinuousType.NEW_LOW,
                days=cont_low, window=cont_low, count=cont_low,
                threshold=float(min_low), value=float(cont_low),
            ))
        return events

    # ── 7. 连续放量 / 连续缩量 ───────────────────────────────────────

    def _detect_continuous_volume(self, bars, latest) -> List[BehaviorEvent]:
        events = []
        ma_win   = self._cfg["vol_ma_window"]
        up_r     = self._cfg["vol_up_ratio"]
        down_r   = self._cfg["vol_down_ratio"]
        min_up   = self._cfg["cont_vol_up_days"]
        min_down = self._cfg["cont_vol_down_days"]

        if len(bars) < ma_win + 1:
            return events

        vols = [b.volume for b in bars]
        up_flags:   List[bool] = []
        down_flags: List[bool] = []

        for i in range(ma_win, len(bars)):
            vol_ma = sum(vols[i - ma_win: i]) / ma_win
            if vol_ma <= 0:
                up_flags.append(False)
                down_flags.append(False)
                continue
            ratio = vols[i] / vol_ma
            up_flags.append(ratio >= up_r)
            down_flags.append(ratio <= down_r)

        cont_up   = max_consecutive_count(up_flags)
        cont_down = max_consecutive_count(down_flags)

        if cont_up >= min_up:
            vol_ma_v = sum(vols[-(ma_win+1):-1]) / ma_win
            events.append(_new_event(
                latest.symbol, EventType.HIGH_VOLUME, latest.dt,
                continuous_type=ContinuousType.VOLUME_UP,
                days=cont_up, window=ma_win, count=cont_up,
                threshold=up_r,
                value=round(latest.volume / vol_ma_v if vol_ma_v else 0, 4),
            ))

        if cont_down >= min_down:
            vol_ma_v = sum(vols[-(ma_win+1):-1]) / ma_win
            events.append(_new_event(
                latest.symbol, EventType.LOW_VOLUME, latest.dt,
                continuous_type=ContinuousType.VOLUME_DOWN,
                days=cont_down, window=ma_win, count=cont_down,
                threshold=down_r,
                value=round(latest.volume / vol_ma_v if vol_ma_v else 0, 4),
            ))
        return events

    # ── 组合条件查询接口 ──────────────────────────────────────────────

    def query(self, symbol: str, conditions: List[Dict[str, Any]]) -> bool:
        """
        多条件 AND 查询。
        conditions: [
          {"event_type": "limit_up",  "window": 10, "count": 3},
          {"event_type": "rise_pct",  "window": 10, "count": 5, "threshold": 5.0},
          {"continuous": "rise",      "days": 5},
          {"continuous": "vol_up",    "days": 3},
        ]
        """
        if not self._candle_buf:
            return False
        for cond in conditions:
            if not self._check_single_condition(symbol, cond):
                return False
        return True

    def _check_single_condition(self, symbol: str, cond: Dict[str, Any]) -> bool:
        bars = self._candle_buf.get(symbol, 250)
        if not bars:
            return False

        cont = cond.get("continuous", "")
        if cont:
            return self._check_continuous(bars, cont, int(cond.get("days", 1)))

        ev_type = cond.get("event_type", "")
        window  = int(cond.get("window", 10))
        count   = int(cond.get("count",  1))
        thresh  = float(cond.get("threshold", 0.0))
        wb      = bars[-window:]

        if ev_type == "limit_up":
            return sum(1 for b in wb if b.is_limit_up) >= count
        if ev_type == "limit_down":
            return sum(1 for b in wb if b.is_limit_down) >= count
        if ev_type == "rise_pct":
            thr = thresh or self._cfg["big_rise_pct"]
            return sum(1 for b in wb if b.change_pct >= thr) >= count
        if ev_type == "fall_pct":
            thr = thresh or self._cfg["big_fall_pct"]
            return sum(1 for b in wb if b.change_pct <= -thr) >= count
        if ev_type == "high_volume":
            ma_win = self._cfg["vol_ma_window"]
            up_r   = thresh or self._cfg["vol_up_ratio"]
            vols   = [b.volume for b in bars]
            hits   = 0
            for i in range(len(bars) - window, len(bars)):
                if i < ma_win:
                    continue
                vol_ma = sum(vols[i - ma_win: i]) / ma_win
                if vol_ma > 0 and vols[i] / vol_ma >= up_r:
                    hits += 1
            return hits >= count
        return False

    def _check_continuous(self, bars, cont_type: str, req_days: int) -> bool:
        if cont_type == "rise":
            flags = [bars[i].close > bars[i-1].close for i in range(1, len(bars))]
            return consecutive_count(flags) >= req_days
        if cont_type == "fall":
            flags = [bars[i].close < bars[i-1].close for i in range(1, len(bars))]
            return consecutive_count(flags) >= req_days
        if cont_type == "new_high":
            flags = []
            for i in range(1, len(bars)):
                flags.append(bars[i].close > max(b.close for b in bars[:i]))
            return consecutive_count(flags) >= req_days
        if cont_type == "new_low":
            flags = []
            for i in range(1, len(bars)):
                flags.append(bars[i].close < min(b.close for b in bars[:i]))
            return consecutive_count(flags) >= req_days
        if cont_type in ("vol_up", "vol_down"):
            ma_win = self._cfg["vol_ma_window"]
            if len(bars) < ma_win + 1:
                return False
            vols  = [b.volume for b in bars]
            up_r  = self._cfg["vol_up_ratio"]
            dn_r  = self._cfg["vol_down_ratio"]
            flags = []
            for i in range(ma_win, len(bars)):
                vol_ma = sum(vols[i - ma_win: i]) / ma_win
                if vol_ma <= 0:
                    flags.append(False)
                    continue
                ratio = vols[i] / vol_ma
                flags.append(ratio >= up_r if cont_type == "vol_up" else ratio <= dn_r)
            return consecutive_count(flags) >= req_days
        return False

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(event_type, data)
            except Exception:
                pass

    def _emit_event(self, ev: BehaviorEvent) -> None:
        from ..event import EVENT_MB_EVENT_DETECTED
        self._emit(EVENT_MB_EVENT_DETECTED, ev.to_dict())
