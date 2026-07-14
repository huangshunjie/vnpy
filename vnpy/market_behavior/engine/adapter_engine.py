"""
market_behavior/engine/adapter_engine.py
Phase 7: 选股条件适配引擎

功能：
  build_condition()      构建标准选股条件对象
  build_from_label()     从 BehaviorLabel 生成条件集合
  build_from_factor()    从因子阈值生成条件
  evaluate()             对单只股票评估条件组合，返回是否通过 + 得分
  screen()               对 symbol 列表批量评分，返回通过条件的股票排名
  to_dict() / to_json()  条件序列化
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..constant import FactorType, LabelType
from ..model.behavior_factor import BehaviorFactor
from ..model.label import BehaviorLabel
from ..model.candle import CandleBar
from ..utils.calculator import consecutive_count


# ── 条件类型常量 ──────────────────────────────────────────────────────
COND_LIMIT_UP_COUNT  = "limit_up_count"
COND_LIMIT_DOWN_COUNT = "limit_down_count"
COND_RISE_PCT        = "rise_pct"
COND_FALL_PCT        = "fall_pct"
COND_KLINE_STRENGTH  = "kline_strength"
COND_RISE_DAYS       = "rise_days"
COND_BIG_YANG_COUNT  = "big_yang_count"
COND_BREAKOUT_COUNT  = "breakout_count"
COND_VOLATILITY      = "volatility"
COND_LABEL           = "label"
COND_CONTINUOUS      = "continuous"
COND_CUSTOM          = "custom"


class ScreenCondition:
    """
    单个选股条件。
    包含条件类型、参数、权重（用于评分时加权）。
    """

    def __init__(
        self,
        cond_type: str,
        params:    Dict[str, Any],
        weight:    float = 1.0,
        name:      str   = "",
    ) -> None:
        self.cond_id   = uuid.uuid4().hex[:8]
        self.cond_type = cond_type
        self.params    = params
        self.weight    = weight
        self.name      = name or f"{cond_type}_{self.cond_id}"

    def to_dict(self) -> dict:
        return {
            "cond_id":   self.cond_id,
            "cond_type": self.cond_type,
            "params":    self.params,
            "weight":    self.weight,
            "name":      self.name,
        }


class ScreenSpec:
    """
    选股规格：一组条件 + 排序方式。
    conditions 之间默认 AND 逻辑；若 require_all=False 则 OR。
    """

    def __init__(
        self,
        name:        str,
        conditions:  List[ScreenCondition],
        sort_by:     str   = COND_KLINE_STRENGTH,
        order:       str   = "desc",
        require_all: bool  = True,
        top_n:       int   = 0,
    ) -> None:
        self.spec_id     = uuid.uuid4().hex[:8]
        self.name        = name
        self.conditions  = conditions
        self.sort_by     = sort_by
        self.order       = order
        self.require_all = require_all
        self.top_n       = top_n

    def to_dict(self) -> dict:
        return {
            "spec_id":     self.spec_id,
            "name":        self.name,
            "conditions":  [c.to_dict() for c in self.conditions],
            "sort_by":     self.sort_by,
            "order":       self.order,
            "require_all": self.require_all,
            "top_n":       self.top_n,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class ScreenResult:
    """单只股票的评估结果。"""

    def __init__(
        self,
        symbol:  str,
        passed:  bool,
        score:   float,
        details: Dict[str, Any],
        dt:      Optional[datetime] = None,
    ) -> None:
        self.symbol  = symbol
        self.passed  = passed
        self.score   = round(score, 6)
        self.details = details
        self.dt      = dt or datetime.now()

    def to_dict(self) -> dict:
        return {
            "symbol":  self.symbol,
            "passed":  self.passed,
            "score":   self.score,
            "details": self.details,
            "dt":      str(self.dt)[:19],
        }


class AdapterEngine:
    """
    选股条件适配引擎 (Phase 7)。

    依赖：
      CandleEngine.buffer  (set_candle_buffer)
      FactorEngine         (set_factor_engine)
      LabelEngine          (set_label_engine)
    """

    DEFAULT_CFG: Dict[str, Any] = {
        "default_window":       20,
        "big_yang_change":      3.0,
        "big_yang_body_ratio":  0.55,
        "score_pass_threshold": 0.5,    # 评分 >= 0.5 才算通过
    }

    def __init__(
        self,
        log_fn:      Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
        dispatch_fn: Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        self._log          = log_fn or print
        self._main_engine  = main_engine
        self._dispatch     = dispatch_fn
        self._running      = False
        self._cfg          = dict(self.DEFAULT_CFG)
        self._candle_buf   = None
        self._factor_engine = None
        self._label_engine  = None
        self._screen_count  = 0

    def set_main_engine(self, e):        self._main_engine  = e
    def set_dispatch(self, fn):          self._dispatch     = fn
    def set_candle_buffer(self, b):      self._candle_buf   = b
    def set_factor_engine(self, fe):     self._factor_engine = fe
    def set_label_engine(self, le):      self._label_engine  = le
    def configure(self, **kw):           self._cfg.update(kw)

    def init(self):  self._log("[AdapterEngine] init()")
    def start(self): self._running = True;  self._log("[AdapterEngine] start()")
    def stop(self):  self._running = False; self._log("[AdapterEngine] stop()")

    def summary(self) -> dict:
        return {
            "engine":  "AdapterEngine",
            "status":  "running" if self._running else "stopped",
            "screened": self._screen_count,
        }

    # ══════════════════════════════════════════════════════════════════
    # 条件构建接口
    # ══════════════════════════════════════════════════════════════════

    def build_condition(
        self,
        cond_type: str,
        weight:    float = 1.0,
        name:      str   = "",
        **params,
    ) -> ScreenCondition:
        """
        构建单个选股条件。
        示例：
          build_condition("limit_up_count", window=10, min=3)
          build_condition("kline_strength",  min=0.65)
          build_condition("continuous",      kind="rise", days=3)
          build_condition("label",           include=["TREND_STRONG"])
        """
        return ScreenCondition(cond_type, params, weight=weight, name=name)

    def build_from_label(
        self,
        label:      BehaviorLabel,
        min_score:  float = 0.3,
        weight_map: Optional[Dict[str, float]] = None,
    ) -> List[ScreenCondition]:
        """
        从 BehaviorLabel 生成对应的选股条件列表。
        每个标签转为一个 COND_LABEL 条件，权重来自 scores。
        """
        conditions = []
        wmap = weight_map or {}
        for lt in label.labels:
            score  = label.scores.get(lt.value, 0.0)
            if score < min_score:
                continue
            weight = wmap.get(lt.value, score)
            cond   = ScreenCondition(
                COND_LABEL,
                {"include": [lt.value]},
                weight=weight,
                name=f"label_{lt.value}",
            )
            conditions.append(cond)
        return conditions

    def build_from_factor(
        self,
        factors:    List[BehaviorFactor],
        thresholds: Optional[Dict[str, float]] = None,
        weight_map: Optional[Dict[str, float]] = None,
    ) -> List[ScreenCondition]:
        """
        从因子列表生成阈值条件。
        thresholds: {factor_type_value: min_norm_value}
        默认对 KLINE_STRENGTH >= 0.5、RISE_DAYS >= 0.5 生成条件。
        """
        default_thr = {
            FactorType.KLINE_STRENGTH.value: 0.50,
            FactorType.RISE_DAYS.value:      0.50,
            FactorType.LIMIT_UP_COUNT.value: 0.0,   # 只要存在涨停记录
        }
        thr  = {**default_thr, **(thresholds or {})}
        wmap = weight_map or {}

        conditions = []
        for f in factors:
            min_norm = thr.get(f.factor_type.value)
            if min_norm is None:
                continue
            if f.norm_value < min_norm:
                continue
            weight = wmap.get(f.factor_type.value, f.norm_value)
            ctype  = self._factor_type_to_cond(f.factor_type)
            cond   = ScreenCondition(
                ctype,
                {"min": min_norm, "window": f.window},
                weight=weight,
                name=f"factor_{f.factor_type.value}",
            )
            conditions.append(cond)
        return conditions

    def build_spec(
        self,
        name:        str,
        conditions:  List[ScreenCondition],
        sort_by:     str  = COND_KLINE_STRENGTH,
        order:       str  = "desc",
        require_all: bool = True,
        top_n:       int  = 0,
    ) -> ScreenSpec:
        """组装 ScreenSpec（选股规格）。"""
        return ScreenSpec(name, conditions, sort_by=sort_by, order=order,
                          require_all=require_all, top_n=top_n)

    # ══════════════════════════════════════════════════════════════════
    # 单只股票评估
    # ══════════════════════════════════════════════════════════════════

    def evaluate(
        self,
        symbol:  str,
        spec:    ScreenSpec,
        factors: Optional[List[BehaviorFactor]] = None,
        label:   Optional[BehaviorLabel]        = None,
    ) -> ScreenResult:
        """
        对单只股票评估选股规格，返回 ScreenResult。
        factors / label 可外部传入，不传则自动计算。
        """
        # ── 准备数据 ──────────────────────────────────────────────────
        bars = self._candle_buf.get(symbol, 60) if self._candle_buf else []
        if not bars:
            return ScreenResult(symbol, False, 0.0, {"reason": "no_data"})

        if factors is None and self._factor_engine:
            factors = self._factor_engine.compute(symbol)
        if label is None and self._label_engine:
            label = self._label_engine.label(symbol, factors=factors)

        fmap = {f.factor_type: f for f in (factors or [])}

        # ── 逐条件评估 ────────────────────────────────────────────────
        cond_results: Dict[str, Tuple[bool, float]] = {}
        for cond in spec.conditions:
            passed, score = self._eval_condition(cond, bars, fmap, label)
            cond_results[cond.name] = (passed, score)

        # ── 汇总：AND / OR ────────────────────────────────────────────
        all_pass  = all(r[0] for r in cond_results.values())
        any_pass  = any(r[0] for r in cond_results.values())
        final_pass = all_pass if spec.require_all else any_pass

        # ── 加权得分 ──────────────────────────────────────────────────
        total_w = sum(c.weight for c in spec.conditions) or 1.0
        score   = sum(
            c.weight * cond_results[c.name][1]
            for c in spec.conditions
        ) / total_w

        self._screen_count += 1
        latest = bars[-1]
        result = ScreenResult(
            symbol, final_pass, score,
            details={
                "conditions": {k: {"passed": v[0], "score": round(v[1], 4)}
                               for k, v in cond_results.items()},
                "factors":    {f.factor_type.value: round(f.norm_value, 4)
                               for f in (factors or [])},
                "labels":     [l.value for l in (label.labels if label else [])],
            },
            dt=latest.dt,
        )
        self._emit_result(result, spec.name)
        return result

    # ══════════════════════════════════════════════════════════════════
    # 批量筛选
    # ══════════════════════════════════════════════════════════════════

    def screen(
        self,
        symbols: List[str],
        spec:    ScreenSpec,
    ) -> List[ScreenResult]:
        """
        对 symbol 列表批量评估，返回按 score 排序的 ScreenResult 列表。
        若 spec.top_n > 0，只返回前 top_n 只。
        """
        results: List[ScreenResult] = []
        for sym in symbols:
            r = self.evaluate(sym, spec)
            if r.passed:
                results.append(r)

        # 排序
        reverse = (spec.order.lower() == "desc")
        results.sort(key=lambda r: r.score, reverse=reverse)

        if spec.top_n > 0:
            results = results[:spec.top_n]

        self._emit_screen_done(spec.name, len(results))
        return results

    # ══════════════════════════════════════════════════════════════════
    # 条件评估核心
    # ══════════════════════════════════════════════════════════════════

    def _eval_condition(
        self,
        cond:    ScreenCondition,
        bars:    List[CandleBar],
        fmap:    Dict[FactorType, BehaviorFactor],
        label:   Optional[BehaviorLabel],
    ) -> Tuple[bool, float]:
        """返回 (passed, score 0~1)。"""
        ct = cond.cond_type
        p  = cond.params

        # ── 因子阈值类条件 ────────────────────────────────────────────
        if ct == COND_KLINE_STRENGTH:
            f = fmap.get(FactorType.KLINE_STRENGTH)
            if f is None:
                return self._fallback_rise_rate(bars, p.get("min", 0.5))
            return self._threshold(f.norm_value, p.get("min", 0.0),
                                   p.get("max", 1.0))

        if ct == COND_RISE_DAYS:
            f = fmap.get(FactorType.RISE_DAYS)
            if f is None:
                wb    = bars[-p.get("window", 20):]
                value = sum(1 for b in wb if b.change_pct > 0) / len(wb) if wb else 0
                return self._threshold(value, p.get("min", 0.0))
            return self._threshold(f.norm_value, p.get("min", 0.0))

        if ct == COND_BIG_YANG_COUNT:
            f = fmap.get(FactorType.BIG_YANG_COUNT)
            if f is None:
                return False, 0.0
            return self._threshold(f.value, p.get("min", 1))

        if ct == COND_LIMIT_UP_COUNT:
            f = fmap.get(FactorType.LIMIT_UP_COUNT)
            win = p.get("window", 10)
            min_cnt = p.get("min", 1)
            if f is not None and f.window == win:
                return self._threshold(f.value, min_cnt)
            # 直接从 bars 计数
            wb  = bars[-win:]
            cnt = sum(1 for b in wb if b.is_limit_up)
            return self._threshold(cnt, min_cnt,
                                   score=min(cnt / max(min_cnt * 2, 1), 1.0))

        if ct == COND_LIMIT_DOWN_COUNT:
            win     = p.get("window", 10)
            min_cnt = p.get("min", 1)
            wb      = bars[-win:]
            cnt     = sum(1 for b in wb if b.is_limit_down)
            return self._threshold(cnt, min_cnt,
                                   score=min(cnt / max(min_cnt * 2, 1), 1.0))

        if ct == COND_BREAKOUT_COUNT:
            f = fmap.get(FactorType.BREAKOUT_COUNT)
            if f is None:
                return False, 0.0
            return self._threshold(f.value, p.get("min", 2.0))

        if ct == COND_VOLATILITY:
            f = fmap.get(FactorType.VOLATILITY)
            if f is None:
                return False, 0.0
            return self._threshold(f.value,
                                   p.get("min", 0.0), p.get("max", 999.0))

        if ct == COND_RISE_PCT:
            win = p.get("window", 10)
            thr = p.get("threshold", 5.0)
            cnt = p.get("min", 1)
            wb  = bars[-win:]
            n   = sum(1 for b in wb if b.change_pct >= thr)
            return self._threshold(n, cnt,
                                   score=min(n / max(cnt * 2, 1), 1.0))

        if ct == COND_FALL_PCT:
            win = p.get("window", 10)
            thr = p.get("threshold", 5.0)
            cnt = p.get("min", 1)
            wb  = bars[-win:]
            n   = sum(1 for b in wb if b.change_pct <= -thr)
            return self._threshold(n, cnt,
                                   score=min(n / max(cnt * 2, 1), 1.0))

        # ── 连续行为条件 ──────────────────────────────────────────────
        if ct == COND_CONTINUOUS:
            kind     = p.get("kind", "rise")
            req_days = p.get("days", 3)
            flags    = self._continuous_flags(bars, kind)
            days     = consecutive_count(flags)
            passed   = days >= req_days
            score    = min(days / max(req_days * 2, 1), 1.0)
            return passed, score

        # ── 标签条件 ──────────────────────────────────────────────────
        if ct == COND_LABEL:
            if label is None:
                return False, 0.0
            include = [LabelType(v) for v in p.get("include", [])
                       if v in {lt.value for lt in LabelType}]
            exclude = [LabelType(v) for v in p.get("exclude", [])
                       if v in {lt.value for lt in LabelType}]
            label_set = set(label.labels)

            if exclude and any(lt in label_set for lt in exclude):
                return False, 0.0
            if not include:
                return True, 1.0
            matched = [lt for lt in include if lt in label_set]
            if not matched:
                return False, 0.0
            score = sum(label.scores.get(lt.value, 0.5) for lt in matched) / len(include)
            return True, min(score, 1.0)

        # ── 自定义条件（外部注入 callable）────────────────────────────
        if ct == COND_CUSTOM:
            fn = p.get("fn")
            if callable(fn):
                try:
                    result = fn(bars, fmap, label)
                    if isinstance(result, tuple):
                        return bool(result[0]), float(result[1])
                    return bool(result), 1.0 if result else 0.0
                except Exception:
                    return False, 0.0

        return False, 0.0

    # ── 工具方法 ──────────────────────────────────────────────────────

    @staticmethod
    def _threshold(
        value: float,
        min_val: float = 0.0,
        max_val: float = float("inf"),
        score:   Optional[float] = None,
    ) -> Tuple[bool, float]:
        passed = min_val <= value <= max_val
        if score is not None:
            return passed, score if passed else 0.0
        # 线性归一化得分（超过 min_val×2 算满分）
        if min_val > 0:
            s = min(value / (min_val * 2), 1.0)
        else:
            s = min(value, 1.0)
        return passed, s if passed else 0.0

    @staticmethod
    def _fallback_rise_rate(
        bars: List[CandleBar], min_val: float
    ) -> Tuple[bool, float]:
        """无因子时回退到简单上涨率判断。"""
        if not bars:
            return False, 0.0
        wb    = bars[-10:]
        rate  = sum(1 for b in wb if b.change_pct > 0) / len(wb)
        return rate >= min_val, rate if rate >= min_val else 0.0

    @staticmethod
    def _continuous_flags(bars: List[CandleBar], kind: str) -> List[bool]:
        if kind == "rise":
            return [bars[i].close > bars[i-1].close for i in range(1, len(bars))]
        if kind == "fall":
            return [bars[i].close < bars[i-1].close for i in range(1, len(bars))]
        if kind == "new_high":
            flags = []
            for i in range(1, len(bars)):
                flags.append(bars[i].close > max(b.close for b in bars[:i]))
            return flags
        if kind == "new_low":
            flags = []
            for i in range(1, len(bars)):
                flags.append(bars[i].close < min(b.close for b in bars[:i]))
            return flags
        if kind == "vol_up":
            flags = []
            for i in range(1, len(bars)):
                prev_vols = [bars[j].volume for j in range(max(0, i-5), i)]
                vol_ma    = sum(prev_vols) / len(prev_vols) if prev_vols else 0
                flags.append(vol_ma > 0 and bars[i].volume / vol_ma >= 1.5)
            return flags
        return []

    @staticmethod
    def _factor_type_to_cond(ft: FactorType) -> str:
        mapping = {
            FactorType.KLINE_STRENGTH:  COND_KLINE_STRENGTH,
            FactorType.RISE_DAYS:       COND_RISE_DAYS,
            FactorType.LIMIT_UP_COUNT:  COND_LIMIT_UP_COUNT,
            FactorType.BIG_YANG_COUNT:  COND_BIG_YANG_COUNT,
            FactorType.BREAKOUT_COUNT:  COND_BREAKOUT_COUNT,
            FactorType.VOLATILITY:      COND_VOLATILITY,
        }
        return mapping.get(ft, COND_CUSTOM)

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, et: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(et, data)
            except Exception:
                pass

    def _emit_result(self, r: ScreenResult, spec_name: str) -> None:
        from ..event import EVENT_MB_CONDITION_READY
        self._emit(EVENT_MB_CONDITION_READY, {
            **r.to_dict(), "spec_name": spec_name,
        })

    def _emit_screen_done(self, spec_name: str, count: int) -> None:
        from ..event import EVENT_MB_CONDITION_READY
        self._emit(EVENT_MB_CONDITION_READY, {
            "type":      "screen_done",
            "spec_name": spec_name,
            "count":     count,
        })
