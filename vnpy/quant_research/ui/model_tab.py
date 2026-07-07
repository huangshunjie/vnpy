"""
quant_research/ui/model_tab.py

ModelTab — Phase 6 完整实现。
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..constant import ModelStatus
from ..event import (
    EVENT_MODEL_CREATED,
    EVENT_MODEL_UPDATED,
    EVENT_MODEL_DELETED,
)
from ..model.model_model import MLModelRecord, TrainingRun, MODEL_TYPES
from .model_dialogs import (
    ModelCreateDialog,
    ModelEvalDialog,
    ModelTrainingRunDialog,
    ModelDeployDialog,
)

STATUS_COLORS = {
    ModelStatus.TRAINING:  QColor("#0d6efd"),
    ModelStatus.EVALUATED: QColor("#fd7e14"),
    ModelStatus.DEPLOYED:  QColor("#198754"),
    ModelStatus.RETIRED:   QColor("#adb5bd"),
}

COL_ID      = 0
COL_NAME    = 1
COL_VERSION = 2
COL_TYPE    = 3
COL_STATUS  = 4
COL_ACC     = 5
COL_AUC     = 6
COL_F1      = 7
COL_AUTHOR  = 8
COL_TIME    = 9

HEADERS = ["模型 ID", "名称", "版本", "类型", "状态",
           "Accuracy", "AUC", "F1", "作者", "更新时间"]


def _metric_card(title: str) -> QWidget:
    from PySide6.QtWidgets import QVBoxLayout
    card = QWidget()
    card.setStyleSheet("background:#f8f9fa; border-radius:6px;")
    lyt = QVBoxLayout(card)
    lyt.setContentsMargins(8, 4, 8, 4)
    t = QLabel(title)
    t.setAlignment(Qt.AlignCenter)
    t.setStyleSheet("color:#666; font-size:11px;")
    v = QLabel("—")
    v.setAlignment(Qt.AlignCenter)
    v.setStyleSheet("font-size:16px; font-weight:bold;")
    v.setObjectName("val")
    lyt.addWidget(t)
    lyt.addWidget(v)
    return card


def _set_card(card: QWidget, value: float, fmt: str = ".4f",
              positive_good: bool = True):
    lbl = card.findChild(QLabel, "val")
    if not lbl:
        return
    lbl.setText(f"{value:{fmt}}")
    if positive_good:
        color = "#198754" if value > 0 else "#dc3545" if value < 0 else "#333"
    else:
        color = "#dc3545" if value > 0 else "#333"
    lbl.setStyleSheet(f"font-size:16px; font-weight:bold; color:{color};")


class ModelDetailPanel(QTabWidget):
    """底部详情：概览 / 评估指标 / 训练历史 / 超参数 / 关联资源。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current: Optional[MLModelRecord] = None
        self._init_ui()

    def _init_ui(self):
        # ── 概览 ──────────────────────────────────────────────────────
        ov_w = QWidget()
        ov_l = QVBoxLayout(ov_w)
        self._overview_table = QTableWidget(0, 2)
        self._overview_table.setHorizontalHeaderLabels(["属性", "值"])
        self._overview_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._overview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._overview_table.setAlternatingRowColors(True)
        ov_l.addWidget(self._overview_table)
        self.addTab(ov_w, "概览")

        # ── 评估指标 ──────────────────────────────────────────────────
        eval_w = QWidget()
        eval_l = QVBoxLayout(eval_w)
        row1 = QHBoxLayout()
        self._c_acc   = _metric_card("Accuracy")
        self._c_auc   = _metric_card("AUC")
        self._c_f1    = _metric_card("F1")
        self._c_rmse  = _metric_card("RMSE")
        self._c_mae   = _metric_card("MAE")
        for c in (self._c_acc, self._c_auc, self._c_f1,
                  self._c_rmse, self._c_mae):
            row1.addWidget(c)
        eval_l.addLayout(row1)

        self._custom_table = QTableWidget(0, 2)
        self._custom_table.setHorizontalHeaderLabels(["自定义指标", "值"])
        self._custom_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._custom_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._custom_table.setAlternatingRowColors(True)
        eval_l.addWidget(QLabel("自定义指标："))
        eval_l.addWidget(self._custom_table)
        self.addTab(eval_w, "评估指标")

        # ── 训练历史 ──────────────────────────────────────────────────
        run_w = QWidget()
        run_l = QVBoxLayout(run_w)
        self._run_table = QTableWidget(0, 6)
        self._run_table.setHorizontalHeaderLabels(
            ["Run ID", "说明", "数据集", "耗时(s)", "指标摘要", "时间"])
        self._run_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._run_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._run_table.setAlternatingRowColors(True)
        run_l.addWidget(self._run_table)
        self.addTab(run_w, "训练历史")

        # ── 超参数 ──────────────────────────────────────────────────────
        hp_w = QWidget()
        hp_l = QVBoxLayout(hp_w)
        self._hp_table = QTableWidget(0, 2)
        self._hp_table.setHorizontalHeaderLabels(["参数名", "值"])
        self._hp_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._hp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._hp_table.setAlternatingRowColors(True)
        hp_l.addWidget(self._hp_table)
        self.addTab(hp_w, "超参数")

        # ── 关联资源 ──────────────────────────────────────────────────
        rel_w = QWidget()
        rel_l = QVBoxLayout(rel_w)
        self._rel_edit = QTextEdit()
        self._rel_edit.setReadOnly(True)
        self._rel_edit.setFont(QFont("Consolas", 10))
        rel_l.addWidget(self._rel_edit)
        self.addTab(rel_w, "关联资源")

    def load(self, record: MLModelRecord):
        self._current = record
        self._load_overview(record)
        self._load_eval(record)
        self._load_runs(record)
        self._load_hp(record)
        self._load_relations(record)

    def _load_overview(self, r: MLModelRecord):
        self._overview_table.setRowCount(0)
        rows = [
            ("ID",       r.model_id),
            ("名称",     r.name),
            ("版本",     r.version),
            ("状态",     r.status.value),
            ("类型",     r.model_type),
            ("作者",     r.author),
            ("框架",     r.framework),
            ("模型路径", r.model_path),
            ("配置路径", r.config_path),
            ("标签",     ", ".join(r.tags)),
            ("创建时间", r.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间", r.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        if r.deploy_at:
            rows.append(("部署时间", r.deploy_at.strftime("%Y-%m-%d %H:%M")))
            rows.append(("部署环境", r.deploy_env))
            rows.append(("Endpoint", r.endpoint))
        rows.append(("描述", r.description))
        for k, v in rows:
            row = self._overview_table.rowCount()
            self._overview_table.insertRow(row)
            self._overview_table.setItem(row, 0, QTableWidgetItem(k))
            self._overview_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _load_eval(self, r: MLModelRecord):
        _set_card(self._c_acc,  r.accuracy, ".4f", True)
        _set_card(self._c_auc,  r.auc,      ".4f", True)
        _set_card(self._c_f1,   r.f1,       ".4f", True)
        _set_card(self._c_rmse, r.rmse,     ".4f", False)
        _set_card(self._c_mae,  r.mae,      ".4f", False)
        self._custom_table.setRowCount(0)
        for k, v in r.custom_metrics.items():
            row = self._custom_table.rowCount()
            self._custom_table.insertRow(row)
            self._custom_table.setItem(row, 0, QTableWidgetItem(k))
            self._custom_table.setItem(row, 1, QTableWidgetItem(f"{v:.6f}"))

    def _load_runs(self, r: MLModelRecord):
        self._run_table.setRowCount(0)
        for run in reversed(r.training_runs):
            row = self._run_table.rowCount()
            self._run_table.insertRow(row)
            metrics_str = ", ".join(
                f"{k}={v:.4f}" for k, v in list(run.metrics.items())[:3])
            vals = [run.run_id, run.run_note, run.dataset_id,
                    f"{run.duration_sec:.1f}", metrics_str,
                    run.started_at.strftime("%Y-%m-%d %H:%M")]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                self._run_table.setItem(row, col, item)

    def _load_hp(self, r: MLModelRecord):
        self._hp_table.setRowCount(0)
        for k, v in r.hyperparams.items():
            row = self._hp_table.rowCount()
            self._hp_table.insertRow(row)
            self._hp_table.setItem(row, 0, QTableWidgetItem(str(k)))
            self._hp_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _load_relations(self, r: MLModelRecord):
        lines = []
        for label, ids, getter in [
            ("■ 依赖因子",    r.feature_ids,    self._engine.get_feature),
            ("■ 依赖数据集",  r.dataset_ids,    self._engine.get_dataset),
            ("■ 关联策略",    r.strategy_ids,   self._engine.get_strategy),
            ("■ 关联实验",    r.experiment_ids, self._engine.get_experiment),
        ]:
            if ids:
                lines.append(f"{label}：")
                for rid in ids:
                    obj = getter(rid)
                    name = obj.name if obj else rid
                    lines.append(f"  ├─ {rid}  {name}")
            else:
                lines.append(f"{label}：无")
            lines.append("")
        self._rel_edit.setPlainText("\n".join(lines))

    def clear(self):
        self._current = None
        self._overview_table.setRowCount(0)
        self._custom_table.setRowCount(0)
        self._run_table.setRowCount(0)
        self._hp_table.setRowCount(0)
        self._rel_edit.clear()


class ModelTab(QWidget):
    """模型注册中心主 Tab。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[MLModelRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        bar1 = QHBoxLayout()
        self._btn_new    = QPushButton('+ 注册模型')
        self._btn_edit   = QPushButton('编辑')
        self._btn_delete = QPushButton('删除')
        self._btn_eval   = QPushButton('录入评估')
        self._btn_run    = QPushButton('录入训练')
        self._btn_deploy = QPushButton('部署')
        self._btn_eval_s = QPushButton('标记已评估')
        self._btn_retire = QPushButton('退役')
        for btn in (self._btn_new, self._btn_edit, self._btn_delete,
                    self._btn_eval, self._btn_run, self._btn_deploy,
                    self._btn_eval_s, self._btn_retire):
            bar1.addWidget(btn)
        bar1.addStretch()
        root.addLayout(bar1)
        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel('状态:'))
        self._status_filter = QComboBox()
        self._status_filter.addItem('全部', None)
        for s in ModelStatus:
            self._status_filter.addItem(s.value, s)
        self._status_filter.setFixedWidth(120)
        bar2.addWidget(self._status_filter)
        bar2.addWidget(QLabel('类型:'))
        self._type_filter = QComboBox()
        self._type_filter.addItem('全部', None)
        for t in MODEL_TYPES:
            self._type_filter.addItem(t, t)
        self._type_filter.setFixedWidth(120)
        bar2.addWidget(self._type_filter)
        bar2.addWidget(QLabel('搜索:'))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('名称 / 类型 / 作者 / 框架')
        self._search_box.setFixedWidth(180)
        bar2.addWidget(self._search_box)
        self._btn_search = QPushButton('搜索'); self._btn_search.setFixedWidth(52)
        bar2.addWidget(self._btn_search)
        self._btn_reset = QPushButton('重置'); self._btn_reset.setFixedWidth(52)
        bar2.addWidget(self._btn_reset)
        bar2.addStretch()
        root.addLayout(bar2)
        splitter = QSplitter(Qt.Vertical)
        self._table = QTableWidget(0, len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(COL_ID, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        splitter.addWidget(self._table)
        self._detail = ModelDetailPanel(self._engine)
        self._detail.setMinimumHeight(240)
        splitter.addWidget(self._detail)
        splitter.setSizes([360, 280])
        root.addWidget(splitter)
        self._status_bar = QLabel('共 0 条模型')
        root.addWidget(self._status_bar)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_eval.clicked.connect(self._on_eval)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_deploy.clicked.connect(self._on_deploy)
        self._btn_eval_s.clicked.connect(self._on_set_evaluated)
        self._btn_retire.clicked.connect(self._on_retire)
        self._btn_search.clicked.connect(self._apply_filter)
        self._btn_reset.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        self._type_filter.currentIndexChanged.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)

    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_MODEL_CREATED, self._on_event)
        ee.register(EVENT_MODEL_UPDATED, self._on_event)
        ee.register(EVENT_MODEL_DELETED, self._on_event)

    def _on_event(self, event: Event):
        self._refresh()

    def _refresh(self):
        self._all_records = self._engine.list_models()
        self._apply_filter()

    def _apply_filter(self):
        status  = self._status_filter.currentData()
        mtype   = self._type_filter.currentData()
        keyword = self._search_box.text().strip()
        if keyword:
            records = self._engine.search_models(keyword)
        else:
            records = self._engine.list_models(status=status, model_type=mtype)
        self._populate_table(records)

    def _reset_filter(self):
        self._status_filter.setCurrentIndex(0)
        self._type_filter.setCurrentIndex(0)
        self._search_box.clear()
        self._populate_table(self._all_records)

    def _populate_table(self, records):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f'共 {len(records)} 条模型')

    def _set_row(self, row: int, rec: MLModelRecord):
        id_item = QTableWidgetItem(rec.model_id)
        id_item.setData(Qt.UserRole, rec.model_id)
        self._table.setItem(row, COL_ID, id_item)
        name_item = QTableWidgetItem(rec.name)
        if rec.status == ModelStatus.RETIRED:
            f = QFont(); f.setStrikeOut(True); name_item.setFont(f)
            name_item.setForeground(QColor('#adb5bd'))
        self._table.setItem(row, COL_NAME, name_item)
        self._table.setItem(row, COL_VERSION, QTableWidgetItem(rec.version))
        self._table.setItem(row, COL_TYPE,    QTableWidgetItem(rec.model_type))
        st_item = QTableWidgetItem(rec.status.value)
        st_item.setForeground(STATUS_COLORS.get(rec.status, QColor('#333')))
        f2 = QFont(); f2.setBold(True); st_item.setFont(f2)
        self._table.setItem(row, COL_STATUS, st_item)
        def _num(v, fmt='.4f'):
            item = QTableWidgetItem(f'{v:{fmt}}')
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item.setForeground(QColor('#198754' if v > 0 else '#333'))
            return item
        self._table.setItem(row, COL_ACC,    _num(rec.accuracy))
        self._table.setItem(row, COL_AUC,    _num(rec.auc))
        self._table.setItem(row, COL_F1,     _num(rec.f1))
        self._table.setItem(row, COL_AUTHOR, QTableWidgetItem(rec.author))
        self._table.setItem(row, COL_TIME,
            QTableWidgetItem(rec.updated_at.strftime('%Y-%m-%d %H:%M')))

    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec: self._detail.load(rec)
        else:   self._detail.clear()

    def _on_new(self):
        dlg = ModelCreateDialog(parent=self)
        if dlg.exec() == ModelCreateDialog.Accepted:
            self._engine.register_model(
                name=dlg.get_name(), version=dlg.get_version(),
                description=dlg.get_description(),
                model_type=dlg.get_model_type(),
                author=dlg.get_author(), framework=dlg.get_framework(),
                model_path=dlg.get_model_path(),
                config_path=dlg.get_config_path(),
                hyperparams=dlg.get_hyperparams(),
                tags=dlg.get_tags(), feature_ids=dlg.get_feature_ids(),
                dataset_ids=dlg.get_dataset_ids(),
            )

    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = ModelCreateDialog(parent=self, record=rec)
        if dlg.exec() == ModelCreateDialog.Accepted:
            rec.name        = dlg.get_name()
            rec.version     = dlg.get_version()
            rec.description = dlg.get_description()
            rec.model_type  = dlg.get_model_type()
            rec.author      = dlg.get_author()
            rec.status      = dlg.get_status()
            rec.framework   = dlg.get_framework()
            rec.model_path  = dlg.get_model_path()
            rec.config_path = dlg.get_config_path()
            rec.hyperparams = dlg.get_hyperparams()
            rec.tags        = dlg.get_tags()
            rec.feature_ids = dlg.get_feature_ids()
            rec.dataset_ids = dlg.get_dataset_ids()
            self._engine.update_model(rec)

    def _on_delete(self):
        rec = self._get_selected_record()
        if rec: self._engine.delete_model(rec.model_id)

    def _on_eval(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = ModelEvalDialog(rec.name, parent=self)
        if dlg.exec() == ModelEvalDialog.Accepted:
            self._engine.update_eval_metrics(
                rec.model_id,
                accuracy=dlg.get_accuracy(), auc=dlg.get_auc(),
                rmse=dlg.get_rmse(), mae=dlg.get_mae(),
                f1=dlg.get_f1(),
                custom_metrics=dlg.get_custom_metrics(),
            )

    def _on_run(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = ModelTrainingRunDialog(rec.name, parent=self)
        if dlg.exec() == ModelTrainingRunDialog.Accepted:
            self._engine.add_training_run(
                rec.model_id,
                run_note=dlg.get_note(),
                hyperparams=dlg.get_hyperparams(),
                metrics=dlg.get_metrics(),
                dataset_id=dlg.get_dataset_id(),
                duration_sec=dlg.get_duration(),
                created_by=dlg.get_author(),
            )

    def _on_deploy(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = ModelDeployDialog(rec.name, parent=self)
        if dlg.exec() == ModelDeployDialog.Accepted:
            self._engine.deploy_model(
                rec.model_id,
                env=dlg.get_env(), endpoint=dlg.get_endpoint(),
            )

    def _on_set_evaluated(self):
        rec = self._get_selected_record()
        if rec: self._engine.set_model_evaluated(rec.model_id)

    def _on_retire(self):
        rec = self._get_selected_record()
        if rec: self._engine.retire_model(rec.model_id)

    def _get_record_at(self, row):
        item = self._table.item(row, COL_ID)
        if item is None: return None
        return self._engine.get_model(item.data(Qt.UserRole))

    def _get_selected_record(self):
        return self._get_record_at(self._table.currentRow())
