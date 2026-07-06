"""
system_console/engine/__init__.py

SystemConsoleEngine — 统一管理所有18个模块的生命周期。
"""
from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from ..constant import (
    APP_NAME, MODULE_REGISTRY,
    ModuleState, ConsoleStatus,
)
from ..event import (
    EVENT_CONSOLE_STARTED, EVENT_CONSOLE_STOPPED,
    EVENT_MODULE_STARTING, EVENT_MODULE_STARTED,
    EVENT_MODULE_STOPPING, EVENT_MODULE_STOPPED,
    EVENT_MODULE_ERROR, EVENT_MODULE_STATE_CHANGED,
    EVENT_SYSTEM_STATE_UPDATED, EVENT_ALL_STARTED,
    EVENT_ALL_STOPPED, EVENT_DASHBOARD_TICK, EVENT_CONSOLE_LOG,
)
from ..model.console_model import ModuleEntry, SystemState, ConsoleLog

_PM_SNAPSHOT_EVENT = "ePM_SnapshotUpdated"


class SystemConsoleEngine(BaseEngine):
    """系统主控台引擎（VeighNa BaseEngine）。"""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._started_at: datetime | None = None
        self._logs: list[ConsoleLog] = []
        self._modules: dict[str, ModuleEntry] = {}
        for meta in MODULE_REGISTRY:
            self._modules[meta["key"]] = ModuleEntry(
                key      = meta["key"],
                label    = meta["label"],
                display  = meta["display"],
                app_name = meta["app_name"],
                layer    = meta["layer"],
            )
        self._system_state = SystemState(total_modules=len(MODULE_REGISTRY))
        self._clog(f"[{APP_NAME}] created")

    def init(self) -> None:
        self.event_engine.register(_PM_SNAPSHOT_EVENT, self._on_pm_snapshot)
        self._clog(f"[{APP_NAME}] init()")

    def start(self) -> None:
        self._started_at = datetime.now()
        self.dispatch(EVENT_CONSOLE_STARTED,
                      {"modules": len(self._modules),
                       "status":  ConsoleStatus.IDLE.value})
        self._clog(f"[{APP_NAME}] started")

    def stop(self) -> None:
        try:
            self.event_engine.unregister(_PM_SNAPSHOT_EVENT,
                                          self._on_pm_snapshot)
        except Exception:
            pass
        self.dispatch(EVENT_CONSOLE_STOPPED, {})
        self._clog(f"[{APP_NAME}] stopped")

    def close(self) -> None:
        self.stop()

    # ── module lifecycle ──────────────────────────────────────────────
    def start_module(self, key: str) -> bool:
        entry = self._modules.get(key)
        if entry is None:
            self._clog(f"unknown module: {key}", "ERROR"); return False
        if entry.state == ModuleState.RUNNING:
            return True
        self._set_state(entry, ModuleState.STARTING)
        self.dispatch(EVENT_MODULE_STARTING,
                      {"key": key, "display": entry.display})
        try:
            eng = self.main_engine.get_engine(entry.app_name)
            if eng is None:
                raise RuntimeError(
                    f"Engine '{entry.app_name}' not found")
            if hasattr(eng, "init"):  eng.init()
            if hasattr(eng, "start"): eng.start()
            entry.started_at = datetime.now()
            self._set_state(entry, ModuleState.RUNNING)
            self.dispatch(EVENT_MODULE_STARTED, entry.to_dict())
            self._clog(f"started: {entry.display}")
            return True
        except Exception as e:
            entry.error_msg = str(e)
            self._set_state(entry, ModuleState.ERROR)
            self.dispatch(EVENT_MODULE_ERROR,
                          {"key": key, "display": entry.display,
                           "error": str(e)})
            self._clog(f"error starting {key}: {e}", "ERROR")
            return False

    def stop_module(self, key: str) -> bool:
        entry = self._modules.get(key)
        if entry is None:
            return False
        if entry.state in (ModuleState.STOPPED, ModuleState.UNKNOWN):
            return True
        self._set_state(entry, ModuleState.STOPPING)
        self.dispatch(EVENT_MODULE_STOPPING, {"key": key})
        try:
            eng = self.main_engine.get_engine(entry.app_name)
            if eng is not None:
                if   hasattr(eng, "stop"):  eng.stop()
                elif hasattr(eng, "close"): eng.close()
            entry.stopped_at = datetime.now()
            self._set_state(entry, ModuleState.STOPPED)
            self.dispatch(EVENT_MODULE_STOPPED, entry.to_dict())
            self._clog(f"stopped: {entry.display}")
            return True
        except Exception as e:
            entry.error_msg = str(e)
            self._set_state(entry, ModuleState.ERROR)
            self.dispatch(EVENT_MODULE_ERROR,
                          {"key": key, "display": entry.display,
                           "error": str(e)})
            self._clog(f"error stopping {key}: {e}", "ERROR")
            return False

    def start_all(self) -> dict[str, bool]:
        ordered = sorted(self._modules.keys(),
                         key=lambda k: self._modules[k].layer)
        results = {k: self.start_module(k) for k in ordered}
        if all(results.values()):
            self.dispatch(EVENT_ALL_STARTED, {"count": len(results)})
            self._clog(f"ALL {len(results)} modules started")
        return results

    def stop_all(self) -> dict[str, bool]:
        ordered = sorted(self._modules.keys(),
                         key=lambda k: self._modules[k].layer,
                         reverse=True)
        results = {k: self.stop_module(k) for k in ordered}
        self.dispatch(EVENT_ALL_STOPPED, {"count": len(results)})
        self._clog("ALL modules stopped")
        return results

    def restart_module(self, key: str) -> bool:
        self.stop_module(key)
        return self.start_module(key)

    # ── tick (called by UI timer every 3s) ───────────────────────────
    def tick(self) -> SystemState:
        self._refresh_metrics_from_pm()
        state = self._build_system_state()
        self._system_state = state
        self.dispatch(EVENT_SYSTEM_STATE_UPDATED, state.to_dict())
        self.dispatch(EVENT_DASHBOARD_TICK,        state.to_dict())
        return state

    # ── PM snapshot listener ──────────────────────────────────────────
    def _on_pm_snapshot(self, event: Event) -> None:
        d = event.data or {}
        modules_data = d.get("modules", {})
        if not modules_data:
            return
        for key, m in self._modules.items():
            mod_d = modules_data.get(key, {})
            if not mod_d:
                continue
            m.event_count = int(mod_d.get("event_count", m.event_count))
            m.error_count = int(mod_d.get("error_count", m.error_count))
            m.latency_ms  = float(mod_d.get("avg_latency_1m", m.latency_ms))
            m.throughput  = float(mod_d.get("throughput_1m",  m.throughput))
            m.error_rate  = float(mod_d.get("error_rate_1m",  m.error_rate))
            if (mod_d.get("status") == "active"
                    and m.state not in (ModuleState.RUNNING,
                                        ModuleState.ERROR)):
                self._set_state(m, ModuleState.RUNNING)

    def _refresh_metrics_from_pm(self) -> None:
        try:
            pm = self.main_engine.get_engine("PerformanceMonitor")
            if pm is None:
                return
            all_m = pm.get_all_metrics()
            for key, m in self._modules.items():
                rec = all_m.get(key)
                if rec is None:
                    continue
                m.event_count = rec.event_count
                m.error_count = rec.error_count
                m.latency_ms  = rec.latency_ms
                m.throughput  = rec.throughput
                m.error_rate  = rec.error_rate
        except Exception:
            pass

    # ── state builder ─────────────────────────────────────────────────
    def _build_system_state(self) -> SystemState:
        mods    = list(self._modules.values())
        running = sum(1 for m in mods if m.state == ModuleState.RUNNING)
        stopped = sum(1 for m in mods
                      if m.state in (ModuleState.STOPPED,
                                     ModuleState.UNKNOWN))
        errors  = sum(1 for m in mods if m.state == ModuleState.ERROR)
        def _si(v): return int(v) if isinstance(v, (int, float)) else 0
        def _sf(v): return float(v) if isinstance(v, (int, float)) else 0.0
        total_ev  = sum(_si(m.event_count) for m in mods)
        total_err = sum(_si(m.error_count) for m in mods)
        lats  = [_sf(m.latency_ms) for m in mods
                 if isinstance(m.latency_ms, (int, float)) and m.latency_ms > 0]
        avg_l = round(sum(lats) / len(lats), 2) if lats else 0.0
        tput  = round(sum(_sf(m.throughput) for m in mods), 2)

        score = 100.0
        score -= errors * 15.0
        score -= min((len(mods) - running) * 2.0, 30.0)
        if total_ev > 0:
            er = total_err / total_ev
            score -= 20.0 if er > 0.3 else (8.0 if er > 0.1 else 0.0)
        score = max(score, 0.0)

        if running == len(mods):
            status = ConsoleStatus.RUNNING
        elif running > 0:
            status = ConsoleStatus.PARTIAL
        elif errors > 0:
            status = ConsoleStatus.ERROR
        else:
            status = ConsoleStatus.IDLE

        return SystemState(
            status        = status,
            running_count = running,
            stopped_count = stopped,
            error_count   = errors,
            total_modules = len(mods),
            total_events  = total_ev,
            total_errors  = total_err,
            avg_latency   = avg_l,
            system_tput   = tput,
            health_score  = round(score, 1),
            updated_at    = datetime.now(),
        )

    def _set_state(self, entry: ModuleEntry, state: ModuleState) -> None:
        old = entry.state
        entry.state = state
        if old != state:
            self.dispatch(EVENT_MODULE_STATE_CHANGED, {
                "key": entry.key, "old": old.value, "new": state.value})

    # ── query ─────────────────────────────────────────────────────────
    def get_module(self, key: str) -> ModuleEntry | None:
        return self._modules.get(key)

    def get_all_modules(self) -> dict[str, ModuleEntry]:
        return dict(self._modules)

    def get_system_state(self) -> SystemState:
        return self._system_state

    def get_logs(self, n: int = 200) -> list[ConsoleLog]:
        return self._logs[-n:]

    def get_summary(self) -> dict:
        s = self._system_state
        return {
            "app":           APP_NAME,
            "status":        s.status.value,
            "running":       s.running_count,
            "stopped":       s.stopped_count,
            "errors":        s.error_count,
            "total_modules": s.total_modules,
            "total_events":  s.total_events,
            "health_score":  s.health_score,
            "uptime":        self._uptime(),
        }

    # ── dispatch & log ────────────────────────────────────────────────
    def dispatch(self, event_type: str,
                  data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    def _clog(self, msg: str, level: str = "INFO",
               module: str = "SystemConsole") -> None:
        entry = ConsoleLog(ts=datetime.now(), module=module,
                           level=level, message=msg)
        self._logs.append(entry)
        if len(self._logs) > 2000:
            self._logs = self._logs[-2000:]
        self.dispatch(EVENT_CONSOLE_LOG,
                      {"line": entry.to_line(), "level": level})
        try:
            self.write_log(msg)
        except Exception:
            pass

    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round(
            (datetime.now() - self._started_at).total_seconds(), 1)
