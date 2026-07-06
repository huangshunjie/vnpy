"""
cross_market_ai/ui/transfer_tab.py

Phase 3: Alpha Transfer Monitor â€” Alpha è¿ç§»ç›‘æŽ§é¢æ¿ã€‚
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..constant import APP_NAME
from ..engine import CrossMarketEngine
from ..event import EVENT_ALPHA_TRANSFERRED


class TransferTab(QtWidgets.QWidget):
    """Alpha è¿ç§»ç›‘æŽ§é¢æ¿ã€‚"""

    signal_transferred = QtCore.pyqtSignal(dict)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._cm_engine: CrossMarketEngine = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._register_events()

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)
        root.addWidget(self._build_control_panel(), stretch=0)
        right = QtWidgets.QVBoxLayout()
        right.addWidget(self._build_conditions_panel(), stretch=0)
        right.addWidget(self._build_result_table(),     stretch=1)
        right.addWidget(self._build_batch_panel(),      stretch=1)
        rw = QtWidgets.QWidget()
        rw.setLayout(right)
        root.addWidget(rw, stretch=1)

    def _build_control_panel(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setFixedWidth(240)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        lbl = QtWidgets.QLabel("Alpha Transfer Engine")
        lbl.setStyleSheet("font-weight:bold; color:#4fc3f7; font-size:12px;")
        layout.addWidget(lbl)
        layout.addWidget(_hline())

        layout.addWidget(QtWidgets.QLabel("Alpha ç±»åž‹:"))
        self._combo_alpha = QtWidgets.QComboBox()
        self._combo_alpha.addItems([
            "momentum", "mean_reversion", "value", "volatility", "carry"
        ])
        layout.addWidget(self._combo_alpha)

        layout.addWidget(QtWidgets.QLabel("æºå¸‚åœº (è®­ç»ƒ):"))
        self._combo_src = QtWidgets.QComboBox()
        self._combo_src.addItems([
            "equity_cn", "futures_cn", "equity_us", "crypto", "forex", "fixed_income"
        ])
        layout.addWidget(self._combo_src)

        layout.addWidget(QtWidgets.QLabel("ç›®æ ‡å¸‚åœº:"))
        self._combo_dst = QtWidgets.QComboBox()
        self._combo_dst.addItems([
            "futures_cn", "equity_cn", "equity_us", "crypto", "forex", "fixed_income"
        ])
        layout.addWidget(self._combo_dst)

        self._chk_force = QtWidgets.QCheckBox("å¼ºåˆ¶åˆ·æ–°")
        layout.addWidget(self._chk_force)

        btn_single = QtWidgets.QPushButton("â–¶  æ‰§è¡Œè¿ç§»")
        btn_single.setStyleSheet("background:#1565c0; color:white; padding:4px;")
        btn_single.clicked.connect(self._on_transfer_single)
        layout.addWidget(btn_single)

        layout.addWidget(_hline())

        layout.addWidget(QtWidgets.QLabel("æ‰¹é‡è¿ç§» â€” Alpha:"))
        self._combo_batch_alpha = QtWidgets.QComboBox()
        self._combo_batch_alpha.addItems([
            "momentum", "mean_reversion", "value", "volatility", "carry"
        ])
        layout.addWidget(self._combo_batch_alpha)

        layout.addWidget(QtWidgets.QLabel("æ‰¹é‡è¿ç§» â€” æºå¸‚åœº:"))
        self._combo_batch_src = QtWidgets.QComboBox()
        self._combo_batch_src.addItems([
            "equity_cn", "futures_cn", "equity_us", "crypto", "forex", "fixed_income"
        ])
        layout.addWidget(self._combo_batch_src)

        btn_batch = QtWidgets.QPushButton("â–¶â–¶  æ‰¹é‡è¿ç§»æ‰€æœ‰å¸‚åœº")
        btn_batch.setStyleSheet("background:#2e7d32; color:white; padding:4px;")
        btn_batch.clicked.connect(self._on_transfer_batch)
        layout.addWidget(btn_batch)

        layout.addWidget(_hline())
        self._stat_total = _stat_row("æ€»è¿ç§»æ¬¡æ•°")
        self._stat_ok    = _stat_row("æˆåŠŸ")
        self._stat_rej   = _stat_row("æ‹’ç»")
        self._stat_avg   = _stat_row("å¹³å‡Tç³»æ•°")
        for w in [self._stat_total, self._stat_ok, self._stat_rej, self._stat_avg]:
            layout.addWidget(w)

        layout.addStretch()
        return frame

    def _build_conditions_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("è¿ç§»æ¡ä»¶è¯„åˆ† & è¿ç§»ç³»æ•° T")
        layout = QtWidgets.QGridLayout(group)
        layout.setSpacing(8)

        self._lbl_corr   = _metric_label("-")
        self._lbl_regime = _metric_label("-")
        self._lbl_vol    = _metric_label("-")
        self._lbl_liq    = _metric_label("-")
        self._lbl_t      = _metric_label("-")
        self._lbl_conf   = _metric_label("-")

        layout.addWidget(QtWidgets.QLabel("ç›¸å…³æ€§ç¨³å®šæ€§:"),  0, 0)
        layout.addWidget(self._lbl_corr,   0, 1)
        layout.addWidget(QtWidgets.QLabel("Regime ä¸å˜æ€§:"), 0, 2)
        layout.addWidget(self._lbl_regime, 0, 3)
        layout.addWidget(QtWidgets.QLabel("æ³¢åŠ¨çŽ‡æ•æ„Ÿåº¦:"),  1, 0)
        layout.addWidget(self._lbl_vol,    1, 1)
        layout.addWidget(QtWidgets.QLabel("æµåŠ¨æ€§æ•æ„Ÿåº¦:"),  1, 2)
        layout.addWidget(self._lbl_liq,    1, 3)
        layout.addWidget(QtWidgets.QLabel("è¿ç§»ç³»æ•° T:"),    2, 0)
        layout.addWidget(self._lbl_t,      2, 1)
        layout.addWidget(QtWidgets.QLabel("ç½®ä¿¡åº¦:"),        2, 2)
        layout.addWidget(self._lbl_conf,   2, 3)

        self._lbl_conclusion = QtWidgets.QLabel("â€”")
        self._lbl_conclusion.setWordWrap(True)
        self._lbl_conclusion.setStyleSheet(
            "font-size:12px; font-weight:bold; padding:4px;"
        )
        layout.addWidget(QtWidgets.QLabel("è¿ç§»ç»“è®º:"), 3, 0)
        layout.addWidget(self._lbl_conclusion, 3, 1, 1, 3)
        return group

    def _build_result_table(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("è¿ç§»ç»“æžœè¯¦æƒ…")
        layout = QtWidgets.QVBoxLayout(group)
        self._result_table = QtWidgets.QTableWidget(0, 10)
        self._result_table.setHorizontalHeaderLabels([
            "Alpha", "æºå¸‚åœº", "ç›®æ ‡å¸‚åœº",
            "Tç³»æ•°", "IC(src)", "IC(dst)", "ICè¡°å‡çŽ‡",
            "Sharpe(dst)", "volè°ƒæ•´", "å¯è¿ç§»",
        ])
        self._result_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self._result_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._result_table.setAlternatingRowColors(True)
        layout.addWidget(self._result_table)
        return group

    def _build_batch_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("æ‰¹é‡è¿ç§»ç»“æžœ â€” å¯è¿ç§»æ€§æŽ’å")
        layout = QtWidgets.QVBoxLayout(group)
        self._batch_table = QtWidgets.QTableWidget(0, 5)
        self._batch_table.setHorizontalHeaderLabels([
            "ç›®æ ‡å¸‚åœº", "Tç³»æ•°", "ç½®ä¿¡åº¦", "ICè¡°å‡çŽ‡", "å¯è¿ç§»",
        ])
        self._batch_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self._batch_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._batch_table.setMaximumHeight(160)
        layout.addWidget(self._batch_table)
        return group

    # ©¤©¤ ÊÂ¼þ×¢²á ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤

    def _register_events(self) -> None:
        self.signal_transferred.connect(self._on_transfer_event)
        self._event_engine.register(EVENT_ALPHA_TRANSFERRED, self.signal_transferred.emit)

    # ©¤©¤ ²Ûº¯Êý ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤

    def _on_transfer_single(self) -> None:
        alpha_id   = self._combo_alpha.currentText()
        market_src = self._combo_src.currentText()
        market_dst = self._combo_dst.currentText()
        force      = self._chk_force.isChecked()
        result     = self._cm_engine.transfer_alpha(alpha_id, market_src, market_dst,
                                                    force_refresh=force)
        if result.get("status") == "ok":
            self._update_conditions(result["record"])
            self._append_result_row(result["record"])
            self._update_state_labels(result.get("state", {}))

    def _on_transfer_batch(self) -> None:
        alpha_id   = self._combo_batch_alpha.currentText()
        market_src = self._combo_batch_src.currentText()
        result     = self._cm_engine.transfer_alpha_batch(alpha_id, market_src)
        if result.get("status") == "ok":
            records = result.get("records", [])
            self._refresh_batch_table(records)
            for rec in records:
                self._append_result_row(rec)
            self._update_state_labels(result.get("state", {}))

    def _on_transfer_event(self, data: dict) -> None:
        if data.get("status") == "ok" and data.get("record"):
            self._update_conditions(data["record"])

    # ©¤©¤ Ë¢ÐÂÂß¼­ ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤

    def _update_conditions(self, rec: dict) -> None:
        corr   = rec.get("correlation_stability",  0.0)
        regime = rec.get("regime_invariance",      0.0)
        vol    = rec.get("volatility_sensitivity", 0.0)
        liq    = rec.get("liquidity_sensitivity",  0.0)
        t      = rec.get("transfer_coefficient",   0.0)
        conf   = rec.get("confidence", "-")
        ok     = rec.get("is_transferable", False)
        reason = rec.get("rejection_reason", "")

        for lbl, score, inv in [
            (self._lbl_corr,   corr,   False),
            (self._lbl_regime, regime, False),
            (self._lbl_vol,    vol,    True),
            (self._lbl_liq,    liq,    True),
            (self._lbl_t,      t,      False),
        ]:
            lbl.setText(f"{score:.4f}")
            eff = (1.0 - score) if inv else score
            c = "#4caf50" if eff >= 0.6 else "#ff9800" if eff >= 0.35 else "#f44336"
            lbl.setStyleSheet(f"font-size:13px; font-weight:bold; color:{c};")

        self._lbl_conf.setText(conf)
        conf_map = {"HIGH": "#4caf50", "MODERATE": "#ff9800",
                    "LOW": "#ff5722", "REJECT": "#f44336"}
        self._lbl_conf.setStyleSheet(
            f"font-size:13px; font-weight:bold; "
            f"color:{conf_map.get(conf, '#888')};"
        )

        text  = f"?  ¿ÉÇ¨ÒÆ  ({conf})" if ok else f"?  ¾Ü¾øÇ¨ÒÆ£º{reason}"
        color = "#4caf50" if ok else "#f44336"
        self._lbl_conclusion.setText(text)
        self._lbl_conclusion.setStyleSheet(
            f"font-size:12px; font-weight:bold; padding:4px; color:{color};"
        )

    def _append_result_row(self, rec: dict) -> None:
        row = self._result_table.rowCount()
        self._result_table.insertRow(row)
        t      = rec.get("transfer_coefficient", 0.0)
        ic_src = rec.get("expected_ic_src",      0.0)
        ic_dst = rec.get("expected_ic_dst",      0.0)
        ic_dec = rec.get("expected_ic_decay",    0.0)
        sharpe = rec.get("expected_sharpe_dst",  0.0)
        vol_sc = rec.get("vol_scale",            1.0)
        ok     = rec.get("is_transferable",      False)

        for col, (val, score, inv) in enumerate([
            (rec.get("alpha_id",    ""), None,    False),
            (rec.get("market_src",  ""), None,    False),
            (rec.get("market_dst",  ""), None,    False),
            (f"{t:.4f}",               t,      False),
            (f"{ic_src:.5f}",          None,    False),
            (f"{ic_dst:.5f}",          None,    False),
            (f"{ic_dec:.4f}",          1-ic_dec, False),
            (f"{sharpe:.4f}",          None,    False),
            (f"{vol_sc:.4f}",          None,    False),
            ("?" if ok else "?",       None,    False),
        ]):
            item = _cell(val)
            if score is not None:
                c = "#4caf50" if score >= 0.6 else "#ff9800" if score >= 0.35 else "#f44336"
                item.setForeground(QtGui.QColor(c))
            if col == 9:
                item.setForeground(QtGui.QColor("#4caf50" if ok else "#f44336"))
            self._result_table.setItem(row, col, item)
        self._result_table.scrollToBottom()

    def _refresh_batch_table(self, records: list[dict]) -> None:
        sorted_recs = sorted(records,
                             key=lambda r: r.get("transfer_coefficient", 0.0),
                             reverse=True)
        self._batch_table.setRowCount(0)
        conf_map = {"HIGH": "#4caf50", "MODERATE": "#ff9800",
                    "LOW": "#ff5722", "REJECT": "#f44336"}
        for rec in sorted_recs:
            row  = self._batch_table.rowCount()
            self._batch_table.insertRow(row)
            t    = rec.get("transfer_coefficient", 0.0)
            conf = rec.get("confidence",  "-")
            dec  = rec.get("expected_ic_decay",   0.0)
            ok   = rec.get("is_transferable",     False)

            self._batch_table.setItem(row, 0, _cell(rec.get("market_dst", "")))
            t_item = _cell(f"{t:.4f}")
            c = "#4caf50" if t >= 0.6 else "#ff9800" if t >= 0.35 else "#f44336"
            t_item.setForeground(QtGui.QColor(c))
            self._batch_table.setItem(row, 1, t_item)

            c_item = _cell(conf)
            c_item.setForeground(QtGui.QColor(conf_map.get(conf, "#888")))
            self._batch_table.setItem(row, 2, c_item)
            self._batch_table.setItem(row, 3, _cell(f"{dec:.4f}"))
            ok_item = _cell("?" if ok else "?")
            ok_item.setForeground(QtGui.QColor("#4caf50" if ok else "#f44336"))
            self._batch_table.setItem(row, 4, ok_item)

    def _update_state_labels(self, state: dict) -> None:
        self._stat_total.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("total_transfers", 0)))
        self._stat_ok.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("successful", 0)))
        self._stat_rej.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("rejected", 0)))
        avg = state.get("avg_coefficient", 0.0)
        self._stat_avg.findChild(QtWidgets.QLabel, "val").setText(f"{avg:.4f}")


# ©¤©¤ Ð¡¹¤¾ß ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤

def _hline() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def _metric_label(value: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(value)
    lbl.setStyleSheet("font-size:13px; font-weight:bold; color:#4fc3f7;")
    return lbl


def _cell(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    return item


def _stat_row(label: str) -> QtWidgets.QWidget:
    w = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    lbl = QtWidgets.QLabel(f"{label}:")
    lbl.setStyleSheet("color:#aaa; font-size:10px;")
    lbl.setFixedWidth(80)
    val = QtWidgets.QLabel("0")
    val.setObjectName("val")
    val.setStyleSheet("font-size:11px;")
    layout.addWidget(lbl)
    layout.addWidget(val)
    return w
