"""write_pe_health_engine.py — append HealthEngine main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\engine\health_engine.py"
)

ENGINE = '''

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
'''

ast.parse(ENGINE)
with open(P, "a", encoding="utf-8") as f:
    f.write(ENGINE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("HealthEngine OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
