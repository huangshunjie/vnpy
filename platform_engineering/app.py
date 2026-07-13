"""
platform_engineering/app.py
VeighNa App 注册入口。
"""
from __future__ import annotations
from pathlib import Path
from typing import Type

from vnpy.trader.app import BaseApp
from vnpy.trader.engine import BaseEngine, MainEngine, EventEngine

from .engine_main import PlatformEngine as _PlatformSubEngine


# ── VeighNa BaseEngine 适配器 ────────────────────────────────────

class PlatformEngineeringEngine(BaseEngine):
    """将 PlatformEngine 注册到 MainEngine。"""

    engine_name: str = "platform_engineering"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, self.engine_name)
        self._pe = _PlatformSubEngine(main_engine, event_engine)

    def start(self)  -> None: self._pe.start()
    def stop(self)   -> None: self._pe.stop()
    def close(self)  -> None: self._pe.close()

    def get_platform_stats(self) -> dict:
        return self._pe.get_platform_stats()

    @property
    def observability(self): return self._pe.observability
    @property
    def tasks(self):         return self._pe.tasks
    @property
    def deployment(self):    return self._pe.deployment
    @property
    def health(self):        return self._pe.health
    @property
    def config(self):        return self._pe.config
    @property
    def api(self):           return self._pe.api
    @property
    def security(self):      return self._pe.security


# ── VeighNa App ───────────────────────────────────────────────────

_app_path = Path(__file__).parent

class PlatformEngineeringApp(BaseApp):
    app_name:     str  = "PlatformEngineering"
    app_module:   str  = "vnpy.platform_engineering"
    app_path:     Path = _app_path
    display_name: str  = "Quant Platform Engineering"
    engine_class: Type = PlatformEngineeringEngine
    widget_name:  str  = "PlatformEngineeringWidget"
    icon_name:    str  = str(_app_path / "ui" / "platform_engineering.ico")
