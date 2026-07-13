"""
screening/ui/factor_rank_widget.py
Factor Rank Widget - Phase 4
"""
from __future__ import annotations
from vnpy.trader.ui import QtWidgets, QtCore
from ..constant import ScoreMethod, RankDirection
from ..model.factor_score import FactorRankConfig, FactorWeight

_PANEL="#181825"; _PANEL2="#11111b"; _BORDER="#45475a"; _FG="#cdd6f4"
_MUT="#6c7086"; _ORG="#fab387"; _GRN="#a6e3a1"; _BLU="#89b4fa"
_YLW="#f9e2af"; _RED="#f38ba8"; _MAV="#cba6f7"
_LABEL=f"color:{_FG};font-size:11px;"
_INPUT=(f"background:{_PANEL2};color:{_FG};border:1px solid {_BORDER};"
        f"border-radius:3px;padding:3px 6px;font-size:11px;")
_SECTION=f"color:{_ORG};font-size:11px;font-weight:bold;"
_BUILTIN_FACTORS=[
    "MOM_1D","MOM_5D","MOM_20D","MOM_60D","REV_1D","REV_5D",
    "VOL_5D","VOL_20D","RSI_14","RSI_28","MACD_SIGNAL","BB_WIDTH",
    "PE_RANK","PB_RANK","ROE_RANK","EPS_SURPRISE",
    "NETFLOW_5D","LARGE_ORDER_RATIO","ILLIQ_5D","AMIHUD_5D",
    "momentum","quality","value","low_vol",
]
_METHOD_LABELS={
    ScoreMethod.MANUAL:"手动权重", ScoreMethod.EQUAL_WEIGHT:"等权",
    ScoreMethod.IC_WEIGHT:"IC加权", ScoreMethod.ICIR_WEIGHT:"ICIR加权",
}
_DIR_LABELS={RankDirection.DESC:"↑越大越好", RankDirection.ASC:"↓越小越好"}

def _sb(text, color=_MUT):
    b=QtWidgets.QPushButton(text)
    b.setStyleSheet(
        f"QPushButton{{background:#313244;color:{color};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:2px 8px;font-size:10px;}}"
        f"QPushButton:hover{{background:#45475a;}}")
    b.setMaximumHeight(22)
    return b

class FactorRow(QtWidgets.QWidget):
    deleted=QtCore.Signal(object)
    def __init__(self,fw=None,available_factors=None,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{_PANEL2};border:1px solid {_BORDER};border-radius:3px;")
        h=QtWidgets.QHBoxLayout(self); h.setContentsMargins(6,3,6,3); h.setSpacing(6)
        self._fc=QtWidgets.QComboBox(); self._fc.setStyleSheet(_INPUT)
        self._fc.setFixedWidth(150); self._fc.setEditable(True)
        for f in (available_factors or _BUILTIN_FACTORS): self._fc.addItem(f)
        self._dc=QtWidgets.QComboBox(); self._dc.setStyleSheet(_INPUT); self._dc.setFixedWidth(110)
        for d,lbl in _DIR_LABELS.items(): self._dc.addItem(lbl,d)
        self._ws=QtWidgets.QDoubleSpinBox()
        self._ws.setRange(0.0,10.0); self._ws.setSingleStep(0.05)
        self._ws.setDecimals(2); self._ws.setValue(1.0)
        self._ws.setFixedWidth(70); self._ws.setStyleSheet(_INPUT)
        self._il=QtWidgets.QLabel("IC:--")
        self._il.setStyleSheet(f"color:{_MUT};font-size:10px;"); self._il.setFixedWidth(90)
        self._db=_sb("x",_RED); self._db.clicked.connect(lambda:self.deleted.emit(self))
        for w in [self._fc,self._dc,QtWidgets.QLabel("W:",styleSheet=_LABEL),
                  self._ws,self._il,self._db]: h.addWidget(w)
        h.addStretch()
        if fw: self._apply(fw)
    def _apply(self,fw):
        i=self._fc.findText(fw.factor_name)
        if i>=0: self._fc.setCurrentIndex(i)
        else: self._fc.setCurrentText(fw.factor_name)
        for i in range(self._dc.count()):
            if self._dc.itemData(i)==fw.direction: self._dc.setCurrentIndex(i); break
        self._ws.setValue(fw.weight)
    def set_ic(self,ic,icir):
        self._il.setText(f"IC:{ic:.3f} IR:{icir:.2f}")
        self._il.setStyleSheet(f"color:{_GRN if abs(ic)>0.02 else _MUT};font-size:10px;")
    def to_fw(self):
        return FactorWeight(factor_name=self._fc.currentText().strip(),
            weight=self._ws.value(),direction=self._dc.currentData(),enabled=True)


class FactorRankWidget(QtWidgets.QWidget):
    """因子排序配置面板（Phase 4）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._rows: list = []
        self._available = list(_BUILTIN_FACTORS)
        self._init_ui()
        self._load_avail()
        self._load_defaults()

    def _sep(self):
        s=QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};"); return s

    def _sec(self, t):
        l=QtWidgets.QLabel(t); l.setStyleSheet(_SECTION); return l

    def _init_ui(self):
        self.setStyleSheet(f"background:{_PANEL};")
        root=QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12,12,12,12); root.setSpacing(8)
        t=QtWidgets.QLabel("Factor Ranking  因子排序引擎")
        t.setStyleSheet(f"color:{_ORG};font-size:13px;font-weight:bold;")
        root.addWidget(t); root.addWidget(self._sep())
        root.addWidget(self._sec("加权方式"))
        mr=QtWidgets.QHBoxLayout()
        self._mc=QtWidgets.QComboBox(); self._mc.setStyleSheet(_INPUT); self._mc.setFixedWidth(130)
        for m,lbl in _METHOD_LABELS.items(): self._mc.addItem(lbl,m)
        self._mc.currentIndexChanged.connect(self._refresh_formula)
        mr.addWidget(QtWidgets.QLabel("方式:",styleSheet=_LABEL))
        mr.addWidget(self._mc); mr.addStretch(); root.addLayout(mr)
        root.addWidget(self._sep()); root.addWidget(self._sec("因子列表"))
        sc=QtWidgets.QScrollArea(); sc.setWidgetResizable(True)
        sc.setStyleSheet(f"QScrollArea{{background:{_PANEL2};border:1px solid {_BORDER};border-radius:4px;}}")
        self._rc=QtWidgets.QWidget(); self._rc.setStyleSheet(f"background:{_PANEL2};")
        self._rl=QtWidgets.QVBoxLayout(self._rc)
        self._rl.setContentsMargins(6,6,6,6); self._rl.setSpacing(4); self._rl.addStretch()
        sc.setWidget(self._rc); sc.setMinimumHeight(150); root.addWidget(sc)
        br=QtWidgets.QHBoxLayout()
        ba=_sb("+ 添加因子",_ORG); ba.clicked.connect(self._on_add)
        bc=_sb("清空",_RED); bc.clicked.connect(self._on_clear)
        bi=_sb("刷新IC",_BLU); bi.clicked.connect(self._on_refresh_ic)
        for b in [ba,bc,bi]: br.addWidget(b)
        br.addStretch(); root.addLayout(br); root.addWidget(self._sep())
        root.addWidget(self._sec("评分公式预览"))
        self._fl=QtWidgets.QLabel("(无因子)")
        self._fl.setStyleSheet(
            f"color:{_YLW};font-size:10px;background:{_PANEL2};"
            f"border:1px solid {_BORDER};border-radius:3px;padding:4px 6px;")
        self._fl.setWordWrap(True); self._fl.setMinimumHeight(36)
        root.addWidget(self._fl); root.addWidget(self._sep())
        root.addWidget(self._sec("配置管理"))
        nr=QtWidgets.QHBoxLayout()
        nr.addWidget(QtWidgets.QLabel("配置名:",styleSheet=_LABEL))
        self._ne=QtWidgets.QLineEdit("default_multi"); self._ne.setStyleSheet(_INPUT)
        nr.addWidget(self._ne,stretch=1); root.addLayout(nr)
        br2=QtWidgets.QHBoxLayout()
        bs=_sb("保存",_BLU); bs.clicked.connect(self._on_save)
        bl=_sb("加载",_MAV); bl.clicked.connect(self._on_load)
        br2.addWidget(bs); br2.addWidget(bl); br2.addStretch(); root.addLayout(br2)
        self._sl=QtWidgets.QLabel(""); self._sl.setStyleSheet(f"color:{_MUT};font-size:10px;")
        root.addWidget(self._sl); root.addStretch()

    def _load_avail(self):
        if self._engine and self._engine.factor_rank_engine:
            f=self._engine.factor_rank_engine.list_available_factors()
            if f: self._available=f

    def _load_defaults(self):
        for fw in FactorRankConfig.default_multi_factor().factors: self._add_row(fw)
        self._refresh_formula()

    def _on_add(self): self._add_row(); self._refresh_formula()

    def _add_row(self, fw=None):
        row=FactorRow(fw=fw,available_factors=self._available)
        row.deleted.connect(self._on_del)
        self._rows.append(row)
        self._rl.insertWidget(self._rl.count()-1, row)

    def _on_del(self, row):
        if row in self._rows: self._rows.remove(row)
        row.deleteLater(); self._refresh_formula()

    def _on_clear(self):
        for r in list(self._rows): r.deleteLater()
        self._rows.clear(); self._refresh_formula()

    def _on_refresh_ic(self):
        if not self._engine: return
        eng=self._engine.factor_rank_engine
        for row in self._rows:
            try:
                fw=row.to_fw()
                row.set_ic(eng.compute_ic(fw.factor_name),eng.compute_icir(fw.factor_name))
            except Exception: pass
        self._set_st("IC/ICIR 已刷新",_GRN)

    def _on_save(self):
        cfg=self.get_config()
        if self._engine:
            try:
                self._engine.repository.save_factor_config(cfg)
                if self._engine.factor_rank_engine:
                    self._engine.factor_rank_engine.set_config(cfg)
                self._set_st(f"已保存: {cfg.name}",_GRN)
            except Exception as e: self._set_st(f"保存失败: {e}",_RED)

    def _on_load(self):
        name=self._ne.text().strip() or "default_multi"
        if self._engine:
            try:
                cfg=self._engine.repository.load_factor_config(name)
                if cfg: self._apply_cfg(cfg); self._set_st(f"已加载: {name}",_GRN)
                else: self._set_st(f"未找到: {name}",_YLW)
            except Exception as e: self._set_st(f"加载失败: {e}",_RED)

    def _apply_cfg(self, cfg):
        self._on_clear(); self._ne.setText(cfg.name)
        idx=self._mc.findData(cfg.method)
        if idx>=0: self._mc.setCurrentIndex(idx)
        for fw in cfg.factors: self._add_row(fw)
        self._refresh_formula()

    def _refresh_formula(self, *_):
        method=self._mc.currentData()
        parts=[]
        for row in self._rows:
            try:
                fw=row.to_fw()
                parts.append(f"{fw.weight:.2f}x{fw.factor_name}"
                             if method==ScoreMethod.MANUAL else fw.factor_name)
            except Exception: pass
        lbl=_METHOD_LABELS.get(method,"")
        self._fl.setText(f"[{lbl}] Score = "+" + ".join(parts) if parts else "(无因子)")

    def _set_st(self, msg, color=_MUT):
        self._sl.setText(msg); self._sl.setStyleSheet(f"color:{color};font-size:10px;")

    def get_config(self) -> FactorRankConfig:
        method=self._mc.currentData()
        name=self._ne.text().strip() or "default_multi"
        factors=[]
        for row in self._rows:
            try: factors.append(row.to_fw())
            except Exception: pass
        return FactorRankConfig(method=method,factors=factors,name=name)
