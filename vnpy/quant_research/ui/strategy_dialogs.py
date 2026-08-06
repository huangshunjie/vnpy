"""
quant_research/ui/strategy_dialogs.py

StrategyCreateDialog       — 注册 / 编辑策略对话框
StrategyPerformanceDialog  — 录入绩效指标对话框
StrategyVersionDialog      — 新增版本快照对话框
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout, QDoubleSpinBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt

from ..constant import StrategyStatus
from ..model.strategy_model import StrategyRecord, STRATEGY_TYPES


class _ParamsEditor(QWidget if False else object):
    pass


# ─── reuse simple inline key-value params editor ──────────────────────
from PySide6.QtWidgets import QAbstractItemView
import json


class _InlineParamsEditor(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["参数名", "值"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setMinimumHeight(100)
        self.setMaximumHeight(160)

    def set_params(self, params: Dict[str, Any]):
        self.setRowCount(0)
        for k, v in params.items():
            r = self.rowCount()
            self.insertRow(r)
            self.setItem(r, 0, QTableWidgetItem(str(k)))
            self.setItem(r, 1, QTableWidgetItem(str(v)))

    def get_params(self) -> Dict[str, Any]:
        result = {}
        for r in range(self.rowCount()):
            k = self.item(r, 0)
            v = self.item(r, 1)
            if k and k.text().strip():
                raw = v.text().strip() if v else ""
                try:
                    result[k.text().strip()] = json.loads(raw)
                except Exception:
                    result[k.text().strip()] = raw
        return result


# ─────────────────────────────────────────────────────────────────────
# StrategyCreateDialog
# ─────────────────────────────────────────────────────────────────────

class StrategyCreateDialog(QDialog):
    """注册 / 编辑策略对话框。"""

    def __init__(self, parent=None, record: Optional[StrategyRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle("编辑策略" if self._editing else "注册策略")
        self.setMinimumWidth(560)
        self._init_ui()
        if self._editing:
            self._load_record()

    def _init_ui(self):
        root = QVBoxLayout(self)

        # ── 基本信息 ──────────────────────────────────────────────────
        info_grp = QGroupBox("基本信息")
        form = QFormLayout(info_grp)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("策略名称（必填）")
        form.addRow("名称 *", self._name_edit)

        self._version_edit = QLineEdit("v1.0")
        form.addRow("版本", self._version_edit)

        self._type_combo = QComboBox()
        self._type_combo.addItem("", "")
        for t in STRATEGY_TYPES:
            self._type_combo.addItem(t, t)
        self._type_combo.setEditable(True)
        form.addRow("类型", self._type_combo)

        self._author_edit = QLineEdit()
        self._author_edit.setPlaceholderText("作者 / 团队")
        form.addRow("作者", self._author_edit)

        self._status_combo = QComboBox()
        for s in StrategyStatus:
            self._status_combo.addItem(s.value, s)
        form.addRow("状态", self._status_combo)

        self._universe_edit = QLineEdit()
        self._universe_edit.setPlaceholderText("如 HS300 / 全A / 期货主力")
        form.addRow("交易标的", self._universe_edit)

        self._code_path_edit = QLineEdit()
        self._code_path_edit.setPlaceholderText("策略代码路径（可选）")
        form.addRow("代码路径", self._code_path_edit)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("策略描述")
        self._desc_edit.setFixedHeight(60)
        form.addRow("描述", self._desc_edit)

        root.addWidget(info_grp)

        # ── 参数 ──────────────────────────────────────────────────────
        param_grp = QGroupBox("策略参数")
        pl = QVBoxLayout(param_grp)
        self._params_editor = _InlineParamsEditor()
        pl.addWidget(self._params_editor)
        btn_bar = QHBoxLayout()
        add_btn = QPushButton("+ 添加行")
        del_btn = QPushButton("- 删除行")
        add_btn.clicked.connect(self._add_param_row)
        del_btn.clicked.connect(self._del_param_row)
        btn_bar.addWidget(add_btn)
        btn_bar.addWidget(del_btn)
        btn_bar.addStretch()
        pl.addLayout(btn_bar)
        root.addWidget(param_grp)

        # ── 关联 ──────────────────────────────────────────────────────
        rel_grp = QGroupBox("标签 / 关联因子 / 数据集")
        rf = QFormLayout(rel_grp)
        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("逗号分隔标签")
        rf.addRow("标签", self._tags_edit)
        self._features_edit = QLineEdit()
        self._features_edit.setPlaceholderText("因子 ID，逗号分隔")
        rf.addRow("依赖因子", self._features_edit)
        self._datasets_edit = QLineEdit()
        self._datasets_edit.setPlaceholderText("数据集 ID，逗号分隔")
        rf.addRow("依赖数据集", self._datasets_edit)
        root.addWidget(rel_grp)

        # ── 按钮 ──────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _add_param_row(self):
        r = self._params_editor.rowCount()
        self._params_editor.insertRow(r)
        self._params_editor.setItem(r, 0, QTableWidgetItem(""))
        self._params_editor.setItem(r, 1, QTableWidgetItem(""))

    def _del_param_row(self):
        rows = {idx.row() for idx in self._params_editor.selectedIndexes()}
        for r in sorted(rows, reverse=True):
            self._params_editor.removeRow(r)

    def _load_record(self):
        r = self._record
        self._name_edit.setText(r.name)
        self._version_edit.setText(r.version)
        idx = self._type_combo.findData(r.strategy_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        else:
            self._type_combo.setCurrentText(r.strategy_type)
        self._author_edit.setText(r.author)
        idx2 = self._status_combo.findData(r.status)
        if idx2 >= 0:
            self._status_combo.setCurrentIndex(idx2)
        self._universe_edit.setText(r.universe)
        self._code_path_edit.setText(r.code_path)
        self._desc_edit.setPlainText(r.description)
        self._params_editor.set_params(r.params)
        self._tags_edit.setText(", ".join(r.tags))
        self._features_edit.setText(", ".join(r.feature_ids))
        self._datasets_edit.setText(", ".join(r.dataset_ids))

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def _split(self, text: str) -> List[str]:
        return [x.strip() for x in text.split(",") if x.strip()]

    def get_name(self)          -> str:            return self._name_edit.text().strip()
    def get_version(self)       -> str:            return self._version_edit.text().strip() or "v1.0"
    def get_strategy_type(self) -> str:            return self._type_combo.currentText().strip()
    def get_author(self)        -> str:            return self._author_edit.text().strip()
    def get_status(self)        -> StrategyStatus: return self._status_combo.currentData()
    def get_universe(self)      -> str:            return self._universe_edit.text().strip()
    def get_code_path(self)     -> str:            return self._code_path_edit.text().strip()
    def get_description(self)   -> str:            return self._desc_edit.toPlainText().strip()
    def get_params(self)        -> Dict:           return self._params_editor.get_params()
    def get_tags(self)          -> List[str]:      return self._split(self._tags_edit.text())
    def get_feature_ids(self)   -> List[str]:      return self._split(self._features_edit.text())
    def get_dataset_ids(self)   -> List[str]:      return self._split(self._datasets_edit.text())


# ─────────────────────────────────────────────────────────────────────
# StrategyPerformanceDialog
# ─────────────────────────────────────────────────────────────────────

class StrategyPerformanceDialog(QDialog):
    """录入策略绩效指标。"""

    def __init__(self, strategy_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"录入绩效 — {strategy_name}")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()

        def _pct(lo=-1.0, hi=10.0):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setDecimals(4)
            s.setSingleStep(0.01)
            s.setSuffix("  (小数，如 0.25 = 25%)")
            return s

        def _ratio(lo=-20.0, hi=20.0):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setDecimals(4)
            s.setSingleStep(0.01)
            return s

        self._annual_spin   = _pct()
        self._dd_spin       = _pct(0.0, 1.0)
        self._dd_spin.setValue(0.0)
        self._sharpe_spin   = _ratio()
        self._sortino_spin  = _ratio()
        self._calmar_spin   = _ratio()
        self._winrate_spin  = _pct(0.0, 1.0)
        self._turnover_spin = _ratio(0.0, 100.0)
        self._pf_spin       = _ratio(0.0, 20.0)
        form.addRow("年化收益",  self._annual_spin)
        form.addRow("最大回撤",  self._dd_spin)
        form.addRow("Sharpe",    self._sharpe_spin)
        form.addRow("Sortino",   self._sortino_spin)
        form.addRow("Calmar",    self._calmar_spin)
        form.addRow("胜率",      self._winrate_spin)
        form.addRow("换手率",    self._turnover_spin)
        form.addRow("盈亏比",    self._pf_spin)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_annual_return(self)  -> float: return self._annual_spin.value()
    def get_max_drawdown(self)   -> float: return self._dd_spin.value()
    def get_sharpe(self)         -> float: return self._sharpe_spin.value()
    def get_sortino(self)        -> float: return self._sortino_spin.value()
    def get_calmar(self)         -> float: return self._calmar_spin.value()
    def get_win_rate(self)       -> float: return self._winrate_spin.value()
    def get_turnover(self)       -> float: return self._turnover_spin.value()
    def get_profit_factor(self)  -> float: return self._pf_spin.value()


# ─────────────────────────────────────────────────────────────────────
# StrategyVersionDialog
# ─────────────────────────────────────────────────────────────────────

class StrategyVersionDialog(QDialog):
    """新增策略版本快照。"""

    def __init__(self, strategy_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"新增版本快照 — {strategy_name}")
        self.setMinimumWidth(380)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(QLabel("版本变更说明："))
        self._note_edit = QPlainTextEdit()
        self._note_edit.setPlaceholderText("例：修复了换手率计算逻辑，优化了持仓权重")
        self._note_edit.setFixedHeight(80)
        root.addWidget(self._note_edit)
        self._author_edit = QLineEdit()
        self._author_edit.setPlaceholderText("操作人（可选）")
        root.addWidget(self._author_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认快照")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_note(self)   -> str: return self._note_edit.toPlainText().strip()
    def get_author(self) -> str: return self._author_edit.text().strip()
