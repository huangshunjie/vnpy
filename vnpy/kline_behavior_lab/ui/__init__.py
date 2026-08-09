"""
kline_behavior_lab/ui/__init__.py

UI模块 - 导出KLineBehaviorLabWidget供VeighNa Apps应用中心发现
"""

from vnpy.kline_behavior_lab.widget import KLineBehaviorLabWidget  # noqa: F401

__all__ = ["KLineBehaviorLabWidget"]