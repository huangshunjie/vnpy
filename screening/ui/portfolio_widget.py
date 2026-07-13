"""
screening/ui/portfolio_widget.py
Portfolio Widget + Template Manager — Phase 8
"""
from __future__ import annotations
import uuid
from typing import Optional, List
from vnpy.trader.ui import QtWidgets, QtCore
from ..engine.portfolio_engine import PortfolioWeightResult

_PANEL="#181825"; _PANEL2="#11111b"; _BORDER="#45475a"; _FG="#cdd6f4"
_MUT="#6c7086"; _MAV="#cba6f7"; _GRN="#a6e3a1"; _BLU="#89b4fa"
_YLW="#f9e2af"; _RED="#f38ba8"; _ORG="#fab387"
_LABEL=f"color:{_FG};font-size:11px;"
_INPUT=(f"background:{_PANEL2};color:{_FG};border:1px solid {_BORDER};"
        f"border-radius:3px;padding:3px 6px;font-size:11px;")
_SECTION=f"color:{_MAV};font-size:11px;font-weight:bold;"

_HDR = ["代码", "权重", "综合评分", "百分位"]
_TABLE_STYLE = f"""
QTableWidget{{background:{_PANEL2};color:{_FG};gridline-color:{_BORDER};
font-size:11px;border:none;}}
QHeaderView::section{{background:#313244;color:{_YLW};font-size:11px;
font-weight:bold;border:1px solid {_BORDER};padding:4px;}}
QTableWidget::item:selected{{background:#45475a;}}"""

def _sb(text, color=_MUT):
    b=QtWidgets.QPushButton(text)
    b.setStyleSheet(
        f"QPushButton{{background:#313244;color:{color};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:3px 10px;font-size:11px;}}"
        f"QPushButton:hover{{background:#45475a;}}")
    return b


class PortfolioWidget(QtWidgets.QWidget):
    """组合权重 + 模板管理面板（Phase 8）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._current_result: Optional[PortfolioWeightResult] = None
        self._init_ui()

    def _sep(self):
        s=QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};"); return s

    def _sec(self, t):
        l=QtWidgets.QLabel(t); l.setStyleSheet(_SECTION); return l

    def _init_ui(self):
        self.setStyleSheet(f"background:{_PANEL};")
        root=QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12,12,12,12); root.setSpacing(8)

        t=QtWidgets.QLabel("Portfolio  组合权重")
        t.setStyleSheet(f"color:{_MAV};font-size:13px;font-weight:bold;")
        root.addWidget(t); root.addWidget(self._sep())

        # ── 权重方式 ──────────────────────────────────────────────────
        root.addWidget(self._sec("权重方式"))
        mr=QtWidgets.QHBoxLayout()
        self._method_combo=QtWidgets.QComboBox()
        self._method_combo.setStyleSheet(_INPUT); self._method_combo.setFixedWidth(140)
        for v,lbl in [("equal","等权"), ("inv_vol","波动率倒数"), ("score","评分加权")]:
            self._method_combo.addItem(lbl, v)
        mr.addWidget(QtWidgets.QLabel("方式:", styleSheet=_LABEL))
        mr.addWidget(self._method_combo)
        mr.addWidget(QtWidgets.QLabel("单票上限:", styleSheet=_LABEL))
        self._cap_spin=QtWidgets.QDoubleSpinBox()
        self._cap_spin.setRange(0.0,1.0); self._cap_spin.setSingleStep(0.01)
        self._cap_spin.setDecimals(2); self._cap_spin.setValue(0.10)
        self._cap_spin.setSuffix("  (0=不限)"); self._cap_spin.setFixedWidth(120)
        self._cap_spin.setStyleSheet(_INPUT)
        mr.addWidget(self._cap_spin); mr.addStretch(); root.addLayout(mr)

        br=QtWidgets.QHBoxLayout()
        bg=_sb("生成权重", _MAV); bg.clicked.connect(self._on_generate)
        bx=_sb("导出CSV", _GRN); bx.clicked.connect(self._on_export)
        br.addWidget(bg); br.addWidget(bx); br.addStretch(); root.addLayout(br)

        # ── 权重表格 ──────────────────────────────────────────────────
        root.addWidget(self._sep()); root.addWidget(self._sec("权重明细"))
        self._table=QtWidgets.QTableWidget(0, len(_HDR))
        self._table.setHorizontalHeaderLabels(_HDR)
        self._table.setStyleSheet(_TABLE_STYLE)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        root.addWidget(self._table)

        root.addWidget(self._sep())

        # ── 模板管理 ──────────────────────────────────────────────────
        root.addWidget(self._sec("模板管理"))
        trow=QtWidgets.QHBoxLayout()
        trow.addWidget(QtWidgets.QLabel("模板名:", styleSheet=_LABEL))
        self._tname=QtWidgets.QLineEdit("")
        self._tname.setStyleSheet(_INPUT); self._tname.setPlaceholderText("输入模板名称")
        trow.addWidget(self._tname, stretch=1); root.addLayout(trow)

        trow2=QtWidgets.QHBoxLayout()
        bs=_sb("保存模板", _BLU); bs.clicked.connect(self._on_save_template)
        bl=_sb("加载模板", _ORG); bl.clicked.connect(self._on_load_template)
        bd=_sb("删除模板", _RED); bd.clicked.connect(self._on_delete_template)
        for b in [bs, bl, bd]: trow2.addWidget(b)
        trow2.addStretch(); root.addLayout(trow2)

        # 模板列表
        self._tmpl_list=QtWidgets.QListWidget()
        self._tmpl_list.setStyleSheet(
            f"QListWidget{{background:{_PANEL2};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;font-size:11px;}}"
            f"QListWidget::item:selected{{background:#45475a;}}")
        self._tmpl_list.setMaximumHeight(90)
        self._tmpl_list.itemClicked.connect(self._on_tmpl_clicked)
        root.addWidget(self._tmpl_list)
        self._refresh_template_list()

        self._sl=QtWidgets.QLabel("")
        self._sl.setStyleSheet(f"color:{_MUT};font-size:10px;")
        root.addWidget(self._sl); root.addStretch()

    # ── 权重生成 ──────────────────────────────────────────────────────

    def _on_generate(self):
        if not self._engine:
            self._set_st("引擎未连接"); return
        method = self._method_combo.currentData()
        cap = self._cap_spin.value()
        self._engine.portfolio_bridge.set_method(method)
        self._engine.portfolio_bridge.set_max_single_weight(cap)

        sr = self._engine.scoring_engine.get_last_result()
        if not sr or not sr.stocks:
            self._set_st("请先运行选股流程"); return

        symbols = [s.symbol for s in sr.stocks if s.passed_risk_filter]
        scores  = {s.symbol: s.composite_score for s in sr.stocks}
        result  = self._engine.portfolio_bridge.generate_portfolio(symbols, scores)
        if result:
            self.update_result(result, sr)
        else:
            self._set_st("权重生成失败")

    def _on_export(self):
        if not self._current_result:
            self._set_st("无数据"); return
        import csv, os
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出组合权重", "portfolio_weights.csv", "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w=csv.writer(f); w.writerow(["代码","权重","评分"])
                for sym, wgt in sorted(
                    self._current_result.weights.items(),
                    key=lambda x: x[1], reverse=True
                ):
                    w.writerow([sym, f"{wgt:.4f}",
                                 f"{self._current_result.scores.get(sym,0):.2f}"])
            self._set_st(f"已导出：{os.path.basename(path)}", _GRN)
        except Exception as e:
            self._set_st(f"导出失败：{e}", _RED)

    # ── 模板操作 ──────────────────────────────────────────────────────

    def _on_save_template(self):
        if not self._engine: return
        name = self._tname.text().strip()
        if not name:
            self._set_st("请输入模板名称", _YLW); return
        try:
            from ..model.template import ScreeningTemplate
            from ..constant import TemplateCategory

            uc = (self._engine.universe_engine.get_config().to_dict()
                  if self._engine.universe_engine else {})
            ct = (self._engine.condition_engine.get_tree().to_dict()
                  if self._engine.condition_engine and
                  self._engine.condition_engine.get_tree() else {})
            fc = (self._engine.factor_rank_engine.get_config().to_dict()
                  if self._engine.factor_rank_engine else {})

            tmpl = ScreeningTemplate(
                template_id=str(uuid.uuid4())[:12],
                name=name,
                category=TemplateCategory.CUSTOM,
                universe_config=uc,
                condition_tree=ct,
                factor_config=fc,
                portfolio_config={"method": self._method_combo.currentData(),
                                  "cap": self._cap_spin.value()},
            )
            self._engine.repository.save_template(tmpl)
            self._set_st(f"模板已保存：{name}", _GRN)
            self._refresh_template_list()
        except Exception as e:
            self._set_st(f"保存失败：{e}", _RED)

    def _on_load_template(self):
        name = self._tname.text().strip()
        if not name or not self._engine: return
        try:
            tmpl = self._engine.repository.load_template_by_name(name)
            if not tmpl:
                self._set_st(f"未找到：{name}", _YLW); return
            self._apply_template(tmpl)
            self._set_st(f"模板已加载：{tmpl.name}", _GRN)
        except Exception as e:
            self._set_st(f"加载失败：{e}", _RED)

    def _on_delete_template(self):
        name = self._tname.text().strip()
        if not name or not self._engine: return
        tmpl = self._engine.repository.load_template_by_name(name)
        if tmpl:
            self._engine.repository.delete_template(tmpl.template_id)
            self._set_st(f"已删除：{name}", _MUT)
            self._refresh_template_list()

    def _on_tmpl_clicked(self, item):
        self._tname.setText(item.text())

    def _apply_template(self, tmpl) -> None:
        """将模板配置应用到各子引擎。"""
        if not self._engine: return
        try:
            if tmpl.universe_config:
                from ..model.universe import UniverseConfig
                cfg = UniverseConfig.from_dict(tmpl.universe_config)
                self._engine.universe_engine.set_config(cfg)
        except Exception: pass
        try:
            if tmpl.factor_config:
                from ..model.factor_score import FactorRankConfig
                cfg = FactorRankConfig.from_dict(tmpl.factor_config)
                self._engine.factor_rank_engine.set_config(cfg)
        except Exception: pass
        try:
            pc = tmpl.portfolio_config
            if pc:
                self._engine.portfolio_bridge.set_method(pc.get("method","equal"))
                self._engine.portfolio_bridge.set_max_single_weight(pc.get("cap",0.10))
                idx = self._method_combo.findData(pc.get("method","equal"))
                if idx >= 0: self._method_combo.setCurrentIndex(idx)
                self._cap_spin.setValue(pc.get("cap", 0.10))
        except Exception: pass

    def _refresh_template_list(self):
        self._tmpl_list.clear()
        if not self._engine: return
        try:
            templates = self._engine.repository.list_templates()
            for t in templates:
                self._tmpl_list.addItem(t.name)
        except Exception: pass

    # ── 数据刷新 ──────────────────────────────────────────────────────

    def update_result(self, result: PortfolioWeightResult,
                      screening_result=None) -> None:
        self._current_result = result
        self._table.setSortingEnabled(False)
        items = sorted(result.weights.items(), key=lambda x: x[1], reverse=True)
        self._table.setRowCount(len(items))

        for row, (sym, wgt) in enumerate(items):
            score = result.scores.get(sym, 0.0)
            pct_rank = "--"
            if screening_result:
                for ss in screening_result.stocks:
                    if ss.symbol == sym:
                        pct_rank = f"{ss.percentile:.1%}"
                        break

            for col, val in enumerate([sym, f"{wgt:.2%}",
                                         f"{score:.2f}", pct_rank]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 1:
                    bar_width = int(wgt * 200)
                    item.setToolTip(f"{'█' * bar_width} {wgt:.2%}")
                self._table.setItem(row, col, item)

        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()
        method_lbl = self._method_combo.currentText()
        self._set_st(
            f"{method_lbl}  |  {len(items)} 只  |  "
            f"最大权重 {max(result.weights.values(), default=0):.2%}  |  "
            f"{str(result.generated_at)[:19]}", _MAV
        )

    def _set_st(self, msg, color=_MUT):
        self._sl.setText(msg)
        self._sl.setStyleSheet(f"color:{color};font-size:10px;")
