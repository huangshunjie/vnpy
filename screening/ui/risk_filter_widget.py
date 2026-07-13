"""
screening/ui/risk_filter_widget.py

Risk Filter Widget — 风险过滤配置面板（Phase 6）。
"""

from __future__ import annotations
from vnpy.trader.ui import QtWidgets
from ..engine.risk_filter_engine import RiskFilterConfig

_PANEL="#181825"; _PANEL2="#11111b"; _BORDER="#45475a"; _FG="#cdd6f4"
_MUT="#6c7086"; _RED="#f38ba8"; _GRN="#a6e3a1"; _BLU="#89b4fa"
_YLW="#f9e2af"; _ORG="#fab387"
_LABEL=f"color:{_FG};font-size:11px;"
_INPUT=(f"background:{_PANEL2};color:{_FG};border:1px solid {_BORDER};"
        f"border-radius:3px;padding:3px 6px;font-size:11px;")
_SECTION=f"color:{_RED};font-size:11px;font-weight:bold;"

def _sb(text, color=_MUT):
    b=QtWidgets.QPushButton(text)
    b.setStyleSheet(
        f"QPushButton{{background:#313244;color:{color};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:3px 10px;font-size:11px;}}"
        f"QPushButton:hover{{background:#45475a;}}")
    return b


class RiskFilterWidget(QtWidgets.QWidget):
    """风险过滤配置面板（Phase 6）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._load_defaults()

    def _sep(self):
        s=QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};"); return s

    def _sec(self, t):
        l=QtWidgets.QLabel(t); l.setStyleSheet(_SECTION); return l

    def _row(self, label, widget, layout):
        r=QtWidgets.QHBoxLayout()
        r.addWidget(QtWidgets.QLabel(label, styleSheet=_LABEL))
        r.addWidget(widget); r.addStretch()
        layout.addLayout(r)

    def _init_ui(self):
        self.setStyleSheet(f"background:{_PANEL};")
        root=QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12,12,12,12); root.setSpacing(8)

        t=QtWidgets.QLabel("Risk Filter  风险过滤引擎")
        t.setStyleSheet(f"color:{_RED};font-size:13px;font-weight:bold;")
        root.addWidget(t); root.addWidget(self._sep())

        # 波动率过滤
        root.addWidget(self._sec("波动率过滤"))
        self._chk_vol=QtWidgets.QCheckBox("启用波动率过滤")
        self._chk_vol.setStyleSheet(f"color:{_FG};font-size:11px;")
        root.addWidget(self._chk_vol)
        self._spin_vol=QtWidgets.QDoubleSpinBox()
        self._spin_vol.setRange(0.1, 5.0); self._spin_vol.setSingleStep(0.05)
        self._spin_vol.setDecimals(2); self._spin_vol.setSuffix("  (年化)")
        self._spin_vol.setFixedWidth(130); self._spin_vol.setStyleSheet(_INPUT)
        self._row("最大波动率：", self._spin_vol, root)
        self._spin_vol_win=QtWidgets.QSpinBox()
        self._spin_vol_win.setRange(5,250); self._spin_vol_win.setSuffix(" 日")
        self._spin_vol_win.setFixedWidth(80); self._spin_vol_win.setStyleSheet(_INPUT)
        self._row("计算窗口：", self._spin_vol_win, root)

        root.addWidget(self._sep())

        # Beta 过滤
        root.addWidget(self._sec("Beta 过滤"))
        self._chk_beta=QtWidgets.QCheckBox("启用 Beta 过滤")
        self._chk_beta.setStyleSheet(f"color:{_FG};font-size:11px;")
        root.addWidget(self._chk_beta)
        self._spin_beta=QtWidgets.QDoubleSpinBox()
        self._spin_beta.setRange(0.1, 5.0); self._spin_beta.setSingleStep(0.1)
        self._spin_beta.setDecimals(2); self._spin_beta.setFixedWidth(90)
        self._spin_beta.setStyleSheet(_INPUT)
        self._row("最大 Beta：", self._spin_beta, root)

        root.addWidget(self._sep())

        # 行业集中度
        root.addWidget(self._sec("行业集中度控制"))
        self._chk_ind=QtWidgets.QCheckBox("启用行业集中度限制")
        self._chk_ind.setStyleSheet(f"color:{_FG};font-size:11px;")
        root.addWidget(self._chk_ind)
        self._spin_ind=QtWidgets.QSpinBox()
        self._spin_ind.setRange(1, 100); self._spin_ind.setSuffix(" 只/行业")
        self._spin_ind.setFixedWidth(100); self._spin_ind.setStyleSheet(_INPUT)
        self._row("同行业上限：", self._spin_ind, root)

        root.addWidget(self._sep())

        # 按钮栏
        br=QtWidgets.QHBoxLayout()
        bs=_sb("应用配置", _GRN); bs.clicked.connect(self._on_apply)
        br.addWidget(bs); br.addStretch(); root.addLayout(br)

        self._sl=QtWidgets.QLabel("")
        self._sl.setStyleSheet(f"color:{_MUT};font-size:10px;")
        root.addWidget(self._sl); root.addStretch()

    def _load_defaults(self):
        cfg=RiskFilterConfig.default()
        self._chk_vol.setChecked(cfg.enable_vol_filter)
        self._spin_vol.setValue(cfg.max_volatility)
        self._spin_vol_win.setValue(cfg.vol_window)
        self._chk_beta.setChecked(cfg.enable_beta_filter)
        self._spin_beta.setValue(cfg.max_beta)
        self._chk_ind.setChecked(cfg.enable_industry_filter)
        self._spin_ind.setValue(cfg.max_industry_count)

    def _on_apply(self):
        cfg=self.get_config()
        if self._engine and self._engine.risk_filter_engine:
            self._engine.risk_filter_engine.set_config(cfg)
            self._sl.setText("配置已应用")
            self._sl.setStyleSheet(f"color:{_GRN};font-size:10px;")

    def get_config(self) -> RiskFilterConfig:
        return RiskFilterConfig(
            max_volatility=self._spin_vol.value(),
            max_beta=self._spin_beta.value(),
            max_industry_count=self._spin_ind.value(),
            vol_window=self._spin_vol_win.value(),
            enable_vol_filter=self._chk_vol.isChecked(),
            enable_beta_filter=self._chk_beta.isChecked(),
            enable_industry_filter=self._chk_ind.isChecked(),
        )
