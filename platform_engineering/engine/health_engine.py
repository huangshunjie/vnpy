"""
platform_engineering/engine/health_engine.py
HealthEngine 完整版 — Phase 5
四维评分（性能/风险/Alpha/执行）+ 健康状态自动判定
"""
from __future__ import annotations
import threading, uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from ..model.health import StrategyHealthRecord, HealthMetricSnapshot
from ..constant import HealthStatus, HealthLevel


class _T:
    SHARPE_GOOD=1.0; SHARPE_WARN=0.5; SHARPE_BAD=0.0
    DRAWDOWN_GOOD=0.10; DRAWDOWN_WARN=0.20; DRAWDOWN_BAD=0.30
    WIN_RATE_GOOD=0.55; WIN_RATE_WARN=0.45
    RISK_EXP_GOOD=0.20; RISK_EXP_WARN=0.40; RISK_EXP_BAD=0.60
    IC_GOOD=0.05; IC_WARN=0.02
    ALPHA_DECAY_OK=0.15; ALPHA_DECAY_WARN=0.30; ALPHA_DECAY_BAD=0.50
    DELAY_GOOD=200.0; DELAY_WARN=500.0; DELAY_BAD=1000.0
    FILL_GOOD=0.98; FILL_WARN=0.90
    SLIP_GOOD=5.0; SLIP_WARN=15.0; SLIP_BAD=30.0


def _sm(val, good, warn, bad, hi=True) -> float:
    if hi:
        if val >= good: return 100.0
        if val >= warn: return 60.0 + 40.0*(val-warn)/(good-warn) if good!=warn else 60.0
        if val >= bad:  return 20.0 + 40.0*(val-bad)/(warn-bad)  if warn!=bad  else 20.0
        return max(0.0, 20.0*val/bad if bad else 0.0)
    else:
        if val <= good: return 100.0
        if val <= warn: return 60.0 + 40.0*(warn-val)/(warn-good) if warn!=good else 60.0
        if val <= bad:  return 20.0 + 40.0*(bad-val)/(bad-warn)   if bad!=warn  else 20.0
        return 0.0


def _wt(parts) -> Optional[float]:
    if not parts: return None
    tw = sum(w for _,w in parts)
    return sum(s*w for s,w in parts)/tw if tw else None


class HealthScorer:
    DIM_WEIGHT = {"perf": 0.40, "risk": 0.25, "alpha": 0.20, "exec": 0.15}

    def compute(self, snap: HealthMetricSnapshot):
        warns: List[str] = []
        # perf
        pp = []
        if snap.sharpe is not None:
            pp.append((_sm(snap.sharpe, _T.SHARPE_GOOD, _T.SHARPE_WARN, _T.SHARPE_BAD), 0.50))
            if snap.sharpe < _T.SHARPE_WARN: warns.append(f"Sharpe \u504f\u4f4e ({snap.sharpe:.2f})")
        if snap.max_drawdown is not None:
            pp.append((_sm(snap.max_drawdown, _T.DRAWDOWN_GOOD, _T.DRAWDOWN_WARN, _T.DRAWDOWN_BAD, hi=False), 0.30))
            if snap.max_drawdown > _T.DRAWDOWN_WARN: warns.append(f"\u6700\u5927\u56de\u64a4 ({snap.max_drawdown*100:.1f}%)")
        if snap.win_rate is not None:
            pp.append((_sm(snap.win_rate, _T.WIN_RATE_GOOD, _T.WIN_RATE_WARN, 0.30), 0.20))
            if snap.win_rate < _T.WIN_RATE_WARN: warns.append(f"\u80dc\u7387\u504f\u4f4e ({snap.win_rate*100:.1f}%)")
        perf = _wt(pp)
        # risk
        rp = []
        if snap.risk_exposure is not None:
            rp.append((_sm(snap.risk_exposure, _T.RISK_EXP_GOOD, _T.RISK_EXP_WARN, _T.RISK_EXP_BAD, hi=False), 1.0))
            if snap.risk_exposure > _T.RISK_EXP_WARN: warns.append(f"\u98ce\u9669\u655e\u53e3 ({snap.risk_exposure*100:.1f}%)")
        risk = _wt(rp)
        # alpha
        ap = []
        if snap.ic_mean is not None:
            ap.append((_sm(snap.ic_mean, _T.IC_GOOD, _T.IC_WARN, 0.0), 0.60))
            if snap.ic_mean < _T.IC_WARN: warns.append(f"IC \u5747\u503c\u504f\u4f4e ({snap.ic_mean:.3f})")
        if snap.alpha_decay is not None:
            ap.append((_sm(snap.alpha_decay, _T.ALPHA_DECAY_OK, _T.ALPHA_DECAY_WARN, _T.ALPHA_DECAY_BAD, hi=False), 0.40))
            if snap.alpha_decay > _T.ALPHA_DECAY_WARN: warns.append(f"Alpha \u8870\u51cf ({snap.alpha_decay*100:.1f}%)")
        alpha = _wt(ap)
        # exec
        ep = []
        if snap.order_delay_ms is not None:
            ep.append((_sm(snap.order_delay_ms, _T.DELAY_GOOD, _T.DELAY_WARN, _T.DELAY_BAD, hi=False), 0.40))
            if snap.order_delay_ms > _T.DELAY_WARN: warns.append(f"\u8ba2\u5355\u5ef6\u8fdf ({snap.order_delay_ms:.0f}ms)")
        if snap.fill_rate is not None:
            ep.append((_sm(snap.fill_rate, _T.FILL_GOOD, _T.FILL_WARN, 0.70), 0.40))
            if snap.fill_rate < _T.FILL_WARN: warns.append(f"\u6210\u4ea4\u7387\u504f\u4f4e ({snap.fill_rate*100:.1f}%)")
        if snap.slippage_bps is not None:
            ep.append((_sm(snap.slippage_bps, _T.SLIP_GOOD, _T.SLIP_WARN, _T.SLIP_BAD, hi=False), 0.20))
            if snap.slippage_bps > _T.SLIP_WARN: warns.append(f"\u6ed1\u70b9\u504f\u9ad8 ({snap.slippage_bps:.1f}bps)")
        exc = _wt(ep)
        # total
        tp = [(s, w) for s, w in [
            (perf,  self.DIM_WEIGHT["perf"]),
            (risk,  self.DIM_WEIGHT["risk"]),
            (alpha, self.DIM_WEIGHT["alpha"]),
            (exc,   self.DIM_WEIGHT["exec"]),
        ] if s is not None]
        total = _wt(tp)
        return total, perf, risk, alpha, exc, warns


def _det_status(score, warns):
    if score is None: return HealthStatus.UNKNOWN, HealthLevel.YELLOW
    if score >= 70 and not warns: return HealthStatus.HEALTHY,  HealthLevel.GREEN
    if score >= 70:               return HealthStatus.WARNING,  HealthLevel.YELLOW
    if score >= 40:               return HealthStatus.WARNING,  HealthLevel.YELLOW
    if score >= 20:               return HealthStatus.CRITICAL, HealthLevel.RED
    return HealthStatus.RETIRE, HealthLevel.RED


class HealthEngine:
    def __init__(self) -> None:
        self._records:   Dict[str, StrategyHealthRecord] = {}
        self._scorer     = HealthScorer()
        self._callbacks: List[Callable[[StrategyHealthRecord], None]] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor   = threading.Event()

    def start(self) -> None: pass
    def stop(self)  -> None: self._stop_monitor.set()

    def register_strategy(self, strategy_id: str,
                          strategy_name: str) -> StrategyHealthRecord:
        rec = StrategyHealthRecord(
            health_id     = "HLT-" + uuid.uuid4().hex[:8].upper(),
            strategy_id   = strategy_id,
            strategy_name = strategy_name,
            status        = HealthStatus.UNKNOWN,
            level         = HealthLevel.YELLOW,
            score         = 0.0,
            created_at    = datetime.now(),
            last_checked  = datetime.now(),
        )
        self._records[strategy_id] = rec
        return rec

    def update_snapshot(self, strategy_id: str,
                        snapshot: HealthMetricSnapshot
                        ) -> Optional[StrategyHealthRecord]:
        rec = self._records.get(strategy_id)
        if not rec: return None
        rec.snapshot     = snapshot
        rec.last_checked = datetime.now()
        total, perf, risk, alpha, exc, warns = self._scorer.compute(snapshot)
        rec.score       = round(total, 1) if total is not None else 0.0
        rec.perf_score  = round(perf,  1) if perf  is not None else 0.0
        rec.risk_score  = round(risk,  1) if risk  is not None else 0.0
        rec.alpha_score = round(alpha, 1) if alpha is not None else 0.0
        rec.exec_score  = round(exc,   1) if exc   is not None else 0.0
        rec.warnings    = warns
        status, level   = _det_status(total, warns)
        prev = rec.status
        rec.status = status; rec.level = level
        if status == HealthStatus.RETIRE:
            rec.retire_reason = "; ".join(warns)
        if prev != status:
            for cb in self._callbacks:
                try: cb(rec)
                except Exception: pass
        return rec

    def get_health(self, strategy_id: str) -> Optional[StrategyHealthRecord]:
        return self._records.get(strategy_id)

    def list_health(self, status: Optional[HealthStatus] = None
                    ) -> List[StrategyHealthRecord]:
        items = list(self._records.values())
        if status: items = [r for r in items if r.status == status]
        return sorted(items, key=lambda r: r.score, reverse=True)

    def on_health_changed(self,
                          cb: Callable[[StrategyHealthRecord], None]) -> None:
        self._callbacks.append(cb)

    def start_monitor(self, interval_secs: int = 60,
                      snapshot_fn=None) -> None:
        self._stop_monitor.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_secs, snapshot_fn),
            name="HealthMonitor", daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self, interval, snapshot_fn):
        while not self._stop_monitor.is_set():
            if snapshot_fn:
                for sid in list(self._records.keys()):
                    try:
                        snap = snapshot_fn(sid)
                        if snap: self.update_snapshot(sid, snap)
                    except Exception: pass
            self._stop_monitor.wait(interval)

    def stats(self) -> dict:
        items = list(self._records.values())
        return {
            "total":    len(items),
            "healthy":  sum(1 for r in items if r.status == HealthStatus.HEALTHY),
            "warning":  sum(1 for r in items if r.status == HealthStatus.WARNING),
            "critical": sum(1 for r in items if r.status == HealthStatus.CRITICAL),
            "retire":   sum(1 for r in items if r.status == HealthStatus.RETIRE),
            "unknown":  sum(1 for r in items if r.status == HealthStatus.UNKNOWN),
            "avg_score": round(
                sum(r.score for r in items)/len(items), 1) if items else 0.0,
        }
