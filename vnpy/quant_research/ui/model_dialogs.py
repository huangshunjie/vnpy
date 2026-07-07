"""
quant_research/ui/model_dialogs.py

ModelCreateDialog      — 注册 / 编辑模型对话框
ModelEvalDialog        — 录入评估指标对话框
ModelTrainingRunDialog — 录入训练历史对话框
ModelDeployDialog      — 部署信息对话框
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout, QDoubleSpinBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt

from ..constant import ModelStatus
from ..model.model_model import MLModelRecord, MODEL_TYPES


class _InlineParamsEditor(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["参数名", "值"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)

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

    def add_row(self):
        r = self.rowCount()
        self.insertRow(r)
        self.setItem(r, 0, QTableWidgetItem(""))
        self.setItem(r, 1, QTableWidgetItem(""))

    def del_row(self):
        rows = {idx.row() for idx in self.selectedIndexes()}
        for r in sorted(rows, reverse=True):
            self.removeRow(r)


class ModelCreateDialog(QDialog):
    """注册 / 编辑模型对话框。"""

    def __init__(self, parent=None, record: Optional[MLModelRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle("编辑模型" if self._editing else "注册模型")
        self.setMinimumWidth(540)
        self._init_ui()
        if self._editing:
            self._load_record()

    def _init_ui(self):
        root = QVBoxLayout(self)
        info_grp = QGroupBox("基本信息")
        form = QFormLayout(info_grp)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("模型名称（必填）")
        form.addRow("名称 *", self._name_edit)
        self._version_edit = QLineEdit("v1.0")
        form.addRow("版本", self._version_edit)
        self._type_combo = QComboBox()
        self._type_combo.addItem("", "")
        for t in MODEL_TYPES:
            self._type_combo.addItem(t, t)
        self._type_combo.setEditable(True)
        form.addRow("模型类型", self._type_combo)
        self._author_edit = QLineEdit()
        form.addRow("作者", self._author_edit)
        self._status_combo = QComboBox()
        for s in ModelStatus:
            self._status_combo.addItem(s.value, s)
        form.addRow("状态", self._status_combo)
        self._framework_edit = QLineEdit()
        self._framework_edit.setPlaceholderText("如 sklearn 1.4 / torch 2.2")
        form.addRow("框架", self._framework_edit)
        self._model_path_edit = QLineEdit()
        form.addRow("模型路径", self._model_path_edit)
        self._config_path_edit = QLineEdit()
        form.addRow("配置路径", self._config_path_edit)
        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setFixedHeight(52)
        form.addRow("描述", self._desc_edit)
        root.addWidget(info_grp)

        hp_grp = QGroupBox("超参数")
        hp_l = QVBoxLayout(hp_grp)
        self._hp_editor = _InlineParamsEditor()
        hp_l.addWidget(self._hp_editor)
        btn_bar = QHBoxLayout()
        add_btn = QPushButton("+ 添加"); del_btn = QPushButton("- 删除")
        add_btn.clicked.connect(self._hp_editor.add_row)
        del_btn.clicked.connect(self._hp_editor.del_row)
        btn_bar.addWidget(add_btn); btn_bar.addWidget(del_btn); btn_bar.addStretch()
        hp_l.addLayout(btn_bar)
        root.addWidget(hp_grp)

        rel_grp = QGroupBox("标签 / 关联资源")
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

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_record(self):
        r = self._record
        self._name_edit.setText(r.name)
        self._version_edit.setText(r.version)
        idx = self._type_combo.findData(r.model_type)
        if idx >= 0: self._type_combo.setCurrentIndex(idx)
        else: self._type_combo.setCurrentText(r.model_type)
        self._author_edit.setText(r.author)
        idx2 = self._status_combo.findData(r.status)
        if idx2 >= 0: self._status_combo.setCurrentIndex(idx2)
        self._framework_edit.setText(r.framework)
        self._model_path_edit.setText(r.model_path)
        self._config_path_edit.setText(r.config_path)
        self._desc_edit.setPlainText(r.description)
        self._hp_editor.set_params(r.hyperparams)
        self._tags_edit.setText(", ".join(r.tags))
        self._features_edit.setText(", ".join(r.feature_ids))
        self._datasets_edit.setText(", ".join(r.dataset_ids))

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus(); return
        self.accept()

    def _split(self, t: str) -> List[str]:
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)        -> str:         return self._name_edit.text().strip()
    def get_version(self)     -> str:         return self._version_edit.text().strip() or "v1.0"
    def get_model_type(self)  -> str:         return self._type_combo.currentText().strip()
    def get_author(self)      -> str:         return self._author_edit.text().strip()
    def get_status(self)      -> ModelStatus: return self._status_combo.currentData()
    def get_framework(self)   -> str:         return self._framework_edit.text().strip()
    def get_model_path(self)  -> str:         return self._model_path_edit.text().strip()
    def get_config_path(self) -> str:         return self._config_path_edit.text().strip()
    def get_description(self) -> str:         return self._desc_edit.toPlainText().strip()
    def get_hyperparams(self) -> Dict:        return self._hp_editor.get_params()
    def get_tags(self)        -> List[str]:   return self._split(self._tags_edit.text())
    def get_feature_ids(self) -> List[str]:   return self._split(self._features_edit.text())
    def get_dataset_ids(self) -> List[str]:   return self._split(self._datasets_edit.text())


class ModelEvalDialog(QDialog):
    """录入评估指标对话框。"""

    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'录入评估指标 — {model_name}')
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        def _spin(lo=0.0, hi=1.0, dec=6):
            s = QDoubleSpinBox()
            s.setRange(lo, hi); s.setDecimals(dec); s.setSingleStep(0.001)
            return s
        self._acc_spin  = _spin()
        self._auc_spin  = _spin()
        self._f1_spin   = _spin()
        self._rmse_spin = _spin(0.0, 1e9, 6); self._rmse_spin.setSingleStep(0.01)
        self._mae_spin  = _spin(0.0, 1e9, 6); self._mae_spin.setSingleStep(0.01)
        form.addRow('Accuracy', self._acc_spin)
        form.addRow('AUC',      self._auc_spin)
        form.addRow('F1',       self._f1_spin)
        form.addRow('RMSE',     self._rmse_spin)
        form.addRow('MAE',      self._mae_spin)
        root.addLayout(form)
        root.addWidget(QLabel('自定义指标（JSON格式，如 {"ic": 0.05}）：'))
        self._custom_edit = QPlainTextEdit()
        self._custom_edit.setPlaceholderText('{}')
        self._custom_edit.setFixedHeight(60)
        root.addWidget(self._custom_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('确认')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_accuracy(self) -> float: return self._acc_spin.value()
    def get_auc(self)      -> float: return self._auc_spin.value()
    def get_f1(self)       -> float: return self._f1_spin.value()
    def get_rmse(self)     -> float: return self._rmse_spin.value()
    def get_mae(self)      -> float: return self._mae_spin.value()

    def get_custom_metrics(self):
        try:
            return json.loads(self._custom_edit.toPlainText() or '{}')
        except Exception:
            return {}


class ModelTrainingRunDialog(QDialog):
    """录入训练历史对话框。"""

    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'录入训练记录 — {model_name}')
        self.setMinimumWidth(440)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._note_edit    = QLineEdit()
        self._note_edit.setPlaceholderText('训练说明')
        self._dataset_edit = QLineEdit()
        self._dataset_edit.setPlaceholderText('数据集 ID（可选）')
        self._author_edit  = QLineEdit()
        self._author_edit.setPlaceholderText('操作人（可选）')
        self._dur_spin     = QDoubleSpinBox()
        self._dur_spin.setRange(0, 86400); self._dur_spin.setDecimals(1)
        self._dur_spin.setSuffix('  秒')
        form.addRow('训练说明',  self._note_edit)
        form.addRow('数据集 ID', self._dataset_edit)
        form.addRow('操作人',    self._author_edit)
        form.addRow('耗时',      self._dur_spin)
        root.addLayout(form)
        root.addWidget(QLabel('超参数（JSON格式）：'))
        self._hp_edit = QPlainTextEdit()
        self._hp_edit.setPlaceholderText('{"n_estimators": 500}')
        self._hp_edit.setFixedHeight(56)
        root.addWidget(self._hp_edit)
        root.addWidget(QLabel('训练指标（JSON格式）：'))
        self._metrics_edit = QPlainTextEdit()
        self._metrics_edit.setPlaceholderText('{"train_auc": 0.92, "val_auc": 0.88}')
        self._metrics_edit.setFixedHeight(56)
        root.addWidget(self._metrics_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('确认')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_note(self)       -> str:   return self._note_edit.text().strip()
    def get_dataset_id(self) -> str:   return self._dataset_edit.text().strip()
    def get_author(self)     -> str:   return self._author_edit.text().strip()
    def get_duration(self)   -> float: return self._dur_spin.value()

    def get_hyperparams(self):
        try: return json.loads(self._hp_edit.toPlainText() or '{}')
        except Exception: return {}

    def get_metrics(self):
        try: return json.loads(self._metrics_edit.toPlainText() or '{}')
        except Exception: return {}


class ModelDeployDialog(QDialog):
    """部署信息对话框。"""

    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'部署模型 — {model_name}')
        self.setMinimumWidth(380)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._env_edit      = QLineEdit()
        self._env_edit.setPlaceholderText('如 prod / staging / sim')
        self._endpoint_edit = QLineEdit()
        self._endpoint_edit.setPlaceholderText('服务地址（可选）')
        form.addRow('部署环境', self._env_edit)
        form.addRow('Endpoint', self._endpoint_edit)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('确认部署')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_env(self)      -> str: return self._env_edit.text().strip()
    def get_endpoint(self) -> str: return self._endpoint_edit.text().strip()
