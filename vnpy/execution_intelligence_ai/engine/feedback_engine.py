"""
execution_intelligence_ai/engine/feedback_engine.py  (Phase 5)

FeedbackEngine — 执行质量反馈引擎。
功能：记录切片成交 / 汇总指标 / 质量评分 / 闭环调参建议
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from ..constant import FeedbackMetric
from ..model.feedback_model import (
    SliceFeedback, FeedbackState, ExecutionReport)


class FeedbackEngine:
    """执行质量反馈引擎（Phase 5 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log     = log_fn or (lambda m: None)
        self._pending: dict[str, list[SliceFeedback]] = {}
        self._reports: dict[str, ExecutionReport]     = {}
        self._meta:    dict[str, dict]                = {}

    def init(self)  -> None: self._log("[FeedbackEngine] init()")
    def start(self) -> None: self._log("[FeedbackEngine] start()")
    def stop(self)  -> None: self._log("[FeedbackEngine] stop()")

    def begin_execution(self, execution_id, symbol, direction,
                        strategy, total_volume) -> None:
        self._pending[execution_id] = []
        self._meta[execution_id] = {
            "symbol": symbol, "direction": direction,
            "strategy": strategy, "total_volume": total_volume,
            "started_at": datetime.now(),
        }
        self._log(f"[FeedbackEngine] begin: {execution_id} symbol={symbol} vol={total_volume}")

    def record_slice(self, execution_id, slice_id, sequence,
                     planned_volume, filled_volume,
                     planned_price, filled_price,
                     venue_id="", latency_ms=0.0,
                     submitted_at=None, filled_at=None) -> SliceFeedback:
        if execution_id not in self._pending:
            self._pending[execution_id] = []
        slippage_bps = 0.0
        if planned_price > 0 and filled_price > 0:
            direction = self._meta.get(execution_id, {}).get("direction", "long")
            sign = 1 if direction == "long" else -1
            slippage_bps = round(sign * (filled_price - planned_price) / planned_price * 10000, 4)
        fill_rate = round(min(filled_volume / max(planned_volume, 1e-9), 1.0), 6)
        sf = SliceFeedback(
            slice_id=slice_id, sequence=sequence,
            planned_volume=planned_volume, filled_volume=filled_volume,
            planned_price=planned_price, filled_price=filled_price,
            slippage_bps=slippage_bps, latency_ms=latency_ms,
            venue_id=venue_id, fill_rate=fill_rate,
            submitted_at=submitted_at, filled_at=filled_at or datetime.now(),
        )
        self._pending[execution_id].append(sf)
        self._log(f"[FeedbackEngine] slice: {execution_id}/{slice_id} "
                  f"fill={fill_rate:.1%} slip={slippage_bps:.2f}bp lat={latency_ms:.1f}ms")
        return sf

    def complete_execution(self, execution_id, realized_impact_bps=0.0,
                           market_vwap=0.0) -> ExecutionReport:
        slices = self._pending.get(execution_id, [])
        meta   = self._meta.get(execution_id, {})
        fb     = self._compute_feedback(execution_id, slices, meta,
                                        realized_impact_bps, market_vwap)
        recs, next_params = self._generate_recommendations(fb, meta)
        report = ExecutionReport(
            execution_id=execution_id,
            symbol=meta.get("symbol",""), direction=meta.get("direction",""),
            strategy=meta.get("strategy",""), total_volume=meta.get("total_volume",0.0),
            feedback=fb, recommendations=recs, next_params=next_params,
        )
        self._reports[execution_id] = report
        self._log(f"[FeedbackEngine] report: {execution_id} "
                  f"fill={fb.fill_rate:.1%} slip={fb.slippage_bps:.2f}bp "
                  f"cost={fb.total_cost_bps:.2f}bp score={fb.quality_score:.1f}")
        return report

    def _compute_feedback(self, execution_id, slices, meta,
                          realized_impact_bps, market_vwap) -> FeedbackState:
        total_vol  = meta.get("total_volume", 0.0)
        started_at = meta.get("started_at", datetime.now())
        if not slices:
            return FeedbackState(execution_id=execution_id,
                                 symbol=meta.get("symbol",""),
                                 total_volume=total_vol,
                                 started_at=started_at,
                                 completed_at=datetime.now())
        filled_vol = sum(s.filled_volume for s in slices)
        fill_rate  = round(filled_vol / max(total_vol, 1e-9), 4)
        wt_slip    = (sum(s.filled_volume * s.slippage_bps for s in slices)
                      / max(filled_vol, 1e-9))
        avg_lat    = sum(s.latency_ms for s in slices) / len(slices)
        vwap_dev   = 0.0
        if market_vwap > 0 and filled_vol > 0:
            exec_vwap = (sum(s.filled_volume * s.filled_price for s in slices) / filled_vol)
            sign = 1 if meta.get("direction","long") == "long" else -1
            vwap_dev = round(sign * (exec_vwap - market_vwap) / market_vwap * 10000, 4)
        times = [s.filled_at for s in slices if s.filled_at is not None]
        duration_s = 0.0
        if times and started_at:
            duration_s = round((max(times) - started_at).total_seconds(), 2)
        n_filled   = sum(1 for s in slices if s.fill_rate >= 0.999)
        n_partial  = sum(1 for s in slices if 0.0 < s.fill_rate < 0.999)
        n_cancelled= sum(1 for s in slices if s.fill_rate == 0.0)
        commission_bps = 3.0
        total_cost = round(wt_slip + commission_bps + realized_impact_bps, 4)
        quality    = self._calc_quality_score(fill_rate, wt_slip, avg_lat)
        return FeedbackState(
            execution_id=execution_id, symbol=meta.get("symbol",""),
            direction=meta.get("direction",""), total_volume=total_vol,
            filled_volume=round(filled_vol,4), fill_rate=fill_rate,
            slippage_bps=round(wt_slip,4), commission_bps=commission_bps,
            market_impact_bps=realized_impact_bps, total_cost_bps=total_cost,
            vwap_deviation_bps=vwap_dev, avg_latency_ms=round(avg_lat,2),
            execution_duration_s=duration_s, n_slices=len(slices),
            n_filled=n_filled, n_partial=n_partial, n_cancelled=n_cancelled,
            quality_score=quality, started_at=started_at,
            completed_at=datetime.now(), slice_feedbacks=slices,
        )

    @staticmethod
    def _calc_quality_score(fill_rate, slippage_bps, avg_latency_ms) -> float:
        score_fill = fill_rate * 40.0
        score_slip = max(0.0, 40.0 * (1.0 - slippage_bps / 100.0))
        score_lat  = max(0.0, 20.0 * (1.0 - avg_latency_ms / 200.0))
        return round(score_fill + score_slip + score_lat, 2)

    def _generate_recommendations(self, fb: FeedbackState, meta: dict):
        recs: list[str] = []; next_p: dict = {}
        n = meta.get("n_slices", 10)
        if fb.slippage_bps > 20:
            new_n = min(int(n * 1.5), 200)
            recs.append(f"滑点过高 ({fb.slippage_bps:.2f}bp)，建议增加切片数: {n} -> {new_n}")
            next_p["n_slices"] = new_n
            next_p["interval_seconds"] = meta.get("interval_seconds", 60) * 2
        elif fb.slippage_bps < 3 and n > 5:
            new_n = max(int(n * 0.8), 5)
            recs.append(f"滑点极低 ({fb.slippage_bps:.2f}bp)，可减少切片数: {n} -> {new_n}")
            next_p["n_slices"] = new_n
        if fb.fill_rate < 0.9:
            recs.append(f"成交率偏低 ({fb.fill_rate:.1%})，建议使用 POV 策略")
            next_p["strategy"] = "pov"
        if fb.avg_latency_ms > 50:
            recs.append(f"延迟过高 ({fb.avg_latency_ms:.1f}ms)，建议路由模式切换为 fastest")
            next_p["routing_mode"] = "fastest"
        if fb.total_cost_bps > 30 and fb.total_volume >= 50000:
            recs.append(f"总成本高 ({fb.total_cost_bps:.2f}bp)，大单建议路由至暗池")
            next_p["routing_mode"] = "min_slippage"
        if not recs:
            recs.append(f"执行质量良好 (评分={fb.quality_score:.1f}/100)，参数可继续沿用")
        return recs, next_p

    def get_report(self, execution_id) -> ExecutionReport | None:
        return self._reports.get(execution_id)

    def get_all_reports(self) -> list[ExecutionReport]:
        return list(self._reports.values())

    def get_pending_slices(self, execution_id) -> list[SliceFeedback]:
        return self._pending.get(execution_id, [])

    def get_aggregate_stats(self) -> dict:
        reports = list(self._reports.values())
        if not reports: return {"count": 0}
        n = len(reports); fbs = [r.feedback for r in reports]
        return {
            "count":              n,
            "avg_fill_rate":      round(sum(f.fill_rate      for f in fbs) / n, 4),
            "avg_slippage_bps":   round(sum(f.slippage_bps   for f in fbs) / n, 4),
            "avg_total_cost_bps": round(sum(f.total_cost_bps  for f in fbs) / n, 4),
            "avg_quality_score":  round(sum(f.quality_score   for f in fbs) / n, 2),
            "avg_latency_ms":     round(sum(f.avg_latency_ms  for f in fbs) / n, 2),
        }

    def summary(self) -> dict:
        return {
            "phase":     5,
            "status":    "active",
            "pending":   len(self._pending),
            "completed": len(self._reports),
            "aggregate": self.get_aggregate_stats(),
        }
