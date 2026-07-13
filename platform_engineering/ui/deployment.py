"""
platform_engineering/ui/deployment.py
DeploymentTab — Phase 4
部署列表 + 生命周期操作 + 版本历史 + 详情面板
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QTabWidget, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QLineEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QTextBrowser, QMenu, QMessageBox,
    QTextEdit,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

from ..constant import DeployStage, DeployAction
from ..model.deployment import DeploymentRecord, DeployVersion

STAGE_COLOR = {
    DeployStage.RESEARCH:      "#8c8c8c",
    DeployStage.VALIDATION:    "#1890ff",
    DeployStage.APPROVAL:      "#faad14",
    DeployStage.PAPER_TRADING: "#722ed1",
    DeployStage.PRODUCTION:    "#52c41a",
    DeployStage.PAUSED:        "#fa8c16",
    DeployStage.ROLLED_BACK:   "#ff4d4f",
    DeployStage.RETIRED:       "#d9d9d9",
}
STAGE_ICON = {
    DeployStage.RESEARCH:      "🔬",
    DeployStage.VALIDATION:    "🧪",
    DeployStage.APPROVAL:      "⏳",
    DeployStage.PAPER_TRADING: "📋",
    DeployStage.PRODUCTION:    "🚀",
    DeployStage.PAUSED:        "⏸",
    DeployStage.ROLLED_BACK:   "↩",
    DeployStage.RETIRED:       "🗄",
}
ROLE_ID = Qt.UserRole


class CreateDeployDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u521b\u5efa\u90e8\u7f72")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u90e8\u7f72\u4fe1\u606f")
        form = QFormLayout(grp)
        self._sid  = QLineEdit(); self._sid.setPlaceholderText("STR-001")
        form.addRow("\u7b56\u7565 ID *", self._sid)
        self._name = QLineEdit(); self._name.setPlaceholderText("\u7b56\u7565\u540d\u79f0")
        form.addRow("\u7b56\u7565\u540d\u79f0 *", self._name)
        self._creator = QLineEdit()
        form.addRow("\u521b\u5efa\u4eba", self._creator)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("tag1,tag2")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        ng = QGroupBox("\u5907\u6ce8")
        nl = QVBoxLayout(ng)
        self._note = QTextEdit(); self._note.setFixedHeight(60)
        nl.addWidget(self._note)
        root.addWidget(ng)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u521b\u5efa")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._sid.text().strip():  self._sid.setFocus();  return
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def get_strategy_id(self)   -> str: return self._sid.text().strip()
    def get_strategy_name(self) -> str: return self._name.text().strip()
    def get_created_by(self)    -> str: return self._creator.text().strip()
    def get_tags(self):
        raw = self._tags.text().strip()
        return [t.strip() for t in raw.split(",") if t.strip()] if raw else []
    def get_note(self) -> str: return self._note.toPlainText().strip()


class AdvanceStageDialog(QDialog):
    def __init__(self, current: DeployStage, allowed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u63a8\u8fdb\u9636\u6bb5")
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)
        form = QFormLayout()
        lbl = QLabel(current.value.upper())
        lbl.setStyleSheet(
            f"color:{STAGE_COLOR.get(current,'#1890ff')};"
            "font-weight:bold;")
        form.addRow("\u5f53\u524d\u9636\u6bb5:", lbl)
        self._combo = QComboBox()
        for s in allowed:
            self._combo.addItem(
                STAGE_ICON.get(s,"") + "  " + s.value.upper(), s)
        form.addRow("\u76ee\u6807\u9636\u6bb5 *", self._combo)
        self._operator = QLineEdit()
        form.addRow("\u64cd\u4f5c\u4eba", self._operator)
        root.addLayout(form)
        ng = QGroupBox("\u5907\u6ce8")
        nl = QVBoxLayout(ng)
        self._note = QTextEdit(); self._note.setFixedHeight(60)
        nl.addWidget(self._note)
        root.addWidget(ng)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4\u63a8\u8fdb")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def get_stage(self)    -> DeployStage: return self._combo.currentData()
    def get_operator(self) -> str:         return self._operator.text().strip()
    def get_note(self)     -> str:         return self._note.toPlainText().strip()


class ApproveDialog(QDialog):
    def __init__(self, approve: bool = True, parent=None):
        super().__init__(parent)
        self._approve = approve
        self.setWindowTitle(
            "\u5ba1\u6279\u901a\u8fc7" if approve else "\u62d2\u7edd\u5ba1\u6279")
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._approver = QLineEdit()
        form.addRow("\u5ba1\u6279\u4eba *", self._approver)
        root.addLayout(form)
        ng = QGroupBox("\u5907\u6ce8" + ("" if approve else " (\u62d2\u7edd\u539f\u56e0)"))
        nl = QVBoxLayout(ng)
        self._note = QTextEdit(); self._note.setFixedHeight(60)
        nl.addWidget(self._note)
        root.addWidget(ng)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_lbl = "\u786e\u8ba4\u901a\u8fc7" if approve else "\u786e\u8ba4\u62d2\u7edd"
        btns.button(QDialogButtonBox.Ok).setText(ok_lbl)
        if not approve:
            btns.button(QDialogButtonBox.Ok).setStyleSheet(
                "background:#ff4d4f;color:#fff;border-radius:4px;")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._approver.text().strip():
            self._approver.setFocus(); return
        self.accept()

    def get_approver(self) -> str: return self._approver.text().strip()
    def get_note(self)     -> str: return self._note.toPlainText().strip()


class DeployList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._stage_filter = None
        self._on_select_cb = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new = QPushButton("\u2795 \u65b0\u5efa\u90e8\u7f72")
        self._btn_new.setFixedHeight(26)
        self._btn_new.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_new.clicked.connect(self._on_new)
        tb.addWidget(self._btn_new)
        self._stage_combo = QComboBox(); self._stage_combo.setFixedHeight(26)
        self._stage_combo.addItem("\u5168\u90e8\u9636\u6bb5", None)
        for s in DeployStage:
            self._stage_combo.addItem(STAGE_ICON.get(s,"")+" "+s.value, s)
        self._stage_combo.currentIndexChanged.connect(self._on_filter)
        tb.addWidget(self._stage_combo, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\u641c\u7d22\u7b56\u7565\u540d")
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._search)
        root.addLayout(tb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u7b56\u7565\u540d\u79f0","\u9636\u6bb5","\u7248\u672c","\u66f4\u65b0\u65f6\u95f4"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def set_select_callback(self, cb): self._on_select_cb = cb

    def refresh(self):
        if not self._engine: return
        kw    = self._search.text().strip().lower()
        items = self._engine.deployment.list_deployments(stage=self._stage_filter)
        if kw:
            items = [d for d in items
                     if kw in d.strategy_name.lower()
                     or kw in d.strategy_id.lower()]
        self._table.setRowCount(0)
        for d in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(d.strategy_name))
            color = STAGE_COLOR.get(d.current_stage, "#8c8c8c")
            icon  = STAGE_ICON.get(d.current_stage, "")
            si = QTableWidgetItem(icon+" "+d.current_stage.value)
            si.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 1, si)
            frozen_lbl = " \U0001f512" if d.is_frozen else ""
            self._table.setItem(r, 2,
                QTableWidgetItem(d.current_version[:8]+frozen_lbl))
            self._table.setItem(r, 3,
                QTableWidgetItem(d.updated_at.strftime("%m-%d %H:%M")))
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, d.deploy_id)

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None

    def _on_filter(self, _):
        self._stage_filter = self._stage_combo.currentData(); self.refresh()

    def _on_click(self, item):
        if self._on_select_cb:
            self._on_select_cb(item.data(ROLE_ID))

    def _on_new(self):
        if not self._engine: return
        dlg = CreateDeployDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.deployment.create_deployment(
                strategy_id=dlg.get_strategy_id(),
                strategy_name=dlg.get_strategy_name(),
                created_by=dlg.get_created_by(),
                tags=dlg.get_tags(), note=dlg.get_note())
            self.refresh()

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        did = item.data(ROLE_ID)
        rec = self._engine.deployment.get_deployment(did)
        if not rec: return
        menu = QMenu(self)
        a_sub  = menu.addAction("\U0001f4e4  \u63d0\u4ea4\u5ba1\u6279")
        a_app  = menu.addAction("\u2705  \u5ba1\u6279\u901a\u8fc7")
        a_rej  = menu.addAction("\u274c  \u62d2\u7edd\u5ba1\u6279")
        menu.addSeparator()
        a_frz  = menu.addAction(
            "\U0001f513  \u89e3\u51bb\u7ed3" if rec.is_frozen
            else "\U0001f512  \u51bb\u7ed3")
        act = menu.exec(self._table.viewport().mapToGlobal(pos))
        de = self._engine.deployment
        try:
            if act == a_sub:
                de.submit_for_approval(did)
            elif act == a_app:
                dlg = ApproveDialog(True, self)
                if dlg.exec() == QDialog.Accepted:
                    de.approve(did, dlg.get_approver(), dlg.get_note())
            elif act == a_rej:
                dlg = ApproveDialog(False, self)
                if dlg.exec() == QDialog.Accepted:
                    de.reject(did, dlg.get_approver(), dlg.get_note())
            elif act == a_frz:
                de.unfreeze(did) if rec.is_frozen else de.freeze(did)
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "\u9519\u8bef", str(e))
        self.refresh()
        if self._on_select_cb: self._on_select_cb(did)


class DetailPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine    = engine
        self._deploy_id = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 0, 0, 0); root.setSpacing(8)
        hdr = QHBoxLayout()
        self._title = QLabel("\u8bf7\u9009\u62e9\u90e8\u7f72\u8bb0\u5f55")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._stage_badge = QLabel("")
        self._stage_badge.setStyleSheet(
            "font-size:12px;padding:2px 10px;border-radius:10px;")
        hdr.addWidget(self._stage_badge)
        root.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)

        ab = QHBoxLayout(); ab.setSpacing(6)
        self._btn_advance = QPushButton("\u27a1\ufe0f  \u63a8\u8fdb\u9636\u6bb5")
        self._btn_advance.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_submit = QPushButton("\U0001f4e4  \u63d0\u4ea4\u5ba1\u6279")
        self._btn_approve = QPushButton("\u2705  \u5ba1\u6279\u901a\u8fc7")
        self._btn_approve.setStyleSheet(
            "background:#52c41a;color:#fff;border-radius:4px;border:none;")
        self._btn_reject = QPushButton("\u274c  \u62d2\u7edd")
        self._btn_reject.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_freeze = QPushButton("\U0001f512  \u51bb\u7ed3")
        for b in (self._btn_advance, self._btn_submit,
                  self._btn_approve, self._btn_reject, self._btn_freeze):
            b.setFixedHeight(28); ab.addWidget(b)
        ab.addStretch(); root.addLayout(ab)

        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        self._info.setFixedHeight(200)
        root.addWidget(self._info)

        vg = QGroupBox("\u7248\u672c\u5386\u53f2")
        vl = QVBoxLayout(vg)
        self._ver_table = QTableWidget(0, 4)
        self._ver_table.setHorizontalHeaderLabels([
            "\u7248\u672c\u53f7","\u9636\u6bb5","\u5907\u6ce8","\u65f6\u95f4"])
        self._ver_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ver_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ver_table.setAlternatingRowColors(True)
        self._ver_table.verticalHeader().setVisible(False)
        self._ver_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._ver_table.customContextMenuRequested.connect(self._on_ver_ctx)
        vl.addWidget(self._ver_table)
        root.addWidget(vg, 1)

        self._btn_advance.clicked.connect(self._on_advance)
        self._btn_submit.clicked.connect(self._on_submit)
        self._btn_approve.clicked.connect(self._on_approve)
        self._btn_reject.clicked.connect(self._on_reject)
        self._btn_freeze.clicked.connect(self._on_freeze)

    def load(self, deploy_id: str):
        self._deploy_id = deploy_id
        rec = self._engine.deployment.get_deployment(deploy_id)
        if rec: self._render(rec)

    def _render(self, rec):
        color = STAGE_COLOR.get(rec.current_stage, "#1890ff")
        icon  = STAGE_ICON.get(rec.current_stage, "")
        self._title.setText(rec.strategy_name)
        self._bar.setStyleSheet(f"background:{color};border-radius:2px;")
        self._stage_badge.setText(icon+" "+rec.current_stage.value.upper())
        self._stage_badge.setStyleSheet(
            f"font-size:12px;padding:2px 10px;border-radius:10px;"
            f"background:{color}22;color:{color};border:1px solid {color}44;")
        is_frozen   = rec.is_frozen
        is_approval = rec.current_stage == DeployStage.APPROVAL
        self._btn_freeze.setText(
            "\U0001f513  \u89e3\u51bb\u7ed3" if is_frozen else "\U0001f512  \u51bb\u7ed3")
        self._btn_approve.setEnabled(is_approval)
        self._btn_reject.setEnabled(is_approval)
        self._btn_submit.setEnabled(rec.current_stage == DeployStage.VALIDATION)
        self._btn_advance.setEnabled(not is_frozen)
        self._info.setRowCount(0)
        live  = rec.live_at.strftime("%Y-%m-%d %H:%M")     if rec.live_at     else "\u2014"
        pause = rec.paused_at.strftime("%Y-%m-%d %H:%M")   if rec.paused_at   else "\u2014"
        appd  = rec.approved_at.strftime("%Y-%m-%d %H:%M") if rec.approved_at else "\u2014"
        for k, v in [
            ("\u90e8\u7f72 ID",       rec.deploy_id[:16]),
            ("\u7b56\u7565 ID",       rec.strategy_id),
            ("\u521b\u5efa\u4eba",   rec.created_by or "\u2014"),
            ("\u5ba1\u6279\u4eba",   rec.approver or "\u2014"),
            ("\u5ba1\u6279\u65f6\u95f4", appd),
            ("\u4e0a\u7ebf\u65f6\u95f4", live),
            ("\u6682\u505c\u65f6\u95f4", pause),
            ("\u5df2\u51bb\u7ed3",   "\u662f" if is_frozen else "\u5426"),
            ("\u7248\u672c\u6570",   str(len(rec.versions))),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#8c8c8c")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._ver_table.setRowCount(0)
        for ver in reversed(rec.versions):
            r = self._ver_table.rowCount(); self._ver_table.insertRow(r)
            self._ver_table.setItem(r, 0, QTableWidgetItem(ver.version_tag))
            sc = STAGE_COLOR.get(ver.stage, "#8c8c8c")
            si = QTableWidgetItem(ver.stage.value)
            si.setForeground(QBrush(QColor(sc)))
            self._ver_table.setItem(r, 1, si)
            self._ver_table.setItem(r, 2, QTableWidgetItem(ver.note))
            self._ver_table.setItem(r, 3,
                QTableWidgetItem(ver.created_at.strftime("%m-%d %H:%M")))
            for c in range(4):
                self._ver_table.item(r, c).setData(ROLE_ID, ver.version_id)

    def _on_ver_ctx(self, pos):
        item = self._ver_table.itemAt(pos)
        if not item or not self._deploy_id: return
        vid  = item.data(ROLE_ID)
        menu = QMenu(self)
        a_rb = menu.addAction("\u21a9  \u56de\u6eda\u5230\u6b64\u7248\u672c")
        if menu.exec(self._ver_table.viewport().mapToGlobal(pos)) == a_rb:
            try:
                self._engine.deployment.rollback_to_version(self._deploy_id, vid)
                self.load(self._deploy_id)
            except Exception as e:
                QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _advance_allowed(self, stage):
        from ..constant import DeployStage as DS
        return {
            DS.RESEARCH:      [DS.VALIDATION],
            DS.PAPER_TRADING: [DS.PRODUCTION, DS.VALIDATION],
            DS.PRODUCTION:    [DS.PAUSED, DS.ROLLED_BACK, DS.RETIRED],
            DS.PAUSED:        [DS.PRODUCTION, DS.ROLLED_BACK, DS.RETIRED],
            DS.ROLLED_BACK:   [DS.RESEARCH],
        }.get(stage, [])

    def _on_advance(self):
        if not self._deploy_id: return
        rec = self._engine.deployment.get_deployment(self._deploy_id)
        if not rec: return
        allowed = self._advance_allowed(rec.current_stage)
        if not allowed:
            QMessageBox.information(
                self, "\u63d0\u793a", "\u5f53\u524d\u9636\u6bb5\u65e0\u53ef\u63a8\u8fdb\u76ee\u6807"); return
        dlg = AdvanceStageDialog(rec.current_stage, allowed, self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._engine.deployment.advance_stage(
                    self._deploy_id, dlg.get_stage(),
                    operator=dlg.get_operator(), note=dlg.get_note())
                self.load(self._deploy_id)
            except ValueError as e:
                QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_submit(self):
        if not self._deploy_id: return
        try:
            self._engine.deployment.submit_for_approval(self._deploy_id)
            self.load(self._deploy_id)
        except ValueError as e:
            QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_approve(self):
        if not self._deploy_id: return
        dlg = ApproveDialog(True, self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._engine.deployment.approve(
                    self._deploy_id, dlg.get_approver(), dlg.get_note())
                self.load(self._deploy_id)
            except ValueError as e:
                QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_reject(self):
        if not self._deploy_id: return
        dlg = ApproveDialog(False, self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._engine.deployment.reject(
                    self._deploy_id, dlg.get_approver(), dlg.get_note())
                self.load(self._deploy_id)
            except ValueError as e:
                QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_freeze(self):
        if not self._deploy_id: return
        rec = self._engine.deployment.get_deployment(self._deploy_id)
        if rec.is_frozen:
            self._engine.deployment.unfreeze(self._deploy_id)
        else:
            self._engine.deployment.freeze(self._deploy_id)
        self.load(self._deploy_id)


class DeploymentTab(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(5_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12); root.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("\U0001f680  Deployment Management")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\U0001f504 \u5237\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        sp = QSplitter(Qt.Horizontal)
        self._deploy_list  = DeployList(self._engine)
        self._detail_panel = DetailPanel(self._engine)
        self._deploy_list.set_select_callback(self._on_selected)
        sp.addWidget(self._deploy_list)
        sp.addWidget(self._detail_panel)
        sp.setSizes([320, 880])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("font-size:11px;color:#6c757d;")
        root.addWidget(self._status)

    def _on_selected(self, deploy_id: str):
        self._detail_panel.load(deploy_id)

    def _refresh(self):
        self._deploy_list.refresh()
        if self._engine:
            s = self._engine.deployment.stats()
            by = s.get("by_stage", {})
            self._stats_lbl.setText(
                f"\u603b\u8ba1: {s.get('total',0)}"
                f"  \u751f\u4ea7: {by.get('production',0)}"
                f"  \u5ba1\u6279\u4e2d: {by.get('approval',0)}"
                f"  \u5df2\u51bb\u7ed3: {s.get('frozen',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
