"""
research_ops/ui/registry_tab.py  Phase 4 - Registry System
"""
from __future__ import annotations
from typing import List, Optional, Dict
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QDoubleSpinBox,
    QSpinBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..model.registry_model import (
    DatasetEntry, FeatureEntry, StrategyEntry, ModelEntry,
)
from ..constant import (
    DatasetStatus, FeatureStatus, StrategyStatus, ModelStatus,
)
from ..event import (
    EVENT_RO_DS_CREATED,  EVENT_RO_DS_UPDATED,  EVENT_RO_DS_DELETED,
    EVENT_RO_FT_CREATED,  EVENT_RO_FT_UPDATED,  EVENT_RO_FT_DELETED,
    EVENT_RO_ST_CREATED,  EVENT_RO_ST_UPDATED,  EVENT_RO_ST_DELETED,
    EVENT_RO_ML_CREATED,  EVENT_RO_ML_UPDATED,  EVENT_RO_ML_DELETED,
    EVENT_RO_ML_DEPLOYED,
)
from .experiment_tab import MetricChart
from ..model.experiment_model import MetricPoint

# ── status palettes ────────────────────────────────────────────────
DS_STATUS_COLOR = {
    DatasetStatus.PENDING:       "#6c757d",
    DatasetStatus.READY:       "#198754",
    DatasetStatus.OUTDATED:  "#dc3545",
    DatasetStatus.ERROR:    "#adb5bd",
}
FT_STATUS_COLOR = {
    FeatureStatus.DRAFT:       "#6c757d",
    FeatureStatus.STABLE:   "#198754",
    FeatureStatus.DEPRECATED:  "#dc3545",
    FeatureStatus.DEPRECATED:    "#adb5bd",
}
ST_STATUS_COLOR = {
    StrategyStatus.IDEA:      "#6c757d",
    StrategyStatus.RESEARCH: "#fd7e14",
    StrategyStatus.VALIDATED:  "#0d6efd",
    StrategyStatus.PRODUCTION:       "#198754",
    StrategyStatus.DEPRECATED:    "#adb5bd",
}
ML_STATUS_COLOR = {
    ModelStatus.TRAINING:       "#6c757d",
    ModelStatus.TRAINING:     "#fd7e14",
    ModelStatus.EVALUATED:   "#0d6efd",
    ModelStatus.DEPLOYED:    "#198754",
    ModelStatus.RETIRED:     "#adb5bd",
}

NODE_TYPE_ICON = {
    "dataset":  "\U0001f4be",
    "feature":  "\U0001f4d0",
    "strategy": "\U0001f4c8",
    "model":    "\U0001f916",
}

ROLE_ID   = Qt.UserRole
ROLE_TYPE = Qt.UserRole + 1


# =================================================================
# _StatCard  通用指标卡片
# =================================================================

def _make_stat_card(label: str, value: str,
                    color: str = "#1a1f36",
                    bg: str = "#ffffff") -> QFrame:
    card = QFrame()
    card.setFrameShape(QFrame.StyledPanel)
    card.setStyleSheet(
        "QFrame{background:" + bg + ";border:1px solid #dee2e6;"
        "border-radius:8px;padding:6px;}")
    lay = QVBoxLayout(card); lay.setSpacing(2)
    lbl = QLabel(label)
    lbl.setStyleSheet("color:#6c757d;font-size:11px;")
    lay.addWidget(lbl)
    val = QLabel(value)
    val.setStyleSheet(
        "font-size:18px;font-weight:bold;color:" + color + ";")
    val.setAlignment(Qt.AlignCenter)
    lay.addWidget(val)
    card._val_lbl = val
    card._lbl_lbl = lbl
    return card


def _sep_v() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.VLine)
    f.setStyleSheet("color:#dee2e6;"); return f


# =================================================================
# LineageTreeWidget  血缘关系树
# =================================================================

class LineageTreeWidget(QTreeWidget):
    def __init__(self, engine: ResearchOpsEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setAnimated(True)

    def load(self, node_id: str):
        self.clear()
        if not node_id:
            return
        lg = self._engine.registry.lineage

        # upstream section
        up_root = QTreeWidgetItem([
            "\u2191 \u4e0a\u6e38\u8840\u7f18 (ancestors)"])
        up_root.setForeground(0, QBrush(QColor("#0d6efd")))
        f = QFont(); f.setBold(True); up_root.setFont(0, f)
        for anc_id in sorted(lg.ancestors(node_id)):
            info = lg._graph.get(anc_id, {})
            ntype = info.get("node_type", "")
            icon  = NODE_TYPE_ICON.get(ntype, "\u25cb")
            label = info.get("label", anc_id)
            item  = QTreeWidgetItem([icon + "  " + label + "  [" + anc_id[:8] + "]"])
            item.setData(0, ROLE_ID, anc_id)
            item.setData(0, ROLE_TYPE, ntype)
            item.setForeground(0, QBrush(QColor("#0d6efd")))
            up_root.addChild(item)
        self.addTopLevelItem(up_root)
        up_root.setExpanded(True)

        # current node
        cur_info = lg._graph.get(node_id, {})
        cur_type = cur_info.get("node_type", "")
        cur_lbl  = cur_info.get("label", node_id)
        cur_item = QTreeWidgetItem([
            "\u25cf  " + NODE_TYPE_ICON.get(cur_type,"") + "  " + cur_lbl
            + "  \u2190 \u5f53\u524d"])
        cur_item.setData(0, ROLE_ID, node_id)
        f2 = QFont(); f2.setBold(True); cur_item.setFont(0, f2)
        cur_item.setForeground(0, QBrush(QColor("#1a1f36")))
        self.addTopLevelItem(cur_item)

        # downstream section
        dn_root = QTreeWidgetItem([
            "\u2193 \u4e0b\u6e38\u8840\u7f18 (descendants)"])
        dn_root.setForeground(0, QBrush(QColor("#198754")))
        dn_root.setFont(0, f)
        for desc_id in sorted(lg.descendants(node_id)):
            info  = lg._graph.get(desc_id, {})
            ntype = info.get("node_type", "")
            icon  = NODE_TYPE_ICON.get(ntype, "\u25cb")
            label = info.get("label", desc_id)
            item  = QTreeWidgetItem([icon + "  " + label + "  [" + desc_id[:8] + "]"])
            item.setData(0, ROLE_ID, desc_id)
            item.setData(0, ROLE_TYPE, ntype)
            item.setForeground(0, QBrush(QColor("#198754")))
            dn_root.addChild(item)
        self.addTopLevelItem(dn_root)
        dn_root.setExpanded(True)


class DatasetDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91\u6570\u636e\u96c6" if self._editing
            else "\u6ce8\u518c\u6570\u636e\u96c6")
        self.setMinimumWidth(480)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u6570\u636e\u96c6\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._name.setPlaceholderText("\u6570\u636e\u96c6\u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._source = QLineEdit()
        self._source.setPlaceholderText("tushare / wind / akshare")
        form.addRow("\u6570\u636e\u6e90", self._source)
        self._start = QLineEdit(); self._start.setPlaceholderText("2015-01-01")
        form.addRow("\u5f00\u59cb\u65e5\u671f", self._start)
        self._end = QLineEdit(); self._end.setPlaceholderText("2024-12-31")
        form.addRow("\u7ed3\u675f\u65e5\u671f", self._end)
        self._row_count = QSpinBox()
        self._row_count.setRange(0, 999_999_999)
        form.addRow("\u884c\u6570", self._row_count)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name); self._desc.setPlainText(r.description)
        self._source.setText(r.source)
        self._start.setText(r.start_date or ""); self._end.setText(r.end_date or "")
        self._row_count.setValue(r.row_count or 0)
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_source(self)      -> str:       return self._source.text().strip()
    def get_start_date(self)  -> str:       return self._start.text().strip()
    def get_end_date(self)    -> str:       return self._end.text().strip()
    def get_row_count(self)   -> int:       return self._row_count.value()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


class DatasetList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._filter  = None
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\u5168\u90e8", None)
        for st in DatasetStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u540d\u79f0","\u7248\u672c","\u72b6\u6001","\u884c\u6570"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_DS_CREATED, EVENT_RO_DS_UPDATED, EVENT_RO_DS_DELETED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_datasets()
        if self._filter:
            items = [d for d in items if d.status == self._filter]
        if self._keyword:
            items = [d for d in items if self._keyword in d.name.lower()]
        self._table.setRowCount(0)
        for ds in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(ds.name))
            self._table.setItem(r, 1, QTableWidgetItem(ds.version))
            sc   = DS_STATUS_COLOR.get(ds.status, "#6c757d")
            si   = QTableWidgetItem(ds.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 2, si)
            ri = QTableWidgetItem(str(ds.row_count or 0))
            ri.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 3, ri)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, ds.dataset_id)

    def _on_click(self, item):
        self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        did = item.data(ROLE_ID)
        ds  = self._engine.get_dataset(did)
        if not ds: return
        menu = QMenu(self)
        a_ready = menu.addAction("\u2705  \u6807\u4e3a Ready")
        a_dep   = menu.addAction("\u26a0  \u6807\u4e3a Deprecated")
        menu.addSeparator()
        a_del   = menu.addAction("\U0001f5d1  \u5220\u9664")
        action  = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_ready:
            self._engine.set_dataset_ready(did); self._refresh()
        elif action == a_dep:
            ds.status = DatasetStatus.OUTDATED
            self._engine.update_dataset(ds); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664\u6570\u636e\u96c6\u300c" + ds.name + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_dataset(did); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class DatasetDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        # Tab1: overview
        ov = QWidget(); ov_l = QVBoxLayout(ov)
        self._title = QLabel("\u8bf7\u9009\u62e9\u6570\u636e\u96c6")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        ov_l.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_rows = _make_stat_card("\u884c\u6570", "0")
        self._c_size = _make_stat_card("\u5927\u5c0f(MB)", "0")
        self._c_qual = _make_stat_card("\u8d28\u91cf\u5206", "0")
        self._c_ver  = _make_stat_card("\u7248\u672c\u6570", "0")
        for c in (self._c_rows, self._c_size, self._c_qual, self._c_ver):
            cr.addWidget(c)
        ov_l.addLayout(cr)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\U0001f4cb  \u6982\u89c8")

        # Tab2: versions
        vt = QWidget(); vt_l = QVBoxLayout(vt)
        self._ver_table = QTableWidget(0, 3)
        self._ver_table.setHorizontalHeaderLabels(
            ["\u7248\u672c","\u884c\u6570","\u65f6\u95f4"])
        self._ver_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ver_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ver_table.setAlternatingRowColors(True)
        self._ver_table.verticalHeader().setVisible(False)
        vt_l.addWidget(self._ver_table)
        self.addTab(vt, "\U0001f4dc  \u7248\u672c")

        # Tab3: lineage
        lt = QWidget(); lt_l = QVBoxLayout(lt)
        self._lineage = LineageTreeWidget(engine)
        lt_l.addWidget(self._lineage)
        self.addTab(lt, "\U0001f9ec  \u8840\u7f18")

    def load(self, did: str):
        self._id = did
        ds = self._engine.get_dataset(did)
        if not ds: return
        self._title.setText(ds.name)
        sc = DS_STATUS_COLOR.get(ds.status, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        self._c_rows._val_lbl.setText(str(ds.row_count or 0))
        self._c_size._val_lbl.setText(str(ds.size_mb or 0))
        self._c_qual._val_lbl.setText(str(round(ds.quality_score or 0, 2)))
        self._c_ver._val_lbl.setText(str(len(ds.versions or [])))
        self._info.setRowCount(0)
        for k, v in [
            ("ID", ds.dataset_id), ("\u540d\u79f0", ds.name),
            ("\u7248\u672c", ds.version), ("\u72b6\u6001", ds.status.value),
            ("\u6570\u636e\u6e90", ds.source or "\u2014"),
            ("\u5f00\u59cb", ds.start_date or "\u2014"),
            ("\u7ed3\u675f", ds.end_date or "\u2014"),
            ("\u6807\u7b7e", ", ".join(ds.tags) if ds.tags else "\u2014"),
            ("\u63cf\u8ff0", ds.description or "\u2014"),
            ("\u521b\u5efa", ds.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._ver_table.setRowCount(0)
        for ver in (ds.versions or []):
            r = self._ver_table.rowCount(); self._ver_table.insertRow(r)
            self._ver_table.setItem(r, 0, QTableWidgetItem(ver.get("version","?")))
            self._ver_table.setItem(r, 1, QTableWidgetItem(str(ver.get("row_count",0))))
            ts = ver.get("created_at","")
            if hasattr(ts, "strftime"): ts = ts.strftime("%Y-%m-%d %H:%M")
            self._ver_table.setItem(r, 2, QTableWidgetItem(str(ts)))
        self._lineage.load(did)

    def clear(self):
        self._id = None
        self._title.setText("\u8bf7\u9009\u62e9\u6570\u636e\u96c6")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for c in (self._c_rows, self._c_size, self._c_qual, self._c_ver):
            c._val_lbl.setText("0")
        self._info.setRowCount(0)
        self._ver_table.setRowCount(0)
        self._lineage.clear()


class FeatureDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91\u56e0\u5b50" if self._editing else "\u6ce8\u518c\u56e0\u5b50")
        self.setMinimumWidth(480)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u56e0\u5b50\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._category = QLineEdit()
        self._category.setPlaceholderText("momentum / reversal / quality")
        form.addRow("\u5206\u7c7b", self._category)
        self._author = QLineEdit()
        form.addRow("\u4f5c\u8005", self._author)
        self._formula = QTextEdit(); self._formula.setFixedHeight(52)
        form.addRow("\u516c\u5f0f", self._formula)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name); self._desc.setPlainText(r.description)
        self._category.setText(r.category or ""); self._author.setText(r.author or "")
        self._formula.setPlainText(r.formula or "")
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_category(self)    -> str:       return self._category.text().strip()
    def get_author(self)      -> str:       return self._author.text().strip()
    def get_formula(self)     -> str:       return self._formula.toPlainText().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


class IcMetricDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u66f4\u65b0 IC \u6307\u6807")
        self.setMinimumWidth(360)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("IC \u6307\u6807")
        form = QFormLayout(grp)

        def _spin(lo=-1.0, hi=1.0, dec=4, step=0.001):
            s = QDoubleSpinBox()
            s.setRange(lo, hi); s.setDecimals(dec); s.setSingleStep(step)
            return s

        self._ic   = _spin(); form.addRow("IC", self._ic)
        self._rank = _spin(); form.addRow("Rank IC", self._rank)
        self._ir   = _spin(-10, 10, 3, 0.01); form.addRow("IR", self._ir)
        self._icir = _spin(-10, 10, 3, 0.01); form.addRow("ICIR", self._icir)
        self._cov  = _spin(0.0, 1.0, 3, 0.01); form.addRow("Coverage", self._cov)
        self._period = QLineEdit(); self._period.setPlaceholderText("2024 / 2024Q1")
        form.addRow("\u671f\u95f4", self._period)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def get_ic(self)      -> float: return self._ic.value()
    def get_rank_ic(self) -> float: return self._rank.value()
    def get_ir(self)      -> float: return self._ir.value()
    def get_icir(self)    -> float: return self._icir.value()
    def get_coverage(self)-> float: return self._cov.value()
    def get_period(self)  -> str:   return self._period.text().strip()


class FeatureList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._filter  = None
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\u5168\u90e8", None)
        for st in FeatureStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u540d\u79f0","\u5206\u7c7b","IC","\u72b6\u6001"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_FT_CREATED, EVENT_RO_FT_UPDATED, EVENT_RO_FT_DELETED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_features()
        if self._filter:
            items = [f for f in items if f.status == self._filter]
        if self._keyword:
            items = [f for f in items if self._keyword in f.name.lower()
                     or self._keyword in (f.category or "").lower()]
        items.sort(key=lambda f: (f.ic or 0), reverse=True)
        self._table.setRowCount(0)
        for ft in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(ft.name))
            self._table.setItem(r, 1, QTableWidgetItem(ft.category or ""))
            ic_val = round(ft.ic or 0, 4)
            ic_item = QTableWidgetItem(str(ic_val))
            ic_item.setTextAlignment(Qt.AlignCenter)
            col = ("#198754" if ic_val >= 0.04
                   else "#dc3545" if ic_val <= 0 else "#fd7e14")
            ic_item.setForeground(QBrush(QColor(col)))
            self._table.setItem(r, 2, ic_item)
            sc = FT_STATUS_COLOR.get(ft.status, "#6c757d")
            si = QTableWidgetItem(ft.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 3, si)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, ft.feature_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        fid = item.data(ROLE_ID)
        ft  = self._engine.get_feature(fid)
        if not ft: return
        menu = QMenu(self)
        a_val = menu.addAction("\u2705  Validated")
        a_dep = menu.addAction("\u26a0  Deprecated")
        menu.addSeparator()
        a_del = menu.addAction("\U0001f5d1  \u5220\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_val:
            self._engine.set_feature_status(fid, FeatureStatus.STABLE); self._refresh()
        elif action == a_dep:
            self._engine.set_feature_status(fid, FeatureStatus.DEPRECATED); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664\u56e0\u5b50\u300c" + ft.name + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_feature(fid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class FeatureDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        ov = QWidget(); ov_l = QVBoxLayout(ov)
        self._title = QLabel("\u8bf7\u9009\u62e9\u56e0\u5b50")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        ov_l.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_ic   = _make_stat_card("IC",       "\u2014")
        self._c_rank = _make_stat_card("Rank IC",  "\u2014")
        self._c_ir   = _make_stat_card("IR",       "\u2014")
        self._c_icir = _make_stat_card("ICIR",     "\u2014")
        self._c_cov  = _make_stat_card("Coverage", "\u2014")
        for c in (self._c_ic, self._c_rank, self._c_ir, self._c_icir, self._c_cov):
            cr.addWidget(c)
        ov_l.addLayout(cr)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\U0001f4cb  \u6982\u89c8")

        ht = QWidget(); ht_l = QVBoxLayout(ht)
        self._ic_chart = MetricChart()
        ht_l.addWidget(self._ic_chart)
        self.addTab(ht, "\U0001f4c8  IC \u5386\u53f2")

        lt = QWidget(); lt_l = QVBoxLayout(lt)
        self._lineage = LineageTreeWidget(engine)
        lt_l.addWidget(self._lineage)
        self.addTab(lt, "\U0001f9ec  \u8840\u7f18")

    def load(self, fid: str):
        self._id = fid
        ft = self._engine.get_feature(fid)
        if not ft: return
        self._title.setText(ft.name)
        sc = FT_STATUS_COLOR.get(ft.status, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        def _fmt(v): return str(round(v, 4)) if v is not None else "\u2014"
        self._c_ic._val_lbl.setText(_fmt(ft.ic))
        self._c_rank._val_lbl.setText(_fmt(ft.rank_ic))
        self._c_ir._val_lbl.setText(_fmt(ft.ir))
        self._c_icir._val_lbl.setText(_fmt(ft.icir))
        self._c_cov._val_lbl.setText(_fmt(ft.coverage))
        if ft.ic is not None:
            col = "#198754" if ft.ic >= 0.04 else ("#dc3545" if ft.ic <= 0 else "#fd7e14")
            self._c_ic._val_lbl.setStyleSheet(
                "font-size:18px;font-weight:bold;color:" + col + ";")
        self._info.setRowCount(0)
        for k, v in [
            ("ID", ft.feature_id), ("\u540d\u79f0", ft.name),
            ("\u7248\u672c", ft.version), ("\u72b6\u6001", ft.status.value),
            ("\u5206\u7c7b", ft.category or "\u2014"),
            ("\u4f5c\u8005", ft.author or "\u2014"),
            ("\u6807\u7b7e", ", ".join(ft.tags) if ft.tags else "\u2014"),
            ("Git", ft.git_commit or "\u2014"),
            ("\u63cf\u8ff0", ft.description or "\u2014"),
            ("\u521b\u5efa", ft.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        hist = ft.ic_history or []
        if hist:
            pts = [MetricPoint(key="IC", value=h.get("ic", 0), step=i+1)
                   for i, h in enumerate(hist)]
            self._ic_chart.set_series({"IC": pts}, title="IC \u5386\u53f2")
        else:
            self._ic_chart.clear()
        self._lineage.load(fid)

    def clear(self):
        self._id = None
        self._title.setText("\u8bf7\u9009\u62e9\u56e0\u5b50")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for c in (self._c_ic, self._c_rank, self._c_ir, self._c_icir, self._c_cov):
            c._val_lbl.setText("\u2014")
        self._info.setRowCount(0)
        self._ic_chart.clear()
        self._lineage.clear()


class StrategyDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91\u7b56\u7565" if self._editing else "\u6ce8\u518c\u7b56\u7565")
        self.setMinimumWidth(480)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u7b56\u7565\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._author = QLineEdit()
        form.addRow("\u4f5c\u8005", self._author)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name); self._desc.setPlainText(r.description)
        self._author.setText(r.author or "")
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_author(self)      -> str:       return self._author.text().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


class StrategyList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._filter  = None
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\u5168\u90e8", None)
        for st in StrategyStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u540d\u79f0","Sharpe","\u5e74\u5316","\u72b6\u6001"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_ST_CREATED, EVENT_RO_ST_UPDATED, EVENT_RO_ST_DELETED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_strategies()
        if self._filter:
            items = [s for s in items if s.status == self._filter]
        if self._keyword:
            items = [s for s in items if self._keyword in s.name.lower()]
        items.sort(key=lambda s: (s.sharpe or 0), reverse=True)
        self._table.setRowCount(0)
        for st in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(st.name))
            sh = round(st.sharpe or 0, 2)
            sh_item = QTableWidgetItem(str(sh))
            sh_item.setTextAlignment(Qt.AlignCenter)
            sh_item.setForeground(QBrush(QColor(
                "#198754" if sh >= 1.5 else "#dc3545" if sh <= 0 else "#fd7e14")))
            self._table.setItem(r, 1, sh_item)
            ar = str(round((st.annual_return or 0) * 100, 1)) + "%"
            ar_item = QTableWidgetItem(ar)
            ar_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 2, ar_item)
            sc = ST_STATUS_COLOR.get(st.status, "#6c757d")
            si = QTableWidgetItem(st.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 3, si)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, st.strategy_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        sid = item.data(ROLE_ID)
        st  = self._engine.get_strategy(sid)
        if not st: return
        menu = QMenu(self)
        sm = menu.addMenu("\u8bbe\u7f6e\u72b6\u6001")
        a_bt  = sm.addAction("\u56de\u6d4b\u5b8c\u6210")
        a_val = sm.addAction("\u5df2\u9a8c\u8bc1")
        a_live= sm.addAction("\u5b9e\u76d8")
        a_ret = sm.addAction("\u5df2\u9000\u5f03")
        menu.addSeparator()
        a_del = menu.addAction("\U0001f5d1  \u5220\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        status_map = {
            a_bt:  StrategyStatus.RESEARCH,
            a_val: StrategyStatus.VALIDATED,
            a_live:StrategyStatus.PRODUCTION,
            a_ret: StrategyStatus.DEPRECATED,
        }
        if action in status_map:
            self._engine.set_strategy_status(sid, status_map[action])
            self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664\u7b56\u7565\u300c" + st.name + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_strategy(sid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class StrategyDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        ov = QWidget(); ov_l = QVBoxLayout(ov)
        self._title = QLabel("\u8bf7\u9009\u62e9\u7b56\u7565")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        ov_l.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_ar  = _make_stat_card("\u5e74\u5316\u6536\u76ca", "\u2014")
        self._c_sh  = _make_stat_card("Sharpe", "\u2014")
        self._c_dd  = _make_stat_card("MaxDD", "\u2014")
        self._c_wr  = _make_stat_card("\u80dc\u7387", "\u2014")
        self._c_so  = _make_stat_card("Sortino", "\u2014")
        for c in (self._c_ar, self._c_sh, self._c_dd, self._c_wr, self._c_so):
            cr.addWidget(c)
        ov_l.addLayout(cr)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\U0001f4cb  \u6982\u89c8")

        vt = QWidget(); vt_l = QVBoxLayout(vt)
        self._ver_table = QTableWidget(0, 3)
        self._ver_table.setHorizontalHeaderLabels(
            ["\u7248\u672c","\u5907\u6ce8","\u65f6\u95f4"])
        self._ver_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ver_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ver_table.setAlternatingRowColors(True)
        self._ver_table.verticalHeader().setVisible(False)
        vt_l.addWidget(self._ver_table)
        self.addTab(vt, "\U0001f4dc  \u7248\u672c")

        lt = QWidget(); lt_l = QVBoxLayout(lt)
        self._lineage = LineageTreeWidget(engine)
        lt_l.addWidget(self._lineage)
        self.addTab(lt, "\U0001f9ec  \u8840\u7f18")

    def load(self, sid: str):
        self._id = sid
        st = self._engine.get_strategy(sid)
        if not st: return
        self._title.setText(st.name)
        sc = ST_STATUS_COLOR.get(st.status, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        def _pct(v): return str(round((v or 0)*100,1))+"%" if v is not None else "\u2014"
        def _fmt(v): return str(round(v,3)) if v is not None else "\u2014"
        self._c_ar._val_lbl.setText(_pct(st.annual_return))
        sh = st.sharpe or 0
        self._c_sh._val_lbl.setText(_fmt(st.sharpe))
        self._c_sh._val_lbl.setStyleSheet(
            "font-size:18px;font-weight:bold;color:"
            + ("#198754" if sh >= 1.5 else "#dc3545" if sh <= 0 else "#fd7e14") + ";")
        dd = st.max_drawdown or 0
        self._c_dd._val_lbl.setText(_pct(st.max_drawdown))
        self._c_dd._val_lbl.setStyleSheet(
            "font-size:18px;font-weight:bold;color:"
            + ("#dc3545" if dd <= -0.2 else "#198754" if dd >= -0.1 else "#fd7e14") + ";")
        self._c_wr._val_lbl.setText(_pct(st.win_rate))
        self._c_so._val_lbl.setText(_fmt(st.sortino))
        self._info.setRowCount(0)
        for k, v in [
            ("ID", st.strategy_id), ("\u540d\u79f0", st.name),
            ("\u7248\u672c", st.version), ("\u72b6\u6001", st.status.value),
            ("\u4f5c\u8005", st.author or "\u2014"),
            ("\u6807\u7b7e", ", ".join(st.tags) if st.tags else "\u2014"),
            ("Git", st.git_commit or "\u2014"),
            ("\u56e0\u5b50\u6570", len(st.feature_ids)),
            ("\u6a21\u578b\u6570", len(st.model_ids)),
            ("\u521b\u5efa", st.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._ver_table.setRowCount(0)
        for ver in (st.versions or []):
            r = self._ver_table.rowCount(); self._ver_table.insertRow(r)
            self._ver_table.setItem(r, 0, QTableWidgetItem(ver.get("version","?")))
            self._ver_table.setItem(r, 1, QTableWidgetItem(ver.get("note","") or ""))
            ts = ver.get("created_at","")
            if hasattr(ts, "strftime"): ts = ts.strftime("%Y-%m-%d %H:%M")
            self._ver_table.setItem(r, 2, QTableWidgetItem(str(ts)))
        self._lineage.load(sid)

    def clear(self):
        self._id = None
        self._title.setText("\u8bf7\u9009\u62e9\u7b56\u7565")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for c in (self._c_ar, self._c_sh, self._c_dd, self._c_wr, self._c_so):
            c._val_lbl.setText("\u2014")
        self._info.setRowCount(0)
        self._ver_table.setRowCount(0)
        self._lineage.clear()


class ModelDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91\u6a21\u578b" if self._editing else "\u6ce8\u518c\u6a21\u578b")
        self.setMinimumWidth(480)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u6a21\u578b\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._model_type = QLineEdit()
        self._model_type.setPlaceholderText("lightgbm / xgboost / lstm ...")
        form.addRow("\u6a21\u578b\u7c7b\u578b", self._model_type)
        self._framework = QLineEdit()
        self._framework.setPlaceholderText("lightgbm 4.3 / sklearn 1.4")
        form.addRow("\u6846\u67b6", self._framework)
        self._author = QLineEdit()
        form.addRow("\u4f5c\u8005", self._author)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name); self._desc.setPlainText(r.description)
        self._model_type.setText(r.model_type or "")
        self._framework.setText(r.framework or "")
        self._author.setText(r.author or "")
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_model_type(self)  -> str:       return self._model_type.text().strip()
    def get_framework(self)   -> str:       return self._framework.text().strip()
    def get_author(self)      -> str:       return self._author.text().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


class ModelList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._filter  = None
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\u5168\u90e8", None)
        for st in ModelStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u540d\u79f0","\u7c7b\u578b","AUC","\u72b6\u6001"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_ML_CREATED, EVENT_RO_ML_UPDATED,
                   EVENT_RO_ML_DELETED, EVENT_RO_ML_DEPLOYED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_models()
        if self._filter:
            items = [m for m in items if m.status == self._filter]
        if self._keyword:
            items = [m for m in items if self._keyword in m.name.lower()
                     or self._keyword in (m.model_type or "").lower()]
        items.sort(key=lambda m: (m.auc or 0), reverse=True)
        self._table.setRowCount(0)
        for ml in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(ml.name))
            self._table.setItem(r, 1, QTableWidgetItem(ml.model_type or ""))
            auc = round(ml.auc or 0, 4)
            ai  = QTableWidgetItem(str(auc))
            ai.setTextAlignment(Qt.AlignCenter)
            ai.setForeground(QBrush(QColor(
                "#198754" if auc >= 0.7 else "#dc3545" if auc <= 0.5 else "#fd7e14")))
            self._table.setItem(r, 2, ai)
            sc = ML_STATUS_COLOR.get(ml.status, "#6c757d")
            si = QTableWidgetItem(ml.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 3, si)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, ml.model_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        mid = item.data(ROLE_ID)
        ml  = self._engine.get_model(mid)
        if not ml: return
        menu = QMenu(self)
        sm    = menu.addMenu("\u8bbe\u7f6e\u72b6\u6001")
        a_tr  = sm.addAction("\u5df2\u8bad\u7ec3")
        a_ev  = sm.addAction("\u5df2\u8bc4\u4f30")
        a_dep = sm.addAction("\u5df2\u90e8\u7f72")
        a_ret = sm.addAction("\u5df2\u9000\u5f03")
        menu.addSeparator()
        a_del = menu.addAction("\U0001f5d1  \u5220\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        status_map = {
            a_tr:  ModelStatus.TRAINING,
            a_ev:  ModelStatus.EVALUATED,
            a_dep: ModelStatus.DEPLOYED,
            a_ret: ModelStatus.RETIRED,
        }
        if action in status_map:
            self._engine.set_model_status(mid, status_map[action]); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664\u6a21\u578b\u300c" + ml.name + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_model(mid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class ModelDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        ov = QWidget(); ov_l = QVBoxLayout(ov)
        self._title = QLabel("\u8bf7\u9009\u62e9\u6a21\u578b")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        ov_l.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_auc = _make_stat_card("AUC",      "\u2014")
        self._c_acc = _make_stat_card("Accuracy", "\u2014")
        self._c_f1  = _make_stat_card("F1",       "\u2014")
        self._c_dep = _make_stat_card("\u73af\u5883",  "\u2014")
        for c in (self._c_auc, self._c_acc, self._c_f1, self._c_dep):
            cr.addWidget(c)
        ov_l.addLayout(cr)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\U0001f4cb  \u6982\u89c8")

        tt = QWidget(); tt_l = QVBoxLayout(tt)
        self._train_table = QTableWidget(0, 3)
        self._train_table.setHorizontalHeaderLabels(
            ["\u8bad\u7ec3 ID","\u6307\u6807","\u65f6\u95f4"])
        self._train_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._train_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._train_table.setAlternatingRowColors(True)
        self._train_table.verticalHeader().setVisible(False)
        tt_l.addWidget(self._train_table)
        self.addTab(tt, "\U0001f3cb  \u8bad\u7ec3\u5386\u53f2")

        lt = QWidget(); lt_l = QVBoxLayout(lt)
        self._lineage = LineageTreeWidget(engine)
        lt_l.addWidget(self._lineage)
        self.addTab(lt, "\U0001f9ec  \u8840\u7f18")

    def load(self, mid: str):
        self._id = mid
        ml = self._engine.get_model(mid)
        if not ml: return
        self._title.setText(ml.name)
        sc = ML_STATUS_COLOR.get(ml.status, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        def _fmt(v): return str(round(v, 4)) if v is not None else "\u2014"
        auc = ml.auc or 0
        self._c_auc._val_lbl.setText(_fmt(ml.auc))
        self._c_auc._val_lbl.setStyleSheet(
            "font-size:18px;font-weight:bold;color:"
            + ("#198754" if auc >= 0.7 else "#dc3545" if auc <= 0.5 else "#fd7e14") + ";")
        self._c_acc._val_lbl.setText(_fmt(ml.accuracy))
        self._c_f1._val_lbl.setText(_fmt(ml.f1))
        self._c_dep._val_lbl.setText(ml.deploy_env or "\u672a\u90e8\u7f72")
        self._info.setRowCount(0)
        for k, v in [
            ("ID", ml.model_id), ("\u540d\u79f0", ml.name),
            ("\u7248\u672c", ml.version), ("\u72b6\u6001", ml.status.value),
            ("\u6a21\u578b\u7c7b\u578b", ml.model_type or "\u2014"),
            ("\u6846\u67b6", ml.framework or "\u2014"),
            ("\u4f5c\u8005", ml.author or "\u2014"),
            ("\u90e8\u7f72\u73af\u5883", ml.deploy_env or "\u2014"),
            ("\u90e8\u7f72\u5730\u5740", ml.deploy_endpoint or "\u2014"),
            ("Git", ml.git_commit or "\u2014"),
            ("\u56e0\u5b50\u6570", len(ml.feature_ids)),
            ("\u521b\u5efa", ml.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._train_table.setRowCount(0)
        for tr in (ml.training_runs or []):
            r = self._train_table.rowCount(); self._train_table.insertRow(r)
            self._train_table.setItem(r, 0, QTableWidgetItem(tr.get("run_id","")[:12]))
            m_str = ", ".join(
                k+"="+str(round(v,4))
                for k,v in (tr.get("metrics") or {}).items())
            self._train_table.setItem(r, 1, QTableWidgetItem(m_str))
            ts = tr.get("created_at","")
            if hasattr(ts,"strftime"): ts = ts.strftime("%Y-%m-%d %H:%M")
            self._train_table.setItem(r, 2, QTableWidgetItem(str(ts)))
        self._lineage.load(mid)

    def clear(self):
        self._id = None
        self._title.setText("\u8bf7\u9009\u62e9\u6a21\u578b")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for c in (self._c_auc, self._c_acc, self._c_f1, self._c_dep):
            c._val_lbl.setText("\u2014")
        self._info.setRowCount(0)
        self._train_table.setRowCount(0)
        self._lineage.clear()


class RegistryTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new  = QPushButton("+ \u6ce8\u518c")
        self._btn_edit = QPushButton("\u270f  \u7f16\u8f91")
        self._btn_del  = QPushButton("\U0001f5d1  \u5220\u9664")
        for btn in (self._btn_new, self._btn_edit, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        tb.addWidget(QLabel("\u641c\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\u540d\u79f0 / \u6807\u7b7e...")
        self._search_box.setFixedWidth(160); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\u641c\u7d22")
        self._btn_search.setFixedSize(52, 28)
        self._btn_reset  = QPushButton("\u91cd\u7f6e")
        self._btn_reset.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset)
        root.addLayout(tb)

        self._stats_bar = QLabel("\u52a0\u8f7d\u4e2d...")
        self._stats_bar.setStyleSheet(
            "background:#f0fff4;border:1px solid #a3cfbb;"
            "border-radius:4px;padding:4px 10px;"
            "color:#198754;font-size:12px;")
        root.addWidget(self._stats_bar)

        self._sub_tabs = QTabWidget()
        self._sub_tabs.setDocumentMode(True)

        def _make_split(list_w, detail_w):
            w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
            sp = QSplitter(Qt.Horizontal)
            sp.addWidget(list_w); sp.addWidget(detail_w)
            sp.setSizes([260, 740])
            sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
            l.addWidget(sp); return w

        self._ds_list   = DatasetList(self._engine)
        self._ds_detail = DatasetDetail(self._engine)
        self._sub_tabs.addTab(_make_split(self._ds_list, self._ds_detail),
                              "\U0001f4be  Dataset")

        self._ft_list   = FeatureList(self._engine)
        self._ft_detail = FeatureDetail(self._engine)
        self._sub_tabs.addTab(_make_split(self._ft_list, self._ft_detail),
                              "\U0001f4d0  Feature")

        self._st_list   = StrategyList(self._engine)
        self._st_detail = StrategyDetail(self._engine)
        self._sub_tabs.addTab(_make_split(self._st_list, self._st_detail),
                              "\U0001f4c8  Strategy")

        self._ml_list   = ModelList(self._engine)
        self._ml_detail = ModelDetail(self._engine)
        self._sub_tabs.addTab(_make_split(self._ml_list, self._ml_detail),
                              "\U0001f916  Model")

        root.addWidget(self._sub_tabs)

        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        self._ds_list.selected.connect(self._ds_detail.load)
        self._ft_list.selected.connect(self._ft_detail.load)
        self._st_list.selected.connect(self._st_detail.load)
        self._ml_list.selected.connect(self._ml_detail.load)
        self._ds_list.selected.connect(lambda i: self._on_sel("Dataset", i))
        self._ft_list.selected.connect(lambda i: self._on_sel("Feature", i))
        self._st_list.selected.connect(lambda i: self._on_sel("Strategy", i))
        self._ml_list.selected.connect(lambda i: self._on_sel("Model", i))

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset.clicked.connect(self._on_reset)
        self._search_box.returnPressed.connect(self._on_search)

        for ev in (EVENT_RO_DS_CREATED, EVENT_RO_DS_UPDATED, EVENT_RO_DS_DELETED,
                   EVENT_RO_FT_CREATED, EVENT_RO_FT_UPDATED, EVENT_RO_FT_DELETED,
                   EVENT_RO_ST_CREATED, EVENT_RO_ST_UPDATED, EVENT_RO_ST_DELETED,
                   EVENT_RO_ML_CREATED, EVENT_RO_ML_UPDATED, EVENT_RO_ML_DELETED,
                   EVENT_RO_ML_DEPLOYED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    def _on_sel(self, label, item_id):
        getters = {
            "Dataset":  self._engine.get_dataset,
            "Feature":  self._engine.get_feature,
            "Strategy": self._engine.get_strategy,
            "Model":    self._engine.get_model,
        }
        obj = getters[label](item_id)
        name = obj.name if obj else item_id
        self._set_status(label + ": " + name)

    def _current_tab(self) -> int:
        return self._sub_tabs.currentIndex()

    def _selected_id(self):
        idx = self._current_tab()
        if idx == 0: return self._ds_list.selected_id()
        if idx == 1: return self._ft_list.selected_id()
        if idx == 2: return self._st_list.selected_id()
        if idx == 3: return self._ml_list.selected_id()
        return None

    def _on_new(self):
        idx = self._current_tab()
        if idx == 0:
            dlg = DatasetDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                ds = self._engine.register_dataset(
                    name=dlg.get_name(), source=dlg.get_source(),
                    description=dlg.get_description(),
                    start_date=dlg.get_start_date(),
                    end_date=dlg.get_end_date(),
                    row_count=dlg.get_row_count(),
                    tags=dlg.get_tags())
                self._set_status("Dataset \u300c" + ds.name + "\u300d\u5df2\u6ce8\u518c")
                self._refresh_stats()
        elif idx == 1:
            dlg = FeatureDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                ft = self._engine.register_feature(
                    name=dlg.get_name(), category=dlg.get_category(),
                    author=dlg.get_author(), description=dlg.get_description(),
                    formula=dlg.get_formula(), tags=dlg.get_tags())
                self._set_status("Feature \u300c" + ft.name + "\u300d\u5df2\u6ce8\u518c")
                self._refresh_stats()
        elif idx == 2:
            dlg = StrategyDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                st = self._engine.register_strategy(
                    name=dlg.get_name(), author=dlg.get_author(),
                    description=dlg.get_description(), tags=dlg.get_tags())
                self._set_status("Strategy \u300c" + st.name + "\u300d\u5df2\u6ce8\u518c")
                self._refresh_stats()
        elif idx == 3:
            dlg = ModelDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                ml = self._engine.register_model(
                    name=dlg.get_name(), model_type=dlg.get_model_type(),
                    framework=dlg.get_framework(), author=dlg.get_author(),
                    description=dlg.get_description(), tags=dlg.get_tags())
                self._set_status("Model \u300c" + ml.name + "\u300d\u5df2\u6ce8\u518c")
                self._refresh_stats()

    def _on_edit(self):
        idx = self._current_tab()
        sel = self._selected_id()
        if not sel:
            self._set_status("\u8bf7\u5148\u9009\u62e9\u8981\u7f16\u8f91\u7684\u6761\u76ee")
            return
        if idx == 0:
            ds = self._engine.get_dataset(sel)
            if not ds: return
            dlg = DatasetDialog(parent=self, record=ds)
            if dlg.exec() == QDialog.Accepted:
                ds.name = dlg.get_name(); ds.description = dlg.get_description()
                ds.source = dlg.get_source(); ds.start_date = dlg.get_start_date()
                ds.end_date = dlg.get_end_date(); ds.row_count = dlg.get_row_count()
                ds.tags = dlg.get_tags()
                self._engine.update_dataset(ds)
                self._ds_detail.load(sel)
                self._set_status("Dataset \u300c" + ds.name + "\u300d\u5df2\u66f4\u65b0")
        elif idx == 1:
            ft = self._engine.get_feature(sel)
            if not ft: return
            dlg = FeatureDialog(parent=self, record=ft)
            if dlg.exec() == QDialog.Accepted:
                ft.name = dlg.get_name(); ft.description = dlg.get_description()
                ft.category = dlg.get_category(); ft.author = dlg.get_author()
                ft.formula = dlg.get_formula(); ft.tags = dlg.get_tags()
                self._engine.update_feature(ft)
                self._ft_detail.load(sel)
                self._set_status("Feature \u300c" + ft.name + "\u300d\u5df2\u66f4\u65b0")
        elif idx == 2:
            st = self._engine.get_strategy(sel)
            if not st: return
            dlg = StrategyDialog(parent=self, record=st)
            if dlg.exec() == QDialog.Accepted:
                st.name = dlg.get_name(); st.description = dlg.get_description()
                st.author = dlg.get_author(); st.tags = dlg.get_tags()
                self._engine.update_strategy(st)
                self._st_detail.load(sel)
                self._set_status("Strategy \u300c" + st.name + "\u300d\u5df2\u66f4\u65b0")
        elif idx == 3:
            ml = self._engine.get_model(sel)
            if not ml: return
            dlg = ModelDialog(parent=self, record=ml)
            if dlg.exec() == QDialog.Accepted:
                ml.name = dlg.get_name(); ml.description = dlg.get_description()
                ml.model_type = dlg.get_model_type(); ml.framework = dlg.get_framework()
                ml.author = dlg.get_author(); ml.tags = dlg.get_tags()
                self._engine.update_model(ml)
                self._ml_detail.load(sel)
                self._set_status("Model \u300c" + ml.name + "\u300d\u5df2\u66f4\u65b0")

    def _on_delete(self):
        idx = self._current_tab()
        sel = self._selected_id()
        if not sel: return
        labels   = {0:"Dataset", 1:"Feature", 2:"Strategy", 3:"Model"}
        getters  = {0:self._engine.get_dataset,    1:self._engine.get_feature,
                    2:self._engine.get_strategy,   3:self._engine.get_model}
        deleters = {0:self._engine.delete_dataset,  1:self._engine.delete_feature,
                    2:self._engine.delete_strategy, 3:self._engine.delete_model}
        obj = getters[idx](sel)
        if not obj: return
        if QMessageBox.question(
            self, "\u786e\u8ba4\u5220\u9664",
            "\u5220\u9664 " + labels[idx] + " \u300c" + obj.name + "\u300d\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            deleters[idx](sel)
            self._set_status(labels[idx] + " \u300c" + obj.name + "\u300d\u5df2\u5220\u9664")
            self._refresh_stats()

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw: return
        idx = self._current_tab()
        lists = {0:self._ds_list, 1:self._ft_list,
                 2:self._st_list, 3:self._ml_list}
        lists[idx].set_keyword(kw)
        self._set_status("\u641c\u7d22\u300c" + kw + "\u300d")

    def _on_reset(self):
        self._search_box.clear()
        for lst in (self._ds_list, self._ft_list,
                    self._st_list, self._ml_list):
            lst.set_keyword("")
        self._set_status("\u5c31\u7eea")

    def _on_stats_event(self, _=None):
        self._refresh_stats()

    def _refresh_stats(self):
        s = self._engine.stats()
        self._stats_bar.setText(
            "Dataset: "  + str(s.get("datasets", 0))
            + "    Feature: "  + str(s.get("features", 0))
            + "    Strategy: " + str(s.get("strategies", 0))
            + "    Model: "    + str(s.get("models", 0))
            + "    \u8840\u7f18\u8282\u70b9: " + str(s.get("lineage_nodes", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
