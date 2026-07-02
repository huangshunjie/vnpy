"""
quant_os/engine/module_registry.py

ModuleRegistry — 模块注册中心（Phase 2 实现）。

职责：
  - 注册 / 注销子模块
  - 维护模块状态机（INIT → RUNNING → PAUSED → STOPPED → ERROR）
  - 发布 EVENT_MODULE_REGISTERED / EVENT_LIFECYCLE_CHANGE 事件
  - 提供查询接口（按名称 / 类型 / 状态）

❌ 不允许调用模块内部逻辑
❌ 不允许跨模块直接调用函数
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import ModuleType, ModuleState
from ..model.module_model import ModuleInfo
from ..event import EVENT_MODULE_REGISTERED, EVENT_LIFECYCLE_CHANGE


# 合法状态转换表
_VALID_TRANSITIONS: dict[ModuleState, set[ModuleState]] = {
    ModuleState.INIT:    {ModuleState.RUNNING, ModuleState.STOPPED, ModuleState.ERROR},
    ModuleState.RUNNING: {ModuleState.PAUSED, ModuleState.STOPPED, ModuleState.ERROR},
    ModuleState.PAUSED:  {ModuleState.RUNNING, ModuleState.STOPPED, ModuleState.ERROR},
    ModuleState.STOPPED: {ModuleState.RUNNING, ModuleState.ERROR},
    ModuleState.ERROR:   {ModuleState.INIT, ModuleState.STOPPED},
}


class ModuleRegistry:
    """
    模块注册中心（Phase 2）。

    使用方式：
        registry = ModuleRegistry(event_put_fn)
        registry.register("FactorResearch", ModuleType.FACTOR)
        registry.set_state("FactorResearch", ModuleState.RUNNING)
    """

    def __init__(self, event_put_fn: Callable) -> None:
        """
        Parameters
        ----------
        event_put_fn : EventEngine.put 的引用，用于发布事件。
        """
        self._modules:  dict[str, ModuleInfo] = {}
        self._put_event = event_put_fn

    # ------------------------------------------------------------------ #
    #  注册 / 注销
    # ------------------------------------------------------------------ #

    def register(
        self,
        name:        str,
        module_type: ModuleType | str,
        *,
        description: str = "",
        version:     str = "1.0",
        tags:        list[str] | None = None,
    ) -> ModuleInfo:
        """
        注册子模块。

        若模块已存在则返回现有 ModuleInfo（不覆盖）。

        Parameters
        ----------
        name        : 模块唯一标识符
        module_type : ModuleType 枚举或字符串
        description : 可选描述
        version     : 版本号
        tags        : 可选标签列表

        Returns
        -------
        ModuleInfo
        """
        if name in self._modules:
            return self._modules[name]

        if isinstance(module_type, str):
            module_type = ModuleType(module_type)

        info = ModuleInfo(
            name        = name,
            module_type = module_type,
            state       = ModuleState.INIT,
            description = description,
            version     = version,
            tags        = tags or [],
        )
        self._modules[name] = info
        self._publish(EVENT_MODULE_REGISTERED, {
            "name":  name,
            "type":  module_type.value,
            "state": ModuleState.INIT.value,
        })
        return info

    def unregister(self, name: str) -> bool:
        """
        注销模块。仅 STOPPED / ERROR 状态可注销。

        Returns
        -------
        bool  True = 成功注销，False = 模块不存在或状态不允许
        """
        info = self._modules.get(name)
        if info is None:
            return False
        if info.state not in (ModuleState.STOPPED, ModuleState.ERROR):
            return False
        del self._modules[name]
        return True

    # ------------------------------------------------------------------ #
    #  状态管理
    # ------------------------------------------------------------------ #

    def set_state(
        self,
        name:      str,
        new_state: ModuleState | str,
        *,
        error_msg: str = "",
    ) -> bool:
        """
        变更模块状态（校验合法转换）。

        Parameters
        ----------
        name      : 模块名称
        new_state : 目标状态
        error_msg : 当 new_state=ERROR 时填写原因

        Returns
        -------
        bool  True = 转换成功，False = 非法转换或模块不存在
        """
        info = self._modules.get(name)
        if info is None:
            return False

        if isinstance(new_state, str):
            new_state = ModuleState(new_state)

        allowed = _VALID_TRANSITIONS.get(info.state, set())
        if new_state not in allowed:
            return False

        old_state    = info.state
        info.state   = new_state

        if new_state == ModuleState.RUNNING and info.started_at is None:
            info.started_at = datetime.now()
        if new_state == ModuleState.STOPPED:
            info.stopped_at = datetime.now()
        if new_state == ModuleState.ERROR and error_msg:
            info.last_error  = error_msg
            info.error_count += 1

        self._publish(EVENT_LIFECYCLE_CHANGE, {
            "name":      name,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "error_msg": error_msg,
        })
        return True

    def start_module(self, name: str) -> bool:
        """将模块状态设为 RUNNING（INIT / STOPPED → RUNNING）。"""
        return self.set_state(name, ModuleState.RUNNING)

    def stop_module(self, name: str) -> bool:
        """将模块状态设为 STOPPED。"""
        return self.set_state(name, ModuleState.STOPPED)

    def pause_module(self, name: str) -> bool:
        """将模块状态设为 PAUSED（RUNNING → PAUSED）。"""
        return self.set_state(name, ModuleState.PAUSED)

    def resume_module(self, name: str) -> bool:
        """将模块状态设为 RUNNING（PAUSED → RUNNING）。"""
        return self.set_state(name, ModuleState.RUNNING)

    def mark_error(self, name: str, error_msg: str = "") -> bool:
        """标记模块为 ERROR 状态。"""
        return self.set_state(name, ModuleState.ERROR, error_msg=error_msg)

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get(self, name: str) -> ModuleInfo | None:
        return self._modules.get(name)

    def get_all(self) -> list[ModuleInfo]:
        return list(self._modules.values())

    def get_by_type(self, module_type: ModuleType | str) -> list[ModuleInfo]:
        if isinstance(module_type, str):
            module_type = ModuleType(module_type)
        return [m for m in self._modules.values() if m.module_type == module_type]

    def get_by_state(self, state: ModuleState | str) -> list[ModuleInfo]:
        if isinstance(state, str):
            state = ModuleState(state)
        return [m for m in self._modules.values() if m.state == state]

    @property
    def count(self) -> int:
        return len(self._modules)

    @property
    def running_count(self) -> int:
        return sum(1 for m in self._modules.values() if m.is_running)

    @property
    def error_count(self) -> int:
        return sum(1 for m in self._modules.values() if m.is_error)

    def summary(self) -> dict:
        return {
            "total":   self.count,
            "running": self.running_count,
            "errors":  self.error_count,
            "modules": [m.to_dict() for m in self.get_all()],
        }

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _publish(self, event_type: str, data: dict) -> None:
        from vnpy.event import Event
        e      = Event(event_type)
        e.data = data
        self._put_event(e)
