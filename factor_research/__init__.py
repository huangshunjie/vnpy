"""
factor_research/__init__.py

Factor Research（因子研究工作台）包入口。

对外只暴露 FactorResearchApp，其余模块由内部按需导入。
"""

from .app import FactorResearchApp

__all__ = ["FactorResearchApp"]
