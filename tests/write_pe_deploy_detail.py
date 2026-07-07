"""write_pe_deploy_detail.py — append DetailPanel + DeploymentTab"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\deployment.py"
)

CODE = '''

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
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u90e8\\u7f72\\u8bb0\\u5f55")
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
        self._btn_advance = QPushButton("\\u27a1\\ufe0f  \\u63a8\\u8fdb\\u9636\\u6bb5")
        self._btn_advance.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_submit = QPushButton("\\U0001f4e4  \\u63d0\\u4ea4\\u5ba1\\u6279")
        self._btn_approve = QPushButton("\\u2705  \\u5ba1\\u6279\\u901a\\u8fc7")
        self._btn_approve.setStyleSheet(
            "background:#52c41a;color:#fff;border-radius:4px;border:none;")
        self._btn_reject = QPushButton("\\u274c  \\u62d2\\u7edd")
        self._btn_reject.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_freeze = QPushButton("\\U0001f512  \\u51bb\\u7ed3")
        for b in (self._btn_advance, self._btn_submit,
                  self._btn_approve, self._btn_reject, self._btn_freeze):
            b.setFixedHeight(28); ab.addWidget(b)
        ab.addStretch(); root.addLayout(ab)

        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        self._info.setFixedHeight(200)
        root.addWidget(self._info)

        vg = QGroupBox("\\u7248\\u672c\\u5386\\u53f2")
        vl = QVBoxLayout(vg)
        self._ver_table = QTableWidget(0, 4)
        self._ver_table.setHorizontalHeaderLabels([
            "\\u7248\\u672c\\u53f7","\\u9636\\u6bb5","\\u5907\\u6ce8","\\u65f6\\u95f4"])
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
            "\\U0001f513  \\u89e3\\u51bb\\u7ed3" if is_frozen else "\\U0001f512  \\u51bb\\u7ed3")
        self._btn_approve.setEnabled(is_approval)
        self._btn_reject.setEnabled(is_approval)
        self._btn_submit.setEnabled(rec.current_stage == DeployStage.VALIDATION)
        self._btn_advance.setEnabled(not is_frozen)
        self._info.setRowCount(0)
        live  = rec.live_at.strftime("%Y-%m-%d %H:%M")     if rec.live_at     else "\\u2014"
        pause = rec.paused_at.strftime("%Y-%m-%d %H:%M")   if rec.paused_at   else "\\u2014"
        appd  = rec.approved_at.strftime("%Y-%m-%d %H:%M") if rec.approved_at else "\\u2014"
        for k, v in [
            ("\\u90e8\\u7f72 ID",       rec.deploy_id[:16]),
            ("\\u7b56\\u7565 ID",       rec.strategy_id),
            ("\\u521b\\u5efa\\u4eba",   rec.created_by or "\\u2014"),
            ("\\u5ba1\\u6279\\u4eba",   rec.approver or "\\u2014"),
            ("\\u5ba1\\u6279\\u65f6\\u95f4", appd),
            ("\\u4e0a\\u7ebf\\u65f6\\u95f4", live),
            ("\\u6682\\u505c\\u65f6\\u95f4", pause),
            ("\\u5df2\\u51bb\\u7ed3",   "\\u662f" if is_frozen else "\\u5426"),
            ("\\u7248\\u672c\\u6570",   str(len(rec.versions))),
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
        a_rb = menu.addAction("\\u21a9  \\u56de\\u6eda\\u5230\\u6b64\\u7248\\u672c")
        if menu.exec(self._ver_table.viewport().mapToGlobal(pos)) == a_rb:
            try:
                self._engine.deployment.rollback_to_version(self._deploy_id, vid)
                self.load(self._deploy_id)
            except Exception as e:
                QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

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
                self, "\\u63d0\\u793a", "\\u5f53\\u524d\\u9636\\u6bb5\\u65e0\\u53ef\\u63a8\\u8fdb\\u76ee\\u6807"); return
        dlg = AdvanceStageDialog(rec.current_stage, allowed, self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._engine.deployment.advance_stage(
                    self._deploy_id, dlg.get_stage(),
                    operator=dlg.get_operator(), note=dlg.get_note())
                self.load(self._deploy_id)
            except ValueError as e:
                QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

    def _on_submit(self):
        if not self._deploy_id: return
        try:
            self._engine.deployment.submit_for_approval(self._deploy_id)
            self.load(self._deploy_id)
        except ValueError as e:
            QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

    def _on_approve(self):
        if not self._deploy_id: return
        dlg = ApproveDialog(True, self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._engine.deployment.approve(
                    self._deploy_id, dlg.get_approver(), dlg.get_note())
                self.load(self._deploy_id)
            except ValueError as e:
                QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

    def _on_reject(self):
        if not self._deploy_id: return
        dlg = ApproveDialog(False, self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._engine.deployment.reject(
                    self._deploy_id, dlg.get_approver(), dlg.get_note())
                self.load(self._deploy_id)
            except ValueError as e:
                QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

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
        title = QLabel("\\U0001f680  Deployment Management")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\\U0001f504 \\u5237\\u65b0")
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

        self._status = QLabel("\\u5c31\\u7eea")
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
                f"\\u603b\\u8ba1: {s.get('total',0)}"
                f"  \\u751f\\u4ea7: {by.get('production',0)}"
                f"  \\u5ba1\\u6279\\u4e2d: {by.get('approval',0)}"
                f"  \\u5df2\\u51bb\\u7ed3: {s.get('frozen',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("DetailPanel+DeploymentTab OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
