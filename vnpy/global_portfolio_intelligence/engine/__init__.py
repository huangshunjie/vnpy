"""
global_portfolio_intelligence/engine/__init__.py

从顶层 engine.py 重新导出 GlobalPortfolioEngine，
保证 `from .engine import GlobalPortfolioEngine` 可用。
"""
from .global_engine import GlobalPortfolioEngine

__all__ = ["GlobalPortfolioEngine"]
