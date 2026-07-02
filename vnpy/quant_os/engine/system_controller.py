"""
quant_os/engine/system_controller.py

SystemController — 全局控制 + Fail-safe 机制（Phase 5 实现）。

职责：
  - start_system / stop_system / pause_system / resume_system
  - 模块异常隔离（单模块故障不影响 OS 主循环）
  - 自动降级（ERROR 模块自动停止，记录并继续运行其他模块）
  - 健康检查（定期扫描模块状态，发现 ERROR 自动处理）
  - 系统级日志（所有控制操作记录到 ControlLog）

❌ 不允许执行交易逻辑
❌ 不允许修改模块内部函数
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable


class ControlAction(str, Enum):
    """控制操作类型。"""
    START_SYSTEM   = "start_system"
    STOP_SYSTEM    = "stop_system"
    PAUSE_SYSTEM   = "pause_system"
    RESUME_SYSTEM  = "resume_system"
    START_MODULE   = "start_module"
    STOP_MODULE    = "stop_module"
    PAUSE_MODULE   = "pause_module"
    RESUME_MODULE  = "resume_module"
    ISOLATE_MODULE = "isolate_module"   # 故障隔离
    DEGRADE_MODULE = "degrade_module"   # 自动降级
    HEALTH_CHECK   = "health_check"


class SystemHealth(str, Enum):
    """系统整体健康状态。"""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"    # 有模块降级，但 OS 仍运行
    CRITICAL  = "critical"    # 多个模块错误
    STOPPED   = "stopped"


@dataclass
class ControlLog:
    """单条控制操作日志。"""
    ts:          datetime     = field(default_factory=datetime.now)
    action:      ControlAction = ControlAction.HEALTH_CHECK
    target:      str          = ""    # 目标模块名（系统操作为 "SYSTEM"）
    detail:      str          = ""
    success:     bool         = True

    def to_line(self) -> str:
        ok  = "OK" if self.success else "FAIL"
        tgt = f"[{self.target}] " if self.target else ""
        return f"[{str(self.ts)[:19]}] {self.action.value}  {tgt}{self.detail}  {ok}"


class SystemController:
    """
    全局系统控制器（Phase 5）。

    使用方式：
        ctrl = SystemController(
            registry      = os_engine.registry,
            event_pub_fn  = os_engine._publish_bus_and_vnpy,
            log_fn        = os_engine._log,
        )
        ctrl.start_system()
        ctrl.stop_module("FactorResearch")
    """

    def __init__(
        self,
        registry,                    # ModuleRegistry 实例
        event_pub_fn: Callable,      # (event_type, data) -> None
        log_fn:       Callable,      # (msg: str) -> None
    ) -> None:
        self._registry    = registry
        self._publish     = event_pub_fn
        self._log         = log_fn

        self._health:     SystemHealth = SystemHealth.STOPPED
        self._control_log: list[ControlLog] = []
        self._max_log     = 1000

        self._lock        = threading.Lock()

        # Fail-safe 配置
        self._max_errors_before_critical: int   = 3
        self._auto_isolate_on_error:      bool  = True

    # ------------------------------------------------------------------ #
    #  系统级控制
    # ------------------------------------------------------------------ #

    def start_system(self) -> bool:
        """启动系统：将所有 INIT / STOPPED 模块设为 RUNNING。"""
        from ..constant import ModuleState
        with self._lock:
            self._health = SystemHealth.HEALTHY
        count = 0
        for m in self._registry.get_all():
            if m.state in (ModuleState.INIT, ModuleState.STOPPED):
                ok = self._registry.start_module(m.name)
                if ok:
                    count += 1
        self._record(ControlAction.START_SYSTEM, "SYSTEM",
                     f"{count} 个模块已启动", True)
        self._log(f"[SystemController] 系统启动，{count} 个模块已设为 RUNNING。")
        self._refresh_health()
        return True

    def stop_system(self) -> bool:
        """停止系统：将所有 RUNNING / PAUSED 模块设为 STOPPED。"""
        from ..constant import ModuleState
        count = 0
        for m in self._registry.get_all():
            if m.state in (ModuleState.RUNNING, ModuleState.PAUSED):
                ok = self._registry.stop_module(m.name)
                if ok:
                    count += 1
        with self._lock:
            self._health = SystemHealth.STOPPED
        self._record(ControlAction.STOP_SYSTEM, "SYSTEM",
                     f"{count} 个模块已停止", True)
        self._log(f"[SystemController] 系统停止，{count} 个模块已设为 STOPPED。")
        return True

    def pause_system(self) -> bool:
        """暂停系统：将所有 RUNNING 模块设为 PAUSED。"""
        from ..constant import ModuleState
        count = 0
        for m in self._registry.get_all():
            if m.state == ModuleState.RUNNING:
                ok = self._registry.pause_module(m.name)
                if ok:
                    count += 1
        with self._lock:
            if self._health == SystemHealth.HEALTHY:
                self._health = SystemHealth.DEGRADED
        self._record(ControlAction.PAUSE_SYSTEM, "SYSTEM",
                     f"{count} 个模块已暂停", True)
        self._log(f"[SystemController] 系统暂停，{count} 个模块已设为 PAUSED。")
        return True

    def resume_system(self) -> bool:
        """恢复系统：将所有 PAUSED 模块设为 RUNNING。"""
        from ..constant import ModuleState
        count = 0
        for m in self._registry.get_all():
            if m.state == ModuleState.PAUSED:
                ok = self._registry.resume_module(m.name)
                if ok:
                    count += 1
        with self._lock:
            self._health = SystemHealth.HEALTHY
        self._record(ControlAction.RESUME_SYSTEM, "SYSTEM",
                     f"{count} 个模块已恢复", True)
        self._log(f"[SystemController] 系统恢复，{count} 个模块已设为 RUNNING。")
        self._refresh_health()
        return True

    # ------------------------------------------------------------------ #
    #  模块级控制
    # ------------------------------------------------------------------ #

    def start_module(self, name: str) -> bool:
        ok = self._registry.start_module(name)
        self._record(ControlAction.START_MODULE, name, "", ok)
        if ok:
            self._log(f"[SystemController] 模块启动：{name}")
            self._refresh_health()
        return ok

    def stop_module(self, name: str) -> bool:
        ok = self._registry.stop_module(name)
        self._record(ControlAction.STOP_MODULE, name, "", ok)
        if ok:
            self._log(f"[SystemController] 模块停止：{name}")
            self._refresh_health()
        return ok

    def pause_module(self, name: str) -> bool:
        ok = self._registry.pause_module(name)
        self._record(ControlAction.PAUSE_MODULE, name, "", ok)
        if ok:
            self._log(f"[SystemController] 模块暂停：{name}")
        return ok

    def resume_module(self, name: str) -> bool:
        ok = self._registry.resume_module(name)
        self._record(ControlAction.RESUME_MODULE, name, "", ok)
        if ok:
            self._log(f"[SystemController] 模块恢复：{name}")
            self._refresh_health()
        return ok

    # ------------------------------------------------------------------ #
    #  Fail-safe 机制
    # ------------------------------------------------------------------ #

    def isolate_module(self, name: str, reason: str = "") -> bool:
        """
        故障隔离：将模块强制标记为 ERROR 并停止。

        其他模块继续运行，OS 进入 DEGRADED 状态。
        """
        from ..constant import ModuleState
        m = self._registry.get(name)
        if m is None:
            return False

        self._registry.mark_error(name, error_msg=reason or "故障隔离")
        self._record(ControlAction.ISOLATE_MODULE, name, reason, True)
        self._log(f"[SystemController][FAIL-SAFE] 模块已隔离：{name}  原因：{reason}")

        with self._lock:
            if self._health == SystemHealth.HEALTHY:
                self._health = SystemHealth.DEGRADED

        self._refresh_health()
        return True

    def handle_module_error(self, name: str, error_msg: str = "") -> None:
        """
        模块异常处理（由外部事件触发）。

        策略：
          1. 记录错误
          2. 若 auto_isolate=True，自动隔离该模块
          3. 统计全局错误数，超过阈值则进入 CRITICAL
          4. 其他模块继续运行（不级联停止）
        """
        self._log(f"[SystemController][ERROR] 模块异常：{name}  {error_msg}")

        if self._auto_isolate_on_error:
            self.isolate_module(name, reason=f"自动隔离: {error_msg}")

        self._record(ControlAction.DEGRADE_MODULE, name, error_msg, True)
        self._refresh_health()

    def health_check(self) -> SystemHealth:
        """执行健康检查，返回当前系统健康状态。"""
        self._refresh_health()
        from ..constant import ModuleState
        modules = self._registry.get_all()
        errors  = [m for m in modules if m.state == ModuleState.ERROR]

        self._record(
            ControlAction.HEALTH_CHECK, "SYSTEM",
            f"total={len(modules)}  errors={len(errors)}  health={self._health.value}",
            True,
        )
        return self._health

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def health(self) -> SystemHealth:
        return self._health

    def get_control_log(self, limit: int = 100) -> list[ControlLog]:
        return self._control_log[-limit:]

    def get_control_log_lines(self, limit: int = 100) -> list[str]:
        return [l.to_line() for l in self._control_log[-limit:]]

    def summary(self) -> dict:
        from ..constant import ModuleState
        modules = self._registry.get_all()
        return {
            "health":   self._health.value,
            "total":    len(modules),
            "running":  sum(1 for m in modules if m.state == ModuleState.RUNNING),
            "paused":   sum(1 for m in modules if m.state == ModuleState.PAUSED),
            "stopped":  sum(1 for m in modules if m.state == ModuleState.STOPPED),
            "error":    sum(1 for m in modules if m.state == ModuleState.ERROR),
            "log_entries": len(self._control_log),
        }

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _refresh_health(self) -> None:
        from ..constant import ModuleState
        modules = self._registry.get_all()
        if not modules:
            with self._lock:
                self._health = SystemHealth.HEALTHY
            return

        error_count = sum(1 for m in modules if m.state == ModuleState.ERROR)
        running_count = sum(1 for m in modules if m.state == ModuleState.RUNNING)

        with self._lock:
            if self._health == SystemHealth.STOPPED:
                return  # 系统已停止，不自动改变
            if error_count >= self._max_errors_before_critical:
                self._health = SystemHealth.CRITICAL
            elif error_count > 0:
                self._health = SystemHealth.DEGRADED
            elif running_count > 0:
                self._health = SystemHealth.HEALTHY

    def _record(
        self,
        action:  ControlAction,
        target:  str,
        detail:  str,
        success: bool,
    ) -> None:
        entry = ControlLog(
            action  = action,
            target  = target,
            detail  = detail,
            success = success,
        )
        self._control_log.append(entry)
        if len(self._control_log) > self._max_log:
            self._control_log.pop(0)
