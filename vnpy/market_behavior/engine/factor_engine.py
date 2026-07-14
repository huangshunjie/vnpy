"""
market_behavior/engine/factor_engine.py
Phase 6: 行为因子引擎
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..constant import FactorType
from ..model.candle import CandleBar
from ..model.behavior_factor import BehaviorFactor


def _new_factor(symbol, factor_type, dt, window, value,
                norm_value=0.0, components=None, formula=""):
    return BehaviorFactor(
        factor_id=uuid.uuid4().hex[:12],
        symbol=symbol, factor_type=factor_type, dt=dt,
        window=window, value=round(value, 6),
        norm_value=round(norm_value, 6),
        components=components or {}, formula=formula,
    )


class FactorEngine:
    """行为因子引擎 (Phase 6)。"""

    DEFAULT_CFG: Dict[str, Any] = {
        "window":               20,
        "big_yang_change":      3.0,
        "big_yin_change":       3.0,
        "big_yang_body_ratio":  0.55,
        "big_yin_body_ratio":   0.55,
        "long_upper_ratio":     0.55,
        "long_upper_body_max":  0.35,
        "vol_breakout_ratio":   2.0,
        "strength_w_rise":      0.30,
        "strength_w_limit":     0.30,
        "strength_w_breakout":  0.25,
        "strength_w_yang":      0.15,
        "norm_limit_up_max":    5,
        "norm_breakout_max":    5,
        "norm_yang_max":        8,
        "norm_vol_ratio_max":   3.0,
    }

    def __init__(self, log_fn=None, main_engine=None, dispatch_fn=None):
        self._log          = log_fn or print
        self._main_engine  = main_engine
        self._dispatch     = dispatch_fn
        self._running      = False
        self._cfg          = dict(self.DEFAULT_CFG)
        self._candle_buf   = None
        self._compute_count = 0

    def set_main_engine(self, e):   self._main_engine = e
    def set_dispatch(self, fn):     self._dispatch = fn
    def set_candle_buffer(self, b): self._candle_buf = b
    def configure(self, **kw):      self._cfg.update(kw)

    def init(self):  self._log("[FactorEngine] init()")
    def start(self): self._running = True;  self._log("[FactorEngine] start()")
    def stop(self):  self._running = False; self._log("[FactorEngine] stop()")

    def summary(self) -> dict:
        return {"engine": "FactorEngine",
                "status": "running" if self._running else "stopped",
                "computed": self._compute_count}

    # ── 主计算入口 ────────────────────────────────────────────────────

    def compute(self, symbol: str, window: int = 0) -> List[BehaviorFactor]:
        """计算全量行为因子，返回列表并发布事件。"""
        if not self._candle_buf:
            return []
        n    = window or self._cfg["window"]
        bars = self._candle_buf.get(symbol, n + 5)
        if len(bars) < 2:
            return []
        latest = bars[-1]
        wb     = bars[-n:] if len(bars) >= n else bars

        factors = [
            self._calc_rise_days(symbol, latest, wb, n),
            self._calc_fall_days(symbol, latest, wb, n),
            self._calc_limit_up_count(symbol, latest, wb, n),
            self._calc_limit_down_count(symbol, latest, wb, n),
            self._calc_big_yang_count(symbol, latest, wb, n),
            self._calc_long_upper_count(symbol, latest, wb, n),
            self._calc_breakout_count(symbol, latest, bars, n),
            self._calc_volatility(symbol, latest, bars, n),
            self._calc_kline_strength(symbol, latest, wb, bars, n),
        ]
        self._compute_count += len(factors)
        for f in factors:
            self._emit_factor(f)
        return factors

    def compute_bar(self, bar: CandleBar) -> List[BehaviorFactor]:
        """流式模式：每收到新K线后调用。"""
        if self._candle_buf:
            self._candle_buf.push(bar)
        return self.compute(bar.symbol)

    # ── 1. 上涨天数 ───────────────────────────────────────────────────

    def _calc_rise_days(self, sym, latest, wb, n) -> BehaviorFactor:
        rise  = sum(1 for b in wb if b.change_pct > 0)
        value = rise / len(wb) if wb else 0.0
        return _new_factor(sym, FactorType.RISE_DAYS, latest.dt, n, value,
                           norm_value=value,
                           formula=f"rise_count({n}) / {n}")

    # ── 2. 下跌天数 ───────────────────────────────────────────────────

    def _calc_fall_days(self, sym, latest, wb, n) -> BehaviorFactor:
        fall  = sum(1 for b in wb if b.change_pct < 0)
        value = fall / len(wb) if wb else 0.0
        return _new_factor(sym, FactorType.FALL_DAYS, latest.dt, n, value,
                           norm_value=value,
                           formula=f"fall_count({n}) / {n}")

    # ── 3. 涨停次数 ───────────────────────────────────────────────────

    def _calc_limit_up_count(self, sym, latest, wb, n) -> BehaviorFactor:
        count    = sum(1 for b in wb if b.is_limit_up)
        norm_max = self._cfg["norm_limit_up_max"]
        return _new_factor(sym, FactorType.LIMIT_UP_COUNT, latest.dt, n,
                           float(count),
                           norm_value=min(count / norm_max, 1.0),
                           formula=f"limit_up_count({n})")

    # ── 4. 跌停次数 ───────────────────────────────────────────────────

    def _calc_limit_down_count(self, sym, latest, wb, n) -> BehaviorFactor:
        count    = sum(1 for b in wb if b.is_limit_down)
        norm_max = self._cfg["norm_limit_up_max"]
        return _new_factor(sym, FactorType.LIMIT_DOWN_COUNT, latest.dt, n,
                           float(count),
                           norm_value=min(count / norm_max, 1.0),
                           formula=f"limit_down_count({n})")

    # ── 5. 大阳线次数 ─────────────────────────────────────────────────

    def _calc_big_yang_count(self, sym, latest, wb, n) -> BehaviorFactor:
        cfg   = self._cfg
        count = sum(1 for b in wb
                    if b.is_yang
                    and b.change_pct >= cfg["big_yang_change"]
                    and b.body_ratio >= cfg["big_yang_body_ratio"])
        norm_max = cfg["norm_yang_max"]
        return _new_factor(sym, FactorType.BIG_YANG_COUNT, latest.dt, n,
                           float(count),
                           norm_value=min(count / norm_max, 1.0),
                           formula=f"big_yang_count({n})")

    # ── 6. 长上影次数 ─────────────────────────────────────────────────

    def _calc_long_upper_count(self, sym, latest, wb, n) -> BehaviorFactor:
        cfg   = self._cfg
        count = sum(1 for b in wb
                    if b.upper_shadow_ratio >= cfg["long_upper_ratio"]
                    and b.body_ratio <= cfg["long_upper_body_max"])
        norm  = min(count / max(n / 4, 1), 1.0)
        return _new_factor(sym, FactorType.LONG_UPPER_COUNT, latest.dt, n,
                           float(count), norm_value=norm,
                           formula=f"long_upper_count({n})")

    # ── 7. 突破次数因子 ───────────────────────────────────────────────

    def _calc_breakout_count(self, sym, latest, bars, n) -> BehaviorFactor:
        """量能突破 × 0.6 + 价格新高 × 0.4（窗口内累计）。"""
        cfg        = self._cfg
        vol_r      = cfg["vol_breakout_ratio"]
        wb         = bars[-n:] if len(bars) >= n else bars
        vol_breaks = 0
        px_breaks  = 0

        for i in range(1, len(wb)):
            b          = wb[i]
            prev_vols  = [wb[j].volume for j in range(max(0, i - 5), i)]
            prev_cls   = [wb[j].close  for j in range(max(0, i - 5), i)]
            if prev_vols:
                vol_ma = sum(prev_vols) / len(prev_vols)
                if vol_ma > 0 and b.volume / vol_ma >= vol_r and b.is_yang:
                    vol_breaks += 1
            if prev_cls and b.close > max(prev_cls):
                px_breaks += 1

        total    = vol_breaks * 0.6 + px_breaks * 0.4
        norm_max = cfg["norm_breakout_max"]
        return _new_factor(sym, FactorType.BREAKOUT_COUNT, latest.dt, n,
                           round(total, 4),
                           norm_value=round(min(total / norm_max, 1.0), 6),
                           components={"vol_breaks": vol_breaks,
                                       "px_breaks":  px_breaks},
                           formula=f"0.6×vol_breaks + 0.4×px_breaks (n={n})")

    # ── 8. 波动强度（ATR%）────────────────────────────────────────────

    def _calc_volatility(self, sym, latest, bars, n) -> BehaviorFactor:
        """N日 ATR / avg_close × 100（相对振幅%，归一化上限3%）。"""
        if len(bars) < n + 1:
            return _new_factor(sym, FactorType.VOLATILITY, latest.dt, n,
                               0.0, formula="atr_pct(insufficient)")
        tr_list = []
        for i in range(len(bars) - n, len(bars)):
            b    = bars[i]
            prev = bars[i - 1]
            tr   = max(b.high - b.low,
                       abs(b.high - prev.close),
                       abs(b.low  - prev.close))
            tr_list.append(tr)

        atr       = sum(tr_list) / n
        closes    = [b.close for b in bars[-n:]]
        avg_close = sum(closes) / len(closes) if closes else 1.0
        atr_pct   = atr / avg_close * 100 if avg_close > 0 else 0.0
        norm_max  = self._cfg["norm_vol_ratio_max"]
        return _new_factor(sym, FactorType.VOLATILITY, latest.dt, n,
                           round(atr_pct, 6),
                           norm_value=round(min(atr_pct / norm_max, 1.0), 6),
                           formula=f"ATR({n}) / avg_close × 100")

    # ── 9. 综合 K线强度 ───────────────────────────────────────────────

    def _calc_kline_strength(self, sym, latest, wb, bars, n) -> BehaviorFactor:
        """
        strength = w_rise×rise_norm + w_limit×limit_norm
                 + w_breakout×breakout_norm + w_yang×yang_norm
        """
        cfg  = self._cfg
        rise_norm  = (sum(1 for b in wb if b.change_pct > 0) / len(wb)
                      if wb else 0.0)
        limit_norm = min(sum(1 for b in wb if b.is_limit_up)
                         / cfg["norm_limit_up_max"], 1.0)
        yang_norm  = min(sum(1 for b in wb
                             if b.is_yang
                             and b.change_pct >= cfg["big_yang_change"]
                             and b.body_ratio >= cfg["big_yang_body_ratio"])
                         / cfg["norm_yang_max"], 1.0)
        bk_f       = self._calc_breakout_count(sym, latest, bars, n)
        bk_norm    = bk_f.norm_value

        wr = cfg["strength_w_rise"]
        wl = cfg["strength_w_limit"]
        wb_ = cfg["strength_w_breakout"]
        wy = cfg["strength_w_yang"]
        strength = wr * rise_norm + wl * limit_norm + wb_ * bk_norm + wy * yang_norm

        return _new_factor(sym, FactorType.KLINE_STRENGTH, latest.dt, n,
                           round(strength, 6),
                           norm_value=round(strength, 6),
                           components={"rise_norm":     round(rise_norm, 4),
                                       "limit_norm":    round(limit_norm, 4),
                                       "breakout_norm": round(bk_norm, 4),
                                       "yang_norm":     round(yang_norm, 4)},
                           formula=f"{wr}×rise+{wl}×limit+{wb_}×breakout+{wy}×yang")

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, et: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(et, data)
            except Exception:
                pass

    def _emit_factor(self, f: BehaviorFactor) -> None:
        from ..event import EVENT_MB_FACTOR_UPDATED
        self._emit(EVENT_MB_FACTOR_UPDATED, f.to_dict())
