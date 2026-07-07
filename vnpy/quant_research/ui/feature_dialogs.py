"""
quant_research/ui/feature_dialogs.py

FeatureCreateDialog  — 注册 / 编辑因子对话框
FeatureICDialog      — 录入 IC 评估结果对话框
FeatureDeprecateDialog — 废弃确认对话框
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton,
    QVBoxLayout, QDoubleSpinBox, QComboBox, QLabel,
)
from PySide6.QtCore import Qt

from ..constant import FeatureStatus
from ..model.feature_model import FeatureRecord

CATEGORIES = [
    "momentum", "reversal", "value", "quality",
    "growth", "technical", "alternative", "macro", "other",
]


class FeatureCreateDialog(QDialog):
    """注册 / 编辑因子对话框。"""

    def __init__(self, parent=None, record: Optional[FeatureRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle("编辑因子" if self._editing else "注册因子")
        self.setMinimumWidth(540)
        self._init_ui()
        if self._editing:
            self._load_record()

    def _init_ui(self):
        root = QVBoxLayout(self)

        # ── 基本信息 ──────────────────────────────────────────────────
        info_grp = QGroupBox("基本信息")
        form = QFormLayout(info_grp)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("因子名称（必填）")
        form.addRow("名称 *", self._name_edit)

        self._version_edit = QLineEdit("v1.0")
        form.addRow("版本", self._version_edit)

        self._category_combo = QComboBox()
        self._category_combo.addItem("", "")
        for c in CATEGORIES:
            self._category_combo.addItem(c, c)
        self._category_combo.setEditable(True)
        form.addRow("分类", self._category_combo)

        self._author_edit = QLineEdit()
        self._author_edit.setPlaceholderText("作者 / 团队")
        form.addRow("作者", self._author_edit)

        self._status_combo = QComboBox()
        for s in FeatureStatus:
            self._status_combo.addItem(s.value, s)
        form.addRow("状态", self._status_combo)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("因子描述")
        self._desc_edit.setFixedHeight(60)
        form.addRow("描述", self._desc_edit)

        root.addWidget(info_grp)

        # ── 公式 ──────────────────────────────────────────────────────
        formula_grp = QGroupBox("计算公式 / 代码描述")
        fl = QVBoxLayout(formula_grp)
        self._formula_edit = QPlainTextEdit()
        self._formula_edit.setPlaceholderText(
            "例：(close - close.shift(20)) / close.shift(20)")
        self._formula_edit.setFixedHeight(80)
        fl.addWidget(self._formula_edit)
        root.addWidget(formula_grp)

        # ── 标签 / 数据集 / 依赖 ──────────────────────────────────────
        ext_grp = QGroupBox("标签 / 数据集 / 上游因子")
        ef = QFormLayout(ext_grp)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("逗号分隔，如 equity,daily,momentum")
        ef.addRow("标签", self._tags_edit)

        self._datasets_edit = QLineEdit()
        self._datasets_edit.setPlaceholderText("数据集 ID，逗号分隔")
        ef.addRow("依赖数据集", self._datasets_edit)

        self._deps_edit = QLineEdit()
        self._deps_edit.setPlaceholderText("上游因子 ID，逗号分隔")
        ef.addRow("依赖因子", self._deps_edit)

        root.addWidget(ext_grp)

        # ── 按钮 ──────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_record(self):
        r = self._record
        self._name_edit.setText(r.name)
        self._version_edit.setText(r.version)
        idx = self._category_combo.findData(r.category)
        if idx >= 0:
            self._category_combo.setCurrentIndex(idx)
        else:
            self._category_combo.setCurrentText(r.category)
        self._author_edit.setText(r.author)
        idx2 = self._status_combo.findData(r.status)
        if idx2 >= 0:
            self._status_combo.setCurrentIndex(idx2)
        self._desc_edit.setPlainText(r.description)
        self._formula_edit.setPlainText(r.formula)
        self._tags_edit.setText(", ".join(r.tags))
        self._datasets_edit.setText(", ".join(r.dataset_ids))
        self._deps_edit.setText(", ".join(r.dependencies))

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def _split(self, text: str) -> List[str]:
        return [x.strip() for x in text.split(",") if x.strip()]

    def get_name(self)        -> str:           return self._name_edit.text().strip()
    def get_version(self)     -> str:           return self._version_edit.text().strip() or "v1.0"
    def get_category(self)    -> str:           return self._category_combo.currentText().strip()
    def get_author(self)      -> str:           return self._author_edit.text().strip()
    def get_status(self)      -> FeatureStatus: return self._status_combo.currentData()
    def get_description(self) -> str:           return self._desc_edit.toPlainText().strip()
    def get_formula(self)     -> str:           return self._formula_edit.toPlainText().strip()
    def get_tags(self)        -> List[str]:     return self._split(self._tags_edit.text())
    def get_dataset_ids(self) -> List[str]:     return self._split(self._datasets_edit.text())
    def get_dependencies(self) -> List[str]:    return self._split(self._deps_edit.text())


class FeatureICDialog(QDialog):
    """录入 IC 评估结果对话框。"""

    def __init__(self, feature_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"录入 IC 指标 — {feature_name}")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()

        def _spin(lo=-1.0, hi=1.0, decimals=6, step=0.001):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setDecimals(decimals)
            s.setSingleStep(step)
            return s

        self._ic_spin     = _spin()
        self._rankic_spin = _spin()
        self._ir_spin     = _spin(-10.0, 10.0, 4, 0.01)
        self._icir_spin   = _spin(-10.0, 10.0, 4, 0.01)
        self._cov_spin    = _spin(0.0, 1.0, 4, 0.01)

        self._period_edit  = QLineEdit()
        self._period_edit.setPlaceholderText("如 2024Q1 或 2024-01")
        self._dataset_edit = QLineEdit()
        self._dataset_edit.setPlaceholderText("评估用数据集 ID（可选）")

        form.addRow("IC",         self._ic_spin)
        form.addRow("Rank IC",    self._rankic_spin)
        form.addRow("IR",         self._ir_spin)
        form.addRow("ICIR",       self._icir_spin)
        form.addRow("Coverage",   self._cov_spin)
        form.addRow("评估周期",    self._period_edit)
        form.addRow("数据集 ID",   self._dataset_edit)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_ic(self)         -> float: return self._ic_spin.value()
    def get_rank_ic(self)    -> float: return self._rankic_spin.value()
    def get_ir(self)         -> float: return self._ir_spin.value()
    def get_icir(self)       -> float: return self._icir_spin.value()
    def get_coverage(self)   -> float: return self._cov_spin.value()
    def get_period(self)     -> str:   return self._period_edit.text().strip()
    def get_dataset_id(self) -> str:   return self._dataset_edit.text().strip()


class FeatureDeprecateDialog(QDialog):
    """废弃因子确认对话框。"""

    def __init__(self, feature_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"废弃因子 — {feature_name}")
        self.setMinimumWidth(380)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(QLabel("请输入废弃原因（可选）："))
        self._reason_edit = QPlainTextEdit()
        self._reason_edit.setPlaceholderText(
            "例：IC 长期低于 0.02，已被更强因子替代")
        self._reason_edit.setFixedHeight(80)
        root.addWidget(self._reason_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认废弃")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_reason(self) -> str:
        return self._reason_edit.toPlainText().strip()
