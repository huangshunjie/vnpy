"""
screening/ui/universe_widget.py

Universe Widget — 股票池配置面板（Phase 2）。
"""

from __future__ import annotations
from typing import Optional

from vnpy.trader.ui import QtWidgets, QtCore

from ..constant import MarketUniverse, UniverseFilter
from ..model.universe import UniverseConfig, UniverseFilterRule

_PANEL  = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_BLU    = "#89b4fa"
_GRN    = "#a6e3a1"
_YLW    = "#f9e2af"
_RED    = "#f38ba8"

_LABEL_STYLE  = f"color:{_FG};font-size:11px;"
_INPUT_STYLE  = (
    f"background:#11111b;color:{_FG};border:1px solid {_BORDER};"
    f"border-radius:3px;padding:3px 6px;font-size:11px;"
)
_CHECK_STYLE  = f"color:{_FG};font-size:11px;"
_SECTION_STYLE = f"color:{_BLU};font-size:11px;font-weight:bold;"


class UniverseWidget(QtWidgets.QWidget):
    """股票池配置面板（Phase 2 完整实现）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._load_defaults()

    # ── UI 构建 ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background:{_PANEL};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QtWidgets.QLabel("Universe Manager  股票池管理")
        title.setStyleSheet(f"color:{_BLU};font-size:13px;font-weight:bold;")
        root.addWidget(title)
        root.addWidget(self._sep())

        # ── 市场选择 ──────────────────────────────────────────────────
        root.addWidget(self._section("市场股票池"))
        mkt_row = QtWidgets.QHBoxLayout()
        self._market_combo = QtWidgets.QComboBox()
        self._market_combo.setStyleSheet(_INPUT_STYLE)
        for m in MarketUniverse:
            self._market_combo.addItem(m.value, m)
        self._market_combo.currentIndexChanged.connect(self._on_market_changed)
        mkt_row.addWidget(QtWidgets.QLabel("市场：", styleSheet=_LABEL_STYLE))
        mkt_row.addWidget(self._market_combo, stretch=1)
        root.addLayout(mkt_row)

        # ── 自定义股票池 ──────────────────────────────────────────────
        self._custom_group = QtWidgets.QGroupBox("自定义股票池")
        self._custom_group.setStyleSheet(
            f"QGroupBox{{color:{_MUT};font-size:10px;border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:6px;}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:8px;}}"
        )
        cg_layout = QtWidgets.QVBoxLayout(self._custom_group)
        cg_layout.setContentsMargins(8, 12, 8, 8)
        hint = QtWidgets.QLabel("每行一个代码，格式：600519.SSE")
        hint.setStyleSheet(f"color:{_MUT};font-size:10px;")
        cg_layout.addWidget(hint)
        self._custom_edit = QtWidgets.QPlainTextEdit()
        self._custom_edit.setStyleSheet(_INPUT_STYLE)
        self._custom_edit.setFixedHeight(80)
        self._custom_edit.setPlaceholderText("600519.SSE\n000858.SZSE\n...")
        cg_layout.addWidget(self._custom_edit)
        root.addWidget(self._custom_group)
        self._custom_group.setVisible(False)

        root.addWidget(self._sep())

        # ── 基础过滤规则 ──────────────────────────────────────────────
        root.addWidget(self._section("基础过滤规则"))

        self._chk_st = QtWidgets.QCheckBox("排除 ST / *ST 股票")
        self._chk_st.setStyleSheet(_CHECK_STYLE)
        root.addWidget(self._chk_st)

        self._chk_suspended = QtWidgets.QCheckBox("排除停牌股票")
        self._chk_suspended.setStyleSheet(_CHECK_STYLE)
        root.addWidget(self._chk_suspended)

        self._chk_delisting = QtWidgets.QCheckBox("排除退市整理股票")
        self._chk_delisting.setStyleSheet(_CHECK_STYLE)
        root.addWidget(self._chk_delisting)

        # 上市天数
        listing_row = QtWidgets.QHBoxLayout()
        self._chk_listing = QtWidgets.QCheckBox("上市天数 ≥")
        self._chk_listing.setStyleSheet(_CHECK_STYLE)
        self._spin_listing = QtWidgets.QSpinBox()
        self._spin_listing.setRange(0, 9999)
        self._spin_listing.setValue(250)
        self._spin_listing.setSuffix(" 天")
        self._spin_listing.setStyleSheet(_INPUT_STYLE)
        self._spin_listing.setFixedWidth(90)
        listing_row.addWidget(self._chk_listing)
        listing_row.addWidget(self._spin_listing)
        listing_row.addStretch()
        root.addLayout(listing_row)

        # 日均成交额
        turnover_row = QtWidgets.QHBoxLayout()
        self._chk_turnover = QtWidgets.QCheckBox("日均成交额 ≥")
        self._chk_turnover.setStyleSheet(_CHECK_STYLE)
        self._spin_turnover = QtWidgets.QDoubleSpinBox()
        self._spin_turnover.setRange(0, 1e10)
        self._spin_turnover.setValue(5000)
        self._spin_turnover.setSuffix(" 万元")
        self._spin_turnover.setDecimals(0)
        self._spin_turnover.setSingleStep(1000)
        self._spin_turnover.setStyleSheet(_INPUT_STYLE)
        self._spin_turnover.setFixedWidth(120)
        turnover_row.addWidget(self._chk_turnover)
        turnover_row.addWidget(self._spin_turnover)
        turnover_row.addStretch()
        root.addLayout(turnover_row)

        root.addWidget(self._sep())

        # ── 配置名称 + 保存/加载 ──────────────────────────────────────
        root.addWidget(self._section("配置管理"))
        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(QtWidgets.QLabel("配置名：", styleSheet=_LABEL_STYLE))
        self._name_edit = QtWidgets.QLineEdit("default")
        self._name_edit.setStyleSheet(_INPUT_STYLE)
        name_row.addWidget(self._name_edit, stretch=1)
        root.addLayout(name_row)

        btn_row = QtWidgets.QHBoxLayout()
        self._btn_save = QtWidgets.QPushButton("保存配置")
        self._btn_load = QtWidgets.QPushButton("加载配置")
        for b in [self._btn_save, self._btn_load]:
            b.setStyleSheet(
                f"QPushButton{{background:#313244;color:{_FG};"
                f"border:1px solid {_BORDER};border-radius:3px;padding:4px 10px;"
                f"font-size:11px;}}"
                f"QPushButton:hover{{background:#45475a;}}"
            )
        self._btn_save.clicked.connect(self._on_save)
        self._btn_load.clicked.connect(self._on_load)
        btn_row.addWidget(self._btn_save)
        btn_row.addWidget(self._btn_load)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ── 预览信息 ──────────────────────────────────────────────────
        root.addWidget(self._sep())
        self._preview_label = QtWidgets.QLabel("股票池：未构建")
        self._preview_label.setStyleSheet(f"color:{_MUT};font-size:10px;")
        self._preview_label.setWordWrap(True)
        root.addWidget(self._preview_label)

        root.addStretch()

    def _section(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(_SECTION_STYLE)
        return lbl

    def _sep(self) -> QtWidgets.QFrame:
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};")
        return s

    # ── 默认值 ────────────────────────────────────────────────────────

    def _load_defaults(self) -> None:
        cfg = UniverseConfig.default()
        idx = self._market_combo.findData(cfg.market)
        if idx >= 0:
            self._market_combo.setCurrentIndex(idx)
        self._chk_st.setChecked(True)
        self._chk_suspended.setChecked(True)
        self._chk_delisting.setChecked(False)
        self._chk_listing.setChecked(True)
        self._spin_listing.setValue(250)
        self._chk_turnover.setChecked(True)
        self._spin_turnover.setValue(5000)

    # ── 事件回调 ──────────────────────────────────────────────────────

    def _on_market_changed(self, _: int) -> None:
        market = self._market_combo.currentData()
        self._custom_group.setVisible(market == MarketUniverse.CUSTOM)

    def _on_save(self) -> None:
        cfg = self.get_config()
        if self._engine:
            try:
                self._engine.repository.save_universe_config(cfg)
                self._preview_label.setText(f"已保存配置：{cfg.name}")
                self._preview_label.setStyleSheet(f"color:{_GRN};font-size:10px;")
            except Exception as e:
                self._preview_label.setText(f"保存失败：{e}")
                self._preview_label.setStyleSheet(f"color:{_RED};font-size:10px;")

    def _on_load(self) -> None:
        name = self._name_edit.text().strip() or "default"
        if self._engine:
            try:
                cfg = self._engine.repository.load_universe_config(name)
                if cfg:
                    self._apply_config(cfg)
                    self._preview_label.setText(f"已加载配置：{cfg.name}")
                    self._preview_label.setStyleSheet(f"color:{_GRN};font-size:10px;")
                else:
                    self._preview_label.setText(f"未找到配置：{name}")
                    self._preview_label.setStyleSheet(f"color:{_YLW};font-size:10px;")
            except Exception as e:
                self._preview_label.setText(f"加载失败：{e}")
                self._preview_label.setStyleSheet(f"color:{_RED};font-size:10px;")

    def _apply_config(self, cfg: UniverseConfig) -> None:
        idx = self._market_combo.findData(cfg.market)
        if idx >= 0:
            self._market_combo.setCurrentIndex(idx)
        self._name_edit.setText(cfg.name)
        if cfg.custom_symbols:
            self._custom_edit.setPlainText("\n".join(cfg.custom_symbols))
        for rule in cfg.filter_rules:
            ft = rule.filter_type
            if ft == UniverseFilter.EXCLUDE_ST:
                self._chk_st.setChecked(rule.enabled)
            elif ft == UniverseFilter.EXCLUDE_SUSPENDED:
                self._chk_suspended.setChecked(rule.enabled)
            elif ft == UniverseFilter.EXCLUDE_DELISTING:
                self._chk_delisting.setChecked(rule.enabled)
            elif ft == UniverseFilter.MIN_LISTING_DAYS:
                self._chk_listing.setChecked(rule.enabled)
                self._spin_listing.setValue(int(rule.value))
            elif ft == UniverseFilter.MIN_DAILY_TURNOVER:
                self._chk_turnover.setChecked(rule.enabled)
                self._spin_turnover.setValue(rule.value / 1e4)

    # ── 公开接口 ──────────────────────────────────────────────────────

    def get_config(self) -> UniverseConfig:
        """读取界面当前配置，返回 UniverseConfig。"""
        market: MarketUniverse = self._market_combo.currentData()
        name = self._name_edit.text().strip() or "default"

        custom = []
        if market == MarketUniverse.CUSTOM:
            raw = self._custom_edit.toPlainText().strip()
            custom = [s.strip() for s in raw.splitlines() if s.strip()]

        rules = []
        if self._chk_st.isChecked():
            rules.append(UniverseFilterRule(UniverseFilter.EXCLUDE_ST))
        if self._chk_suspended.isChecked():
            rules.append(UniverseFilterRule(UniverseFilter.EXCLUDE_SUSPENDED))
        if self._chk_delisting.isChecked():
            rules.append(UniverseFilterRule(UniverseFilter.EXCLUDE_DELISTING))
        if self._chk_listing.isChecked():
            rules.append(UniverseFilterRule(
                UniverseFilter.MIN_LISTING_DAYS,
                value=float(self._spin_listing.value()),
            ))
        if self._chk_turnover.isChecked():
            rules.append(UniverseFilterRule(
                UniverseFilter.MIN_DAILY_TURNOVER,
                value=self._spin_turnover.value() * 1e4,
            ))

        return UniverseConfig(
            name=name,
            market=market,
            custom_symbols=custom,
            filter_rules=rules,
        )

    def update_preview(self, universe_data) -> None:
        """供 ScreeningEngine 回调更新预览信息。"""
        if universe_data:
            txt = (
                f"市场：{universe_data.config.market.value}  |  "
                f"过滤前：{universe_data.total_before_filter}  |  "
                f"过滤后：{universe_data.total_after_filter} 只"
            )
            self._preview_label.setText(txt)
            self._preview_label.setStyleSheet(f"color:{_GRN};font-size:10px;")
