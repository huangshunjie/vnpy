"""
market_behavior/engine/label_engine.py
Phase 6: 行为标签引擎

标签规则：
  TREND_STRONG     综合强度 >= 0.7
  TREND_WEAK       综合强度 <= 0.3
  CONTINUOUS_RISE  连续上涨 >= 3 天
  LIMIT_DENSE      近 10 日涨停 >= 3 次
  BREAKOUT         突破次数 >= 2
  HIGH_VOLATILITY  ATR% >= 均值 × 1.5
  REVERSAL         出现锤子/早晨之星等反转形态
  CONSOLIDATION    ATR% <= 均值 × 0.5 且无方向性
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..constant import LabelType, FactorType
from ..model.candle import CandleBar
from ..model.behavior_factor import BehaviorFactor
from ..model.label import BehaviorLabel
from ..utils.calculator import consecutive_count


class LabelEngine:
    """行为标签引擎 (Phase 6)。"""

    DEFAULT_CFG: Dict[str, Any] = {
        # TREND_STRONG / WEAK
        "strong_threshold":      0.65,
        "weak_threshold":        0.30,
        # CONTINUOUS_RISE
        "cont_rise_days":        3,
        # LIMIT_DENSE
        "limit_dense_window":    10,
        "limit_dense_count":     3,
        # BREAKOUT
        "breakout_threshold":    2.0,   # BREAKOUT_COUNT factor.value >= 2
        # HIGH_VOLATILITY
        "high_vol_ratio":        1.5,   # atr_pct >= history_mean × 1.5
        "vol_history_window":    20,    # 历史 atr_pct 均值窗口
        # REVERSAL（依赖 K线形态标记，通过最近 change_pct 变化判断）
        "reversal_change_thr":   -5.0,  # 前期跌幅阈值（% ）
        "reversal_rebound_thr":   3.0,  # 反弹涨幅阈值（%）
        # CONSOLIDATION
        "consol_vol_ratio":       0.6,  # atr_pct <= history_mean × 0.6
        "consol_direction_thr":   0.55, # rise_days 在 45~55% 之间（无方向）
    }

    def __init__(
        self,
        log_fn: Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
        dispatch_fn: Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        self._log         = log_fn or print
        self._main_engine = main_engine
        self._dispatch    = dispatch_fn
        self._running     = False
        self._cfg         = dict(self.DEFAULT_CFG)
        self._candle_buf  = None
        self._label_count = 0

    def set_main_engine(self, e):   self._main_engine = e
    def set_dispatch(self, fn):     self._dispatch = fn
    def set_candle_buffer(self, b): self._candle_buf = b
    def configure(self, **kw):      self._cfg.update(kw)

    def init(self):  self._log("[LabelEngine] init()")
    def start(self): self._running = True;  self._log("[LabelEngine] start()")
    def stop(self):  self._running = False; self._log("[LabelEngine] stop()")

    def summary(self) -> dict:
        return {"engine": "LabelEngine",
                "status": "running" if self._running else "stopped",
                "labeled": self._label_count}

    # ══════════════════════════════════════════════════════════════════
    # 主标注入口
    # ══════════════════════════════════════════════════════════════════

    def label(
        self,
        symbol: str,
        factors: Optional[List[BehaviorFactor]] = None,
        n_bars: int = 30,
    ) -> Optional[BehaviorLabel]:
        """
        对 symbol 生成行为标签。
        factors: 来自 FactorEngine.compute() 的因子列表（可选，不传则自动计算）。
        """
        if not self._candle_buf:
            return None
        bars = self._candle_buf.get(symbol, n_bars)
        if not bars:
            return None

        latest = bars[-1]

        # 整理因子 dict {FactorType: BehaviorFactor}
        factor_map: Dict[FactorType, BehaviorFactor] = {}
        if factors:
            for f in factors:
                factor_map[f.factor_type] = f

        labels:  List[LabelType] = []
        scores:  Dict[str, float] = {}
        reasons: Dict[str, str]   = {}

        # 各规则逐一评估
        rules = [
            (LabelType.TREND_STRONG,    self._rule_trend_strong),
            (LabelType.TREND_WEAK,      self._rule_trend_weak),
            (LabelType.CONTINUOUS_RISE, self._rule_continuous_rise),
            (LabelType.LIMIT_DENSE,     self._rule_limit_dense),
            (LabelType.BREAKOUT,        self._rule_breakout),
            (LabelType.HIGH_VOLATILITY, self._rule_high_volatility),
            (LabelType.REVERSAL,        self._rule_reversal),
            (LabelType.CONSOLIDATION,   self._rule_consolidation),
        ]

        for lt, rule_fn in rules:
            triggered, score, reason = rule_fn(bars, factor_map)
            if triggered:
                labels.append(lt)
                scores[lt.value]  = round(score, 4)
                reasons[lt.value] = reason

        bl = BehaviorLabel(
            label_id=uuid.uuid4().hex[:12],
            symbol=symbol,
            dt=latest.dt,
            labels=labels,
            scores=scores,
            reasons=reasons,
        )
        self._label_count += len(labels)
        self._emit_label(bl)
        return bl

    def label_bar(
        self,
        bar: CandleBar,
        factors: Optional[List[BehaviorFactor]] = None,
    ) -> Optional[BehaviorLabel]:
        """流式模式：每收到新K线后调用。"""
        if self._candle_buf:
            self._candle_buf.push(bar)
        return self.label(bar.symbol, factors=factors)

    # ══════════════════════════════════════════════════════════════════
    # 规则 1: TREND_STRONG
    # ══════════════════════════════════════════════════════════════════

    def _rule_trend_strong(self, bars, fm):
        f = fm.get(FactorType.KLINE_STRENGTH)
        if f and f.value >= self._cfg["strong_threshold"]:
            return True, f.value, f"strength={f.value:.3f}>={self._cfg['strong_threshold']}"
        # 无因子时回退到简单判断：近 10 日上涨天数 >= 70%
        wb = bars[-10:]
        rise_rate = sum(1 for b in wb if b.change_pct > 0) / len(wb) if wb else 0
        if rise_rate >= 0.70:
            return True, rise_rate, f"rise_rate={rise_rate:.0%}>=70%"
        return False, 0.0, ""

    # ══════════════════════════════════════════════════════════════════
    # 规则 2: TREND_WEAK
    # ══════════════════════════════════════════════════════════════════

    def _rule_trend_weak(self, bars, fm):
        f = fm.get(FactorType.KLINE_STRENGTH)
        if f and f.value <= self._cfg["weak_threshold"]:
            return True, 1.0 - f.value, f"strength={f.value:.3f}<={self._cfg['weak_threshold']}"
        wb = bars[-10:]
        fall_rate = sum(1 for b in wb if b.change_pct < 0) / len(wb) if wb else 0
        if fall_rate >= 0.70:
            return True, fall_rate, f"fall_rate={fall_rate:.0%}>=70%"
        return False, 0.0, ""

    # ══════════════════════════════════════════════════════════════════
    # 规则 3: CONTINUOUS_RISE
    # ══════════════════════════════════════════════════════════════════

    def _rule_continuous_rise(self, bars, fm):
        min_days = self._cfg["cont_rise_days"]
        flags    = [bars[i].close > bars[i-1].close for i in range(1, len(bars))]
        days     = consecutive_count(flags)
        if days >= min_days:
            score = min(days / (min_days * 2), 1.0)
            return True, score, f"consecutive_rise={days}days>={min_days}"
        return False, 0.0, ""

    # ══════════════════════════════════════════════════════════════════
    # 规则 4: LIMIT_DENSE
    # ══════════════════════════════════════════════════════════════════

    def _rule_limit_dense(self, bars, fm):
        cfg   = self._cfg
        win   = cfg["limit_dense_window"]
        thr   = cfg["limit_dense_count"]
        wb    = bars[-win:]
        count = sum(1 for b in wb if b.is_limit_up)
        if count >= thr:
            score = min(count / (thr * 2), 1.0)
            return True, score, f"limit_up_count({win})={count}>={thr}"
        return False, 0.0, ""

    # ══════════════════════════════════════════════════════════════════
    # 规则 5: BREAKOUT
    # ══════════════════════════════════════════════════════════════════

    def _rule_breakout(self, bars, fm):
        f = fm.get(FactorType.BREAKOUT_COUNT)
        thr = self._cfg["breakout_threshold"]
        if f and f.value >= thr:
            return True, min(f.norm_value * 1.2, 1.0), f"breakout_count={f.value:.1f}>={thr}"
        # 无因子：简单计算近 10 日价格新高次数
        wb = bars[-10:]
        count = 0
        for i in range(1, len(wb)):
            prev_max = max(b.close for b in wb[:i])
            if wb[i].close > prev_max:
                count += 1
        if count >= thr:
            return True, min(count / 5, 1.0), f"price_new_high_count={count}>={thr}"
        return False, 0.0, ""

    # ══════════════════════════════════════════════════════════════════
    # 规则 6: HIGH_VOLATILITY
    # ══════════════════════════════════════════════════════════════════

    def _rule_high_volatility(self, bars, fm):
        f = fm.get(FactorType.VOLATILITY)
        if f and f.value > 0:
            # 用历史 ATR% 均值作基准（简化：用近 20 根振幅均值）
            wb  = bars[-20:]
            if len(wb) >= 5:
                hist_amp = sum(b.amplitude for b in wb) / len(wb)
                if hist_amp > 0:
                    ratio = f.value / hist_amp
                    thr   = self._cfg["high_vol_ratio"]
                    if ratio >= thr:
                        return True, min(ratio / (thr * 2), 1.0), \
                               f"atr_pct={f.value:.3f}>=mean×{thr}"
        # 无因子：用最近振幅 vs 历史均值
        wb = bars[-20:]
        if len(wb) < 5:
            return False, 0.0, ""
        hist_amp  = sum(b.amplitude for b in wb[:-1]) / (len(wb) - 1)
        latest_amp = bars[-1].amplitude
        thr = self._cfg["high_vol_ratio"]
        if hist_amp > 0 and latest_amp >= hist_amp * thr:
            score = min(latest_amp / hist_amp / (thr * 2), 1.0)
            return True, score, f"amplitude={latest_amp:.2f}>=mean×{thr}"
        return False, 0.0, ""

    # ══════════════════════════════════════════════════════════════════
    # 规则 7: REVERSAL
    # ══════════════════════════════════════════════════════════════════

    def _rule_reversal(self, bars, fm):
        """
        反转信号：
          前期下跌（近 5 根中最大单日跌幅 <= reversal_change_thr）
          最新一根强势反弹（change_pct >= reversal_rebound_thr）
        """
        cfg = self._cfg
        if len(bars) < 3:
            return False, 0.0, ""
        prev_bars  = bars[-6:-1]
        latest     = bars[-1]
        min_change = min((b.change_pct for b in prev_bars), default=0)
        if (min_change <= cfg["reversal_change_thr"]
                and latest.change_pct >= cfg["reversal_rebound_thr"]):
            score = min(latest.change_pct / (cfg["reversal_rebound_thr"] * 3), 1.0)
            return True, score, (f"prev_min_change={min_change:.2f}%"
                                 f"<=thr, rebound={latest.change_pct:.2f}%")
        return False, 0.0, ""

    # ══════════════════════════════════════════════════════════════════
    # 规则 8: CONSOLIDATION
    # ══════════════════════════════════════════════════════════════════

    def _rule_consolidation(self, bars, fm):
        """
        盘整：低波动 + 无明显方向。
        ATR% <= hist_mean × consol_vol_ratio
        且 rise_days 在 consol_direction_thr 两侧（接近 50%）
        """
        cfg = self._cfg
        wb  = bars[-20:]
        if len(wb) < 5:
            return False, 0.0, ""

        hist_amp   = sum(b.amplitude for b in wb[:-1]) / (len(wb) - 1)
        latest_amp = bars[-1].amplitude
        rise_rate  = sum(1 for b in wb if b.change_pct > 0) / len(wb)
        low_vol    = hist_amp > 0 and latest_amp <= hist_amp * cfg["consol_vol_ratio"]
        no_dir     = abs(rise_rate - 0.5) <= (0.5 - cfg["consol_direction_thr"] + 0.5)

        if low_vol and no_dir:
            score = 1.0 - abs(rise_rate - 0.5) * 2
            return True, score, (f"amplitude={latest_amp:.2f}<=mean×"
                                 f"{cfg['consol_vol_ratio']}, rise={rise_rate:.0%}")
        return False, 0.0, ""

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, et: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(et, data)
            except Exception:
                pass

    def _emit_label(self, bl: BehaviorLabel) -> None:
        from ..event import EVENT_MB_LABEL_UPDATED
        self._emit(EVENT_MB_LABEL_UPDATED, bl.to_dict())
