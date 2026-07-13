"""ui sub-package: VeighNa GUI widgets for BatchResearch."""

from .widget import BatchResearchWidget
from .setting_dialog import SettingDialog
from .result_table import ResultTableWidget
from .factor_dialog import FactorAnalysisDialog
from .stock_pool_dialog import StockPoolDialog
from .stock_pool_editor import StockPoolEditor

__all__ = [
    "BatchResearchWidget",
    "SettingDialog",
    "ResultTableWidget",
    "FactorAnalysisDialog",
    "StockPoolDialog",
    "StockPoolEditor",
]
