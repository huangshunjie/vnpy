"""
capital_allocation_ai/ui/dashboard_tab.py  (Phase 5)

DashboardTab — Capital Allocation AI 总览面板。
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_MAV      = "#cba6f7"
_CYN      = "#89dceb"
_TITLE    = "Capital Allocation Intelligence System"


def _panel(title: str) -> tuple:
    w = QtWidgets.QWidget()
    w.setStyleSheet(
        f"background: {_PANEL_BG}; border-radius: 6px;"
        f" border: 1px solid {_BORDER};")
    v = QtWidgets.QVBoxLayout(w)
    v.setContentsMargins(12, 8, 12, 8)
    v.setSpacing(4)
    if title:
        lbl = QtWidgets.QLabel(title)
        lbl.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(lbl)
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        v.addWidget(sep)
    return w, v


def _kv_row(v_layout, key: str, attr: str,
            store: dict, key_w: int = 80) -> QtWidgets.QLabel:
    row = QtWidgets.QWidget()
    row.setStyleSheet("border: none;")
    h = QtWidgets.QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(4)
    k = QtWidgets.QLabel(key)
    k.setFixedWidth(key_w)
    k.setStyleSheet(f"color: {_MUT}; font-size: 11px; border: none;")
    lbl = QtWidgets.QLabel("---")
    lbl.setStyleSheet(f"color: {_FG}; font-size: 12px; border: none;")
    h.addWidget(k)
    h.addWidget(lbl, stretch=1)
    v_layout.addWidget(row)
    store[attr] = lbl
    return lbl


class DashboardTab(QtWidgets.QWidget):
    """Capital Allocation AI 总览面板（Phase 5）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._score_rows: list = []
        self._alloc_lbls: dict = {}
        self._risk_lbls:  dict = {}
        self._rb_lbls:    dict = {}
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_header())
        root.addWidget(self._build_body(), stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_header(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(52)
        w.setStyleSheet(
            f"background: #11111b; border-radius: 6px;"
            f" border: 1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 0, 16, 0)
        title = QtWidgets.QLabel(_TITLE)
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 14px; font-weight: bold; border: none;")
        h.addWidget(title)
        h.addStretch()
        self._phase_lbl  = QtWidgets.QLabel("Phase: 5")
        self._status_lbl = QtWidgets.QLabel("Engine: ---")
        self._uptime_lbl = QtWidgets.QLabel("Uptime: 0s")
        for lbl in (self._phase_lbl, self._status_lbl, self._uptime_lbl):
            lbl.setStyleSheet(
                f"color: {_MUT}; font-size: 11px; padding: 0 8px; border: none;")
            h.addWidget(lbl)
        return w

    def _build_body(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(self._build_scoring_panel(),    stretch=3)
        h.addWidget(self._build_allocation_panel(), stretch=3)
        h.addWidget(self._build_risk_panel(),       stretch=2)
        h.addWidget(self._build_rebalance_panel(),  stretch=2)
        return w

    def _build_scoring_panel(self) -> QtWidgets.QWidget:
        w, v = _panel("Alpha 评分 Top-10")
        for i in range(10):
            rw = QtWidgets.QWidget()
            rw.setStyleSheet("border: none;")
            rh = QtWidgets.QHBoxLayout(rw)
            rh.setContentsMargins(0, 0, 0, 0)
            rh.setSpacing(4)
            rn = QtWidgets.QLabel(f"{i+1:2d}.")
            rn.setFixedWidth(22)
            rn.setStyleSheet(f"color: {_MUT}; font-size: 11px; border: none;")
            id_l = QtWidgets.QLabel("---")
            id_l.setFixedWidth(90)
            id_l.setStyleSheet(f"color: {_MAV}; font-size: 11px; border: none;")
            sc_l = QtWidgets.QLabel("0.0000")
            sc_l.setStyleSheet(f"color: {_FG}; font-size: 11px; border: none;")
            br_l = QtWidgets.QLabel("")
            br_l.setStyleSheet(
                f"color: {_GRN}; font-size: 10px; border: none;"
                f" font-family: monospace;")
            rh.addWidget(rn); rh.addWidget(id_l)
            rh.addWidget(sc_l); rh.addWidget(br_l, stretch=1)
            v.addWidget(rw)
            self._score_rows.append((id_l, sc_l, br_l))
        v.addStretch()
        return w

    def _build_allocation_panel(self) -> QtWidgets.QWidget:
        w, v = _panel("资金分配摘要")
        for key, attr in [
            ("总资金",     "_d_capital"),
            ("活跃 Alpha", "_d_active"),
            ("集中度 HHI", "_d_hhi"),
            ("有效 N",     "_d_eff_n"),
            ("换手率",     "_d_turnover"),
            ("信号数",     "_d_signals"),
        ]:
            _kv_row(v, key, attr, self._alloc_lbls)
        v.addStretch()
        return w

    def _build_risk_panel(self) -> QtWidgets.QWidget:
        w, v = _panel("风险状态")
        for key, attr in [
            ("组合 VaR",   "_r_var"),
            ("组合 DD",    "_r_dd"),
            ("组合 Beta",  "_r_beta"),
            ("违规 Alpha", "_r_breach"),
            ("风险信号",   "_r_signals"),
            ("Vol 上限",   "_r_vol_lim"),
        ]:
            _kv_row(v, key, attr, self._risk_lbls, key_w=72)
        v.addStretch()
        return w

    def _build_rebalance_panel(self) -> QtWidgets.QWidget:
        w, v = _panel("再平衡状态")
        for key, attr in [
            ("执行次数", "_rb_count"),
            ("漂移分",   "_rb_drift"),
            ("交易笔数", "_rb_trades"),
            ("预估成本", "_rb_cost"),
            ("成本有效", "_rb_ok"),
            ("上次时间", "_rb_last"),
        ]:
            _kv_row(v, key, attr, self._rb_lbls, key_w=72)
        v.addStretch()
        return w

    def _build_action_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)

        def _btn(label, color, slot):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 3px;"
                f" padding: 4px 16px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b

        h.addWidget(_btn("★ 全链路计算  Full Pipeline", _MAV, self._on_full_pipeline))
        h.addWidget(_btn("⚡ 自动再平衡  Auto Rebalance", _CYN, self._on_auto_rebalance))
        h.addStretch()
        h.addWidget(_btn("刷新 Refresh", _MUT, self.refresh))
        return bar

    def refresh(self) -> None:
        if self._engine is None:
            return
        summ = self._engine.get_summary()
        self._update_header(summ)
        self._update_scoring()
        self._update_allocation()
        self._update_risk()
        self._update_rebalance(summ)

    def _on_full_pipeline(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "未初始化", "请先启动引擎。")
            return
        self._engine.calculate_allocation()
        self._engine.evaluate_risk()
        self.refresh()

    def _on_auto_rebalance(self) -> None:
        if self._engine is None:
            return
        plan = self._engine.auto_rebalance()
        if plan is None:
            QtWidgets.QMessageBox.information(
                self, "自动再平衡", "当前无需再平衡，所有条件均未触发。")
        self.refresh()

    def _update_header(self, summ: dict) -> None:
        self._phase_lbl.setText(f"Phase: {summ.get('phase', '?')}")
        self._uptime_lbl.setText(f"Uptime: {summ.get('uptime', 0):.0f}s")
        self._status_lbl.setText("Engine: Running")
        self._status_lbl.setStyleSheet(
            f"color: {_GRN}; font-size: 11px; padding: 0 8px; border: none;")

    def _update_scoring(self) -> None:
        if self._engine is None:
            return
        ranking = self._engine.scoring_engine.get_ranking(top_n=10)
        max_sc   = max((s.capital_score for s in ranking), default=1.0) or 1.0
        for i, (id_l, sc_l, br_l) in enumerate(self._score_rows):
            if i < len(ranking):
                sc     = ranking[i]
                bar_n  = int(sc.capital_score / max_sc * 12)
                bar    = "█" * bar_n + "░" * (12 - bar_n)
                color  = (_GRN if sc.capital_score > 0.5
                          else _YLW if sc.capital_score > 0.3 else _RED)
                id_l.setText(sc.alpha_id[-8:])
                sc_l.setText(f"{sc.capital_score:.4f}")
                sc_l.setStyleSheet(
                    f"color: {color}; font-size: 11px; border: none;")
                br_l.setText(bar)
                br_l.setStyleSheet(
                    f"color: {color}; font-size: 10px; border: none;"
                    f" font-family: monospace;")
            else:
                id_l.setText("---"); sc_l.setText("---"); br_l.setText("")

    def _update_allocation(self) -> None:
        snap = self._engine.allocation_engine.get_latest_snapshot()
        al   = self._alloc_lbls
        if snap:
            cap = snap.total_capital
            al["_d_capital"].setText(
                f"¥{cap/1_000_000:.1f}M" if cap >= 1_000_000 else f"¥{cap:,.0f}")
            al["_d_active"].setText(str(snap.n_active))
            al["_d_hhi"].setText(f"{snap.concentration:.4f}")
            al["_d_eff_n"].setText(f"{snap.effective_n:.1f}")
            al["_d_turnover"].setText(f"{snap.turnover:.4f}")
            sigs = len(snap.signals)
            al["_d_signals"].setText(str(sigs))
            al["_d_signals"].setStyleSheet(
                f"color: {_YLW if sigs > 0 else _FG}; font-size: 12px; border: none;")
        else:
            for lbl in al.values():
                lbl.setText("---")

    def _update_risk(self) -> None:
        snap = self._engine.risk_budget_engine.get_latest_snapshot()
        rl   = self._risk_lbls
        lims = self._engine.risk_budget_engine.get_limits()
        if snap:
            rl["_r_var"].setText(f"{snap.portfolio_var:.4f}")
            rl["_r_var"].setStyleSheet(
                f"color: {_RED if snap.portfolio_var > 0.02 else _GRN};"
                f" font-size: 12px; border: none;")
            rl["_r_dd"].setText(f"{snap.portfolio_dd:.4f}")
            rl["_r_dd"].setStyleSheet(
                f"color: {_RED if snap.portfolio_dd > 0.12 else _GRN};"
                f" font-size: 12px; border: none;")
            rl["_r_beta"].setText(f"{snap.portfolio_beta:.4f}")
            rl["_r_breach"].setText(str(snap.n_breached))
            rl["_r_breach"].setStyleSheet(
                f"color: {_RED if snap.n_breached > 0 else _GRN};"
                f" font-size: 12px; border: none;")
            rl["_r_signals"].setText(str(len(snap.adjust_signals)))
        else:
            for k in ("_r_var", "_r_dd", "_r_beta", "_r_breach", "_r_signals"):
                rl[k].setText("---")
        rl["_r_vol_lim"].setText(f"{lims.get('vol_limit', 0.30):.2f}")

    def _update_rebalance(self, summ: dict) -> None:
        plan = self._engine.rebalance_engine.get_latest_plan()
        rb   = self._rb_lbls
        rs   = summ.get("rebalance", {})
        rb["_rb_count"].setText(str(rs.get("rebalances", 0)))
        drift = rs.get("latest_drift", 0.0)
        rb["_rb_drift"].setText(f"{drift:.4f}")
        rb["_rb_drift"].setStyleSheet(
            f"color: {_RED if drift > 0.1 else _YLW if drift > 0.05 else _GRN};"
            f" font-size: 12px; border: none;")
        rb["_rb_trades"].setText(str(rs.get("latest_trades", 0)))
        cost = rs.get("latest_cost", 0.0)
        rb["_rb_cost"].setText(f"¥{cost:,.0f}" if cost else "---")
        if plan is not None:
            ok_c = _GRN if plan.is_cost_effective else _RED
            rb["_rb_ok"].setText("✓ YES" if plan.is_cost_effective else "✗ NO")
            rb["_rb_ok"].setStyleSheet(
                f"color: {ok_c}; font-size: 12px; border: none;")
        else:
            rb["_rb_ok"].setText("---")
        last_at = rs.get("last_at")
        rb["_rb_last"].setText(str(last_at)[:16] if last_at else "Never")
