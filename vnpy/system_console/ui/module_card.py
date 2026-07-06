"""
system_console/ui/module_card.py

ModuleCard — 单个模块卡片组件（含状态灯、指标、启停按钮）。
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import ModuleState

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"; _RED = "#f38ba8"
_ORG = "#fab387"; _TEA = "#94e2d5"; _BLUE = "#89b4fa"; _MAV = "#cba6f7"

_STATE_BG = {
    ModuleState.RUNNING:  "#1a3a2a",
    ModuleState.STARTING: "#2a2a1a",
    ModuleState.STOPPING: "#2a2a1a",
    ModuleState.STOPPED:  "#1e1e2e",
    ModuleState.ERROR:    "#3a1a1a",
    ModuleState.UNKNOWN:  "#1e1e2e",
}
_STATE_BORDER = {
    ModuleState.RUNNING:  _GRN,
    ModuleState.STARTING: _YLW,
    ModuleState.STOPPING: _YLW,
    ModuleState.STOPPED:  _BORDER,
    ModuleState.ERROR:    _RED,
    ModuleState.UNKNOWN:  _BORDER,
}
_STATE_DOT = {
    ModuleState.RUNNING:  _GRN,
    ModuleState.STARTING: _YLW,
    ModuleState.STOPPING: _YLW,
    ModuleState.STOPPED:  _MUT,
    ModuleState.ERROR:    _RED,
    ModuleState.UNKNOWN:  _BORDER,
}


def _q(color: str) -> str:
    """Return a stylesheet fragment with given color."""
    return f"color:{color};font-size:9px;font-weight:bold;border:none;background:transparent;"


class ModuleCard(QtWidgets.QWidget):
    """
    18-module card (170 × 126 px).

    Signals:
      start_requested(key: str)
      stop_requested(key: str)
    """

    start_requested = QtCore.Signal(str)
    stop_requested  = QtCore.Signal(str)

    def __init__(self, key: str, label: str, display: str,
                 layer: int, parent=None) -> None:
        super().__init__(parent)
        self._key     = key
        self._label   = label
        self._display = display
        self._layer   = layer
        self._state   = ModuleState.UNKNOWN
        self.setFixedSize(170, 126)
        self._init_ui()

    # ── build UI ──────────────────────────────────────────────────────
    def _init_ui(self) -> None:
        self._apply_state(ModuleState.UNKNOWN)
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(8, 6, 8, 6)
        vb.setSpacing(3)

        # header row
        hdr = QtWidgets.QHBoxLayout()
        self._dot = QtWidgets.QLabel("●")
        self._dot.setStyleSheet(
            f"color:{_MUT};font-size:11px;border:none;background:transparent;")
        self._lbl_name = QtWidgets.QLabel(self._label)
        self._lbl_name.setStyleSheet(
            f"color:{_FG};font-weight:bold;font-size:11px;"
            f"border:none;background:transparent;")
        self._lbl_layer = QtWidgets.QLabel(f"L{self._layer}")
        self._lbl_layer.setStyleSheet(
            f"color:{_MUT};font-size:8px;border:none;background:transparent;")
        hdr.addWidget(self._dot)
        hdr.addWidget(self._lbl_name)
        hdr.addStretch()
        hdr.addWidget(self._lbl_layer)
        vb.addLayout(hdr)

        # state label
        self._lbl_state = QtWidgets.QLabel("unknown")
        self._lbl_state.setStyleSheet(
            f"color:{_MUT};font-size:9px;border:none;background:transparent;")
        vb.addWidget(self._lbl_state)

        # metrics grid
        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setSpacing(1)
        self._kv: dict[str, QtWidgets.QLabel] = {}
        for row, (k, txt) in enumerate([
            ("lat",   "Lat ms"),
            ("tput",  "Evt/min"),
            ("err",   "ErrRate"),
            ("evts",  "Events"),
        ]):
            lk = QtWidgets.QLabel(txt)
            lk.setStyleSheet(
                f"color:{_MUT};font-size:8px;border:none;background:transparent;")
            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(_q(_TEA))
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lk, row, 0)
            grid.addWidget(lv, row, 1)
            self._kv[k] = lv
        vb.addLayout(grid)

        # button row
        vb.addStretch()
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(4)
        self._btn_start = self._make_btn("▶ Start", _GRN, self._on_start)
        self._btn_stop  = self._make_btn("■ Stop",  _RED,  self._on_stop)
        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        vb.addLayout(btn_row)

    @staticmethod
    def _make_btn(text: str, color: str, slot) -> QtWidgets.QPushButton:
        b = QtWidgets.QPushButton(text)
        b.setFixedHeight(20)
        b.setStyleSheet(
            f"QPushButton{{background:{color};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:3px;font-size:9px;padding:0 4px;}}"
            f"QPushButton:disabled{{background:#45475a;color:#6c7086;}}")
        b.clicked.connect(slot)
        return b

    # ── slots ─────────────────────────────────────────────────────────
    def _on_start(self) -> None:
        self.start_requested.emit(self._key)

    def _on_stop(self) -> None:
        self.stop_requested.emit(self._key)

    # ── refresh ───────────────────────────────────────────────────────
    def refresh(self, entry_dict: dict) -> None:
        state_str = entry_dict.get("state", "unknown")
        state = ModuleState(state_str) if state_str in [
            s.value for s in ModuleState] else ModuleState.UNKNOWN

        if state != self._state:
            self._state = state
            self._apply_state(state)

        dot_c = _STATE_DOT.get(state, _MUT)
        self._dot.setStyleSheet(
            f"color:{dot_c};font-size:11px;"
            f"border:none;background:transparent;")
        self._lbl_state.setText(state_str)
        self._lbl_state.setStyleSheet(
            f"color:{dot_c};font-size:9px;border:none;background:transparent;")

        lat  = entry_dict.get("latency_ms", 0.0)
        tput = entry_dict.get("throughput",  0.0)
        err  = entry_dict.get("error_rate",  0.0)
        evts = entry_dict.get("event_count", 0)

        lat_c = _GRN if lat < 500 else (_YLW if lat < 2000 else _RED)
        err_c = _GRN if err < 0.05 else (_YLW if err < 0.20 else _RED)

        self._kv["lat"].setText(f"{lat:.0f}")
        self._kv["lat"].setStyleSheet(_q(lat_c))
        self._kv["tput"].setText(f"{tput:.1f}")
        self._kv["err"].setText(f"{err:.1%}")
        self._kv["err"].setStyleSheet(_q(err_c))
        self._kv["evts"].setText(str(evts))

        # button state
        running = state == ModuleState.RUNNING
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)

        # error tooltip
        msg = entry_dict.get("error_msg", "")
        if msg:
            self.setToolTip(f"Error: {msg}")
        else:
            uptime = entry_dict.get("uptime_s", 0)
            self.setToolTip(
                f"{self._display}\nState: {state_str}\nUptime: {uptime:.0f}s")

    def _apply_state(self, state: ModuleState) -> None:
        bg     = _STATE_BG.get(state, _BG)
        border = _STATE_BORDER.get(state, _BORDER)
        self.setStyleSheet(
            f"ModuleCard{{background:{bg};"
            f"border:1px solid {border};border-radius:6px;}}")

    @property
    def key(self) -> str:
        return self._key
