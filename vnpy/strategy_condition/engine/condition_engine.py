"""
strategy_condition/engine/condition_engine.py
条件引擎：Condition 叶节点 -> 具体指标计算的调度层

Phase 2-4 多周期改造：
- 支持从 MultiTimeframeContext 获取指定周期的数据
- 保持向后兼容：仍支持传统的 (symbol, bars) 接口
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple

from vnpy.trader.constant import Interval

from ..constant import ConditionIndicator
from ..core.condition import Condition
from ..core.mtf_context import MultiTimeframeContext
from ..indicators.trend      import (check_ma_slope, check_weekly_ma_slope,
                                      check_ma_alignment, check_new_high_n)
from ..indicators.momentum   import (check_macd_golden, check_macd_death,
                                      check_rsi_range, check_return_n_days)
from ..indicators.volume     import (check_volume_ratio, check_volume_price_up,
                                      check_volume_shrink)
from ..indicators.volatility import check_atr_ratio, check_boll_width
from ..indicators.kline_patterns import (
    check_kline_yin, check_kline_yang, check_kline_shrink_yin,
    check_kline_doji, check_kline_big_yang, check_kline_limit_up,
    check_kline_long_lower
)



class ConditionEngine:
    """
    叶节点条件评估引擎。
    通过依赖注入接收 candle_buffer / multi_tf / factor_engine。
    
    Phase 2-4 改造：支持多周期数据评估。
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
                       symbol: str, bars: list,
                       _precomputed: dict = None,
                       _mtf_context: Optional[MultiTimeframeContext] = None) -> Tuple[bool, float]:
        """
        评估买入条件树叶节点，返回 (passed, score)。

        Phase 2-4 多周期支持：
        - 如果提供了 _mtf_context 且 cond.data_interval 不为 None，
          则从 _mtf_context 中获取指定周期的数据进行评估
        - 否则使用传统的 bars 参数（向后兼容）

        Args:
            cond: 条件对象
            symbol: 股票代码
            bars: 传统单周期K线数据（向后兼容）
            _precomputed: 预计算数组字典（性能优化）
            _mtf_context: 多周期上下文（Phase 2-4 新增）

        _precomputed: 可选预计算数组字典，格式：
            {"closes": np_array, "highs": np_array,
             "lows": np_array, "volumes": np_array}
            传入时跳过 list comprehension，直接使用（性能优化）。
        """
        if not cond.enabled:
            return True, 1.0

        # Phase 2-4: 多周期数据选择
        if _mtf_context and cond.data_interval:
            # 使用指定周期的数据
            bars = _mtf_context.get_bars(cond.data_interval)
            if not bars:
                # 数据不足，条件不通过
                return False, 0.0
            # 清空预计算缓存（因为bars已经切换）
            _precomputed = None

        if not bars:
            return False, 0.0

        p = cond.params
        if _precomputed:
            closes = _precomputed["closes"]
            opens = _precomputed.get("opens")  # 新增：提取 opens
            highs = _precomputed["highs"]
            lows = _precomputed["lows"]
            volumes = _precomputed["volumes"]
        else:
            closes  = [b.close  for b in bars]
            opens   = [b.open   for b in bars]  # 保持一致
            highs   = [b.high   for b in bars]
            lows    = [b.low    for b in bars]
            volumes = [float(b.volume) for b in bars]
        try:
            return self._dispatch(cond.indicator, p, symbol,
                                  closes, highs, lows, volumes, bars)
        except Exception as e:
            self._log(f"[ConditionEngine] {cond.indicator.value}: {e}")
            return False, 0.0

    def eval_condition_mtf(self, cond: Condition,
                           symbol: str, bars: list,
                           mtf_context: MultiTimeframeContext,
                           _precomputed: dict = None) -> Tuple[bool, float]:
        """
        多周期条件评估方法（Phase 6-8 统一接口）
        
        这是一个包装方法，将 mtf_context 传递给 eval_condition。
        与 Phase 6 MonitorEngine 和 Phase 7 ScanEngine 的调用方式保持一致。
        
        Args:
            cond: 条件对象
            symbol: 股票代码
            bars: 执行周期的K线数据
            mtf_context: 多周期上下文（包含所有需要的周期数据）
            _precomputed: 预计算数组字典（可选）
        
        Returns:
            (passed, score): 条件是否通过及得分
        """
        return self.eval_condition(
            cond, symbol, bars,
            _precomputed=_precomputed,
            _mtf_context=mtf_context
        )

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
            return check_ma_alignment(closes, p.get("periods", [5,10,20,60]),
                                      float(p.get("max_gap_pct", 0.0)))
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


        # ── K线形态（单根） ───────────────────────────────────────────
        if ind == CI.KLINE_YANG:
            opens = [b.open for b in bars]
            return check_kline_yang(closes, opens)
        if ind == CI.KLINE_YIN:
            opens = [b.open for b in bars]
            return check_kline_yin(closes, opens)
        if ind == CI.KLINE_SHRINK_YIN:
            opens = [b.open for b in bars]
            return check_kline_shrink_yin(closes, opens, volumes,
                                          int(p.get("vol_period", 5)),
                                          float(p.get("max_vol_ratio", 0.8)))
        if ind == CI.KLINE_DOJI:
            opens = [b.open for b in bars]
            return check_kline_doji(closes, opens, highs, lows,
                                    float(p.get("max_body_ratio", 0.1)))
        if ind == CI.KLINE_BIG_YANG:
            opens = [b.open for b in bars]
            return check_kline_big_yang(closes, opens, float(p.get("min_pct", 5.0)))
        if ind == CI.KLINE_LIMIT_UP:
            return check_kline_limit_up(closes, closes)
        if ind == CI.KLINE_LONG_LOWER:
            opens = [b.open for b in bars]
            return check_kline_long_lower(closes, opens, highs, lows,
                                          float(p.get("min_ratio", 2.0)))

        # ── 波动 ──────────────────────────────────────────────────────
        if ind == CI.ATR_RATIO:
            return check_atr_ratio(closes, highs, lows, int(p.get("period",14)),
                                   float(p.get("min",1.0)), float(p.get("max",9999.0)))
        if ind == CI.BOLL_WIDTH:
            return check_boll_width(closes, int(p.get("period",20)),
                                    float(p.get("std_mult",2.0)), float(p.get("min",0.05)),
                                    float(p.get("max",9999.0)))

        # ── 时间过滤 ──────────────────────────────────────────────────
        if ind == CI.TIME_OF_DAY:
            return self._check_time_of_day(p, bars)

        # ── 卖出条件（纯技术面，不需要持仓上下文） ────────────────────
        if ind == CI.MA_BREAK_DOWN:
            mp = int(p.get("ma_period", 20))
            if len(closes) < mp: return False, 0.0
            ma = sum(closes[-mp:]) / mp
            ok = closes[-1] < ma; return ok, 1.0 if ok else 0.0
        if ind == CI.MACD_DEATH_SELL:
            return check_macd_death(closes, int(p.get("fast", 12)),
                                    int(p.get("slow", 26)), int(p.get("signal", 9)))

        # ── 追踪止盈（纯技术面近似：从近期低点涨幅达标后从高点回撤达标） ──
        if ind == CI.TRAILING_STOP:
            tp_thr = float(p.get("take_profit", 15.0))
            tr_thr = float(p.get("trail_drawdown", 10.0))
            # 用最近 N 根K线的低点作为"入场价"近似
            lookback = min(60, len(closes))
            recent_closes = closes[-lookback:]
            recent_low = min(recent_closes)
            recent_high = max(recent_closes)
            if recent_low <= 0:
                return False, 0.0
            # 从低点的涨幅
            rise_pct = (recent_high - recent_low) / recent_low * 100
            if rise_pct < tp_thr:
                return False, 0.0
            # 从高点的回撤
            if recent_high <= 0:
                return False, 0.0
            dd_pct = (recent_high - closes[-1]) / recent_high * 100
            ok = dd_pct >= tr_thr
            return ok, 1.0 if ok else 0.0

        # ── 止损（纯技术面近似：从近期高点回撤超过阈值） ────────────────
        if ind == CI.STOP_LOSS:
            thr = float(p.get("pct", 8.0))
            lookback = min(60, len(closes))
            recent_high = max(closes[-lookback:])
            if recent_high <= 0:
                return False, 0.0
            dd = (recent_high - closes[-1]) / recent_high * 100
            ok = dd >= thr
            return ok, 1.0 if ok else 0.0

        # ── 最大持仓天数（纯技术面无法判断，恒返回 False） ──────────────
        if ind == CI.MAX_HOLD_DAYS:
            return False, 0.0

        # 其他未识别的条件
        return False, 0.0

    @staticmethod
    def _check_time_of_day(p: dict, bars: list) -> Tuple[bool, float]:
        """
        判断当前（序列最后一根）K线的日内时间是否落在 [min_time, max_time]。
        - 日线K线（时间为 00:00）视为无日内信息，恒不通过；
        - 分钟K线按 HH:MM 比较。
        """
        if not bars:
            return False, 0.0
        # BarData 的属性名是 datetime（不是 dt）
        dt = getattr(bars[-1], "datetime", None) or getattr(bars[-1], "dt", None)
        if dt is None:
            return False, 0.0
        # 日线：小时和分钟都为0，无日内时间概念
        if dt.hour == 0 and dt.minute == 0:
            return False, 0.0
        cur = dt.hour * 60 + dt.minute

        def _parse(t: str, default: int) -> int:
            try:
                hh, mm = str(t).split(":")
                return int(hh) * 60 + int(mm)
            except Exception:
                return default

        lo = _parse(p.get("min_time", "14:30"), 14 * 60 + 30)
        hi = _parse(p.get("max_time", "15:00"), 15 * 60)
        ok = lo <= cur <= hi
        return ok, 1.0 if ok else 0.0

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

        # ── 阈值取值策略：节点参数优先，StrategyParams 兜底 ──
        # 语义变更（2026-08）：过去为 sp 覆盖节点，导致用户在条件编辑器
        # 中调整止损/止盈/追踪/持仓阈值完全不生效，且 label 显示与实际
        # 计算值三方不同步。现在改为节点自身 params 优先——只有当节点
        # 未提供该键时才回退到全局 StrategyParams。
        if ind == CI.STOP_LOSS:
            default_thr = sp.stop_loss_pct if sp is not None else 8.0
            thr = float(p.get("pct", default_thr))
            ok  = ret <= -thr; return ok, 1.0 if ok else 0.0
        if ind == CI.TAKE_PROFIT:
            default_thr = sp.take_profit_pct if sp is not None else 15.0
            thr = float(p.get("pct", default_thr))
            ok  = ret >= thr; return ok, 1.0 if ok else 0.0
        if ind == CI.TRAILING_STOP:
            default_tp = sp.take_profit_pct if sp is not None else 15.0
            default_tr = sp.trail_drawdown  if sp is not None else 10.0
            tp_thr = float(p.get("take_profit",  default_tp))
            tr_thr = float(p.get("trail_drawdown", default_tr))
            # 正确语义：用 peak_ret（峰值收益率）判断是否曾达到止盈阈值
            # 而非 ret（当前收益率），否则价格回撤后 ret < tp_thr 永远不触发
            if peak_price <= 0: return False, 0.0
            peak_ret = (peak_price - entry_price) / entry_price * 100
            if peak_ret < tp_thr: return False, 0.0
            dd = (peak_price - current_price) / peak_price * 100
            ok = dd >= tr_thr; return ok, 1.0 if ok else 0.0
        if ind == CI.MAX_HOLD_DAYS:
            default_days = sp.max_hold_days if sp is not None else 60
            days = int(p.get("days", default_days))
            ok   = hold_days >= days; return ok, 1.0 if ok else 0.0
        if ind == CI.MA_BREAK_DOWN:
            if not bars: return False, 0.0
            closes = [b.close for b in bars]; mp = int(p.get("ma_period", 20))
            if len(closes) < mp: return False, 0.0
            ma = sum(closes[-mp:]) / mp
            ok = closes[-1] < ma; return ok, 1.0 if ok else 0.0
        if ind == CI.MACD_DEATH_SELL:
            if not bars: return False, 0.0
            return check_macd_death([b.close for b in bars], int(p.get("fast", 12)),
                                    int(p.get("slow", 26)), int(p.get("signal", 9)))
        # ── 时间过滤（不依赖持仓上下文，直接判断K线时间） ──────────────
        if ind == CI.TIME_OF_DAY:
            return self._check_time_of_day(p, bars)
        return False, 0.0