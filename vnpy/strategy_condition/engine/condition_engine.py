"""
strategy_condition/engine/condition_engine.py
条件引擎：Condition 叶节点 -> 具体指标计算的调度层
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Tuple

from ..constant import ConditionIndicator
from ..core.condition import Condition
from ..indicators.trend      import (check_ma_slope, check_weekly_ma_slope,
                                      check_ma_alignment, check_new_high_n)
from ..indicators.momentum   import (check_macd_golden, check_macd_death,
                                      check_rsi_range, check_return_n_days)
from ..indicators.volume     import (check_volume_ratio, check_volume_price_up,
                                      check_volume_shrink)
from ..indicators.volatility import check_atr_ratio, check_boll_width


class ConditionEngine:
    """
    叶节点条件评估引擎。
    通过依赖注入接收 candle_buffer / multi_tf / factor_engine。
    """

    def __init__(self, candle_buffer=None, multi_tf=None,
                 factor_engine=None, log_fn=None):
        self._buf    = candle_buffer
        self._multi  = multi_tf
        self._factor = factor_engine
        self._log    = log_fn or print

    def set_candle_buffer(self, buf) -> None: self._buf    = buf
    def set_multi_tf(self, mt)       -> None: self._multi  = mt
    def set_factor_engine(self, fe)  -> None: self._factor = fe

    def eval_condition(self, cond: Condition,
                       symbol: str, bars: list) -> Tuple[bool, float]:
        """评估买入条件树叶节点，返回 (passed, score)。"""
        if not cond.enabled or not bars:
            return (True, 1.0) if not cond.enabled else (False, 0.0)
        p = cond.params
        closes  = [b.close  for b in bars]
        highs   = [b.high   for b in bars]
        lows    = [b.low    for b in bars]
        volumes = [float(b.volume) for b in bars]
        try:
            return self._dispatch(cond.indicator, p, symbol,
                                  closes, highs, lows, volumes, bars)
        except Exception as e:
            self._log(f"[ConditionEngine] {cond.indicator.value}: {e}")
            return False, 0.0

    def _dispatch(self, ind: ConditionIndicator, p: dict, symbol: str,
                  closes, highs, lows, volumes, bars) -> Tuple[bool, float]:
        CI = ConditionIndicator

        # ── 趋势 ──────────────────────────────────────────────────────
        if ind == CI.MA_SLOPE:
            return check_ma_slope(closes, int(p.get("ma_period",20)),
                                  int(p.get("slope_window",10)), float(p.get("min_slope",0.0)))
        if ind == CI.WEEKLY_MA_SLOPE:
            if self._multi is None: return False, 0.0
            wc = self._multi.get_weekly_closes(symbol,
                 int(p.get("ma_period",13)) + int(p.get("slope_window",5)) + 5)
            return check_weekly_ma_slope(wc, int(p.get("ma_period",13)),
                                         int(p.get("slope_window",5)), float(p.get("min_slope",0.0)))
        if ind == CI.MA_ALIGNMENT:
            return check_ma_alignment(closes, p.get("periods", [5,10,20,60]))
        if ind == CI.NEW_HIGH_N:
            return check_new_high_n(closes, highs, int(p.get("n",20)))

        # ── 回调 ──────────────────────────────────────────────────────
        if ind in (CI.PULLBACK_PCT, CI.PULLBACK_FROM_HIGH, CI.PULLBACK_TO_MA):
            from vnpy.market_behavior.engine.signal_engine import detect_pullback
            mode = {"PULLBACK_PCT":"pct_drop","PULLBACK_FROM_HIGH":"from_high",
                    "PULLBACK_TO_MA":"to_ma"}[ind.value]
            return detect_pullback(closes, highs, mode,
                                   int(p.get("window",10)), float(p.get("min_drop",-8.0)),
                                   float(p.get("max_drop",-2.0)), int(p.get("ma_period",20)),
                                   float(p.get("ma_tol_pct",2.0)))

        # ── 动量 ──────────────────────────────────────────────────────
        if ind == CI.MACD_GOLDEN:
            return check_macd_golden(closes, int(p.get("fast",12)),
                                     int(p.get("slow",26)), int(p.get("signal",9)))
        if ind == CI.MACD_DEATH:
            return check_macd_death(closes, int(p.get("fast",12)),
                                    int(p.get("slow",26)), int(p.get("signal",9)))
        if ind == CI.RSI_RANGE:
            return check_rsi_range(closes, int(p.get("period",14)),
                                   float(p.get("min",30.0)), float(p.get("max",70.0)))
        if ind == CI.RETURN_N_DAYS:
            return check_return_n_days(closes, int(p.get("n",10)),
                                       float(p.get("min_return",5.0)))

        # ── 成交量 ────────────────────────────────────────────────────
        if ind == CI.VOLUME_RATIO:
            return check_volume_ratio(volumes, int(p.get("period",20)),
                                      float(p.get("min_ratio",1.5)))
        if ind == CI.VOLUME_PRICE_UP:
            return check_volume_price_up(closes, volumes, int(p.get("period",20)),
                                         float(p.get("min_ratio",1.5)), float(p.get("min_chg",1.0)))
        if ind == CI.VOLUME_SHRINK:
            return check_volume_shrink(volumes, int(p.get("period",20)),
                                       float(p.get("max_ratio",0.7)))

        # ── K线行为 ───────────────────────────────────────────────────
        if ind == CI.CONTINUOUS_RISE:
            recent = closes[-int(p.get("window",10)):]
            rise   = sum(1 for i in range(1,len(recent)) if recent[i] > recent[i-1])
            mn     = int(p.get("min_days",3))
            return rise >= mn, min(rise/(mn*2+1e-9),1.0) if rise>=mn else 0.0
        if ind == CI.LIMIT_UP_COUNT:
            w  = int(p.get("window",20)); mn = int(p.get("min_count",1))
            rc = bars[-w:] if len(bars)>=w else bars
            c  = sum(1 for b in rc if b.open>0 and (b.close-b.open)/b.open>=0.095)
            return c>=mn, min(c/(mn*2+1e-9),1.0) if c>=mn else 0.0
        if ind == CI.BIG_YANG_COUNT:
            w  = int(p.get("window",20)); mn = int(p.get("min_count",2))
            mp = float(p.get("min_pct",3.0))
            rc = bars[-w:] if len(bars)>=w else bars
            c  = sum(1 for b in rc if b.open>0 and (b.close-b.open)/b.open*100>=mp)
            return c>=mn, min(c/(mn*2+1e-9),1.0) if c>=mn else 0.0
        if ind == CI.KLINE_STRENGTH:
            if self._factor is None: return False, 0.0
            try:
                sc = self._factor.get_factor(symbol, "kline_strength")
                if sc is None or math.isnan(sc): return False, 0.0
                ms = float(p.get("min_score",0.4))
                return sc>=ms, min(sc,1.0) if sc>=ms else 0.0
            except Exception: return False, 0.0

        # ── 波动 ──────────────────────────────────────────────────────
        if ind == CI.ATR_RATIO:
            return check_atr_ratio(closes, highs, lows, int(p.get("period",14)),
                                   float(p.get("min",1.0)), float(p.get("max",9999.0)))
        if ind == CI.BOLL_WIDTH:
            return check_boll_width(closes, int(p.get("period",20)),
                                    float(p.get("std_mult",2.0)), float(p.get("min",0.05)),
                                    float(p.get("max",9999.0)))

        # 卖出条件由 eval_exit 处理，此处直接返回
        return False, 0.0

    # ── 卖出条件评估（逐日模拟持仓时调用） ───────────────────────────

    def eval_exit(self, cond: Condition, entry_price: float,
                  current_price: float, peak_price: float,
                  hold_days: int, bars: list,
                  strategy_params=None) -> Tuple[bool, float]:
        """
        Evaluate a sell condition node.
        strategy_params (StrategyParams | None): when provided, threshold
        values for STOP_LOSS / TAKE_PROFIT / TRAILING_STOP / MAX_HOLD_DAYS
        are taken from it; the node's own params act only as fallback.
        """
        if not cond.enabled or entry_price <= 0: return False, 0.0
        p   = cond.params
        sp  = strategy_params        # may be None
        ind = cond.indicator
        ret = (current_price - entry_price) / entry_price * 100
        CI  = ConditionIndicator

        if ind == CI.STOP_LOSS:
            thr = sp.stop_loss_pct if sp is not None else float(p.get("pct", 8.0))
            ok  = ret <= -thr; return ok, 1.0 if ok else 0.0
        if ind == CI.TAKE_PROFIT:
            thr = sp.take_profit_pct if sp is not None else float(p.get("pct", 15.0))
            ok  = ret >= thr; return ok, 1.0 if ok else 0.0
        if ind == CI.TRAILING_STOP:
            tp_thr = sp.take_profit_pct  if sp is not None else float(p.get("take_profit",  15.0))
            tr_thr = sp.trail_drawdown    if sp is not None else float(p.get("trail_drawdown", 10.0))
            if ret < tp_thr: return False, 0.0
            if peak_price <= 0: return False, 0.0
            dd = (peak_price - current_price) / peak_price * 100
            ok = dd >= tr_thr; return ok, 1.0 if ok else 0.0
        if ind == CI.MAX_HOLD_DAYS:
            days = sp.max_hold_days if sp is not None else int(p.get("days", 60))
            ok   = hold_days >= days; return ok, 1.0 if ok else 0.0
        if ind == CI.MA_BREAK_DOWN:
            if not bars: return False, 0.0
            closes = [b.close for b in bars]; mp = int(p.get("ma_period", 20))
            if len(closes) < mp: return False, 0.0
            ma = sum(closes[-mp:]) / mp
            ok = current_price < ma; return ok, 1.0 if ok else 0.0
        if ind == CI.MACD_DEATH_SELL:
            if not bars: return False, 0.0
            return check_macd_death([b.close for b in bars], int(p.get("fast", 12)),
                                    int(p.get("slow", 26)), int(p.get("signal", 9)))
        return False, 0.0
