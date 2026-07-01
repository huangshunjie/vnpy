"""
risk_engine_2/__init__.py

Risk Engine 2.0 — 机构级风控系统。

使用方式（run.py）：
    from vnpy.risk_engine_2 import RiskEngine2App
    main_engine.add_app(RiskEngine2App)
"""

from .app import RiskEngine2App

__all__ = ["RiskEngine2App"]
