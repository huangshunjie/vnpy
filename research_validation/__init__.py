"""
research_validation/__init__.py

Research Validation System — Alpha 真实性过滤器。

导出 App 注册入口供 run.py 使用：
    from vnpy.research_validation import ResearchValidationApp
    main_engine.add_app(ResearchValidationApp)
"""

from .app import ResearchValidationApp

__all__ = ["ResearchValidationApp"]
