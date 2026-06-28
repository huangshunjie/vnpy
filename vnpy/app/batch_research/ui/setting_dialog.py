from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from vnpy.trader.ui import QtCore, QtWidgets

_CONFIG_PATH = Path.home() / ".vnpy" / "batch_research_config.json"
_HINT_STYLE = "color: #888888; font-size: 11px;"


def _hint(text: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text)
    lbl.setStyleSheet(_HINT_STYLE)
    lbl.setWordWrap(True)
    return lbl


def _field_with_hint(widget: QtWidgets.QWidget, hint_text: str) -> QtWidgets.QWidget:
    c = QtWidgets.QWidget()
    v = QtWidgets.QVBoxLayout(c)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(2)
    v.addWidget(widget)
    v.addWidget(_hint(hint_text))
    return c


class _ParamTable(QtWidgets.QTableWidget):
    """策略参数编辑表格：左列参数名+类型（只读），右列参数值（可直接编辑）。"""

    def __init__(self) -> None:
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels(["参数名（类型）", "值"])
        self.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
            | QtWidgets.QAbstractItemView.EditTrigger.SelectedClicked
            | QtWidgets.QAbstractItemView.EditTrigger.AnyKeyPressed
        )

    def load_params(self, strategy_cls: type, existing: dict | None = None) -> None:
        keys = getattr(strategy_cls, "parameters", [])
        self.setRowCount(len(keys))
        for row, key in enumerate(keys):
            default = getattr(strategy_cls, key, "")
            val_type = type(default).__name__ if default != "" else "str"

            name_item = QtWidgets.QTableWidgetItem(f"{key}  ({val_type})")
            name_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            from vnpy.trader.ui import QtGui
            name_item.setForeground(QtGui.QColor('#888888'))
            self.setItem(row, 0, name_item)

            value = existing.get(key, default) if existing else default
            self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(value)))

        self.resizeRowsToContents()

    def get_setting(self) -> dict:
        out: dict = {}
        for row in range(self.rowCount()):
            name_cell = self.item(row, 0)
            val_cell  = self.item(row, 1)
            if not name_cell or not val_cell:
                continue
            key   = name_cell.text().split("  ")[0].strip()
            v_str = val_cell.text().strip()
            try:
                out[key] = int(v_str)
            except ValueError:
                try:
                    out[key] = float(v_str)
                except ValueError:
                    out[key] = v_str
        return out

    def set_from_dict(self, setting: dict) -> None:
        for row in range(self.rowCount()):
            name_cell = self.item(row, 0)
            if not name_cell:
                continue
            key = name_cell.text().split("  ")[0].strip()
            if key in setting:
                self.item(row, 1).setText(str(setting[key]))


class SettingDialog(QtWidgets.QDialog):
    """批量回测配置对话框，支持配置持久化记忆。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("批量回测配置")
        self.setMinimumWidth(580)
        self._init_ui()
        self._load_config()

    # ------------------------------------------------------------------ #
    #  Build UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        form.setVerticalSpacing(6)

        self._strategy_combo = QtWidgets.QComboBox()
        self._strategy_combo.setMinimumWidth(260)
        self._populate_strategy_combo()
        self._strategy_combo.currentTextChanged.connect(self._on_strategy_changed)
        form.addRow("策略类：", self._strategy_combo)

        self._start_edit = QtWidgets.QDateEdit(QtCore.QDate(2020, 1, 1))
        self._start_edit.setCalendarPopup(True)
        self._start_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("开始日期：", self._start_edit)

        self._end_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self._end_edit.setCalendarPopup(True)
        self._end_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("结束日期：", self._end_edit)

        self._capital_spin = QtWidgets.QDoubleSpinBox()
        self._capital_spin.setRange(1_000, 1_000_000_000)
        self._capital_spin.setValue(1_000_000)
        self._capital_spin.setSingleStep(100_000)
        self._capital_spin.setDecimals(0)
        form.addRow("初始资金：", self._capital_spin)

        self._rate_edit = QtWidgets.QLineEdit("0.0001")
        form.addRow("手续费率：", _field_with_hint(
            self._rate_edit, "示例：0.0001（万分之一）"))

        self._slippage_edit = QtWidgets.QLineEdit("0.02")
        form.addRow("滑点（元）：", _field_with_hint(
            self._slippage_edit,
            "A 股建议 2.0（绝对金额）；期货填 tick 数 × pricetick"))

        self._size_edit = QtWidgets.QLineEdit("1.0")
        form.addRow("合约乘数：", _field_with_hint(
            self._size_edit, "A 股填 100（1 手 = 100 股）；期货填合约乘数"))

        self._pricetick_edit = QtWidgets.QLineEdit("0.01")
        form.addRow("最小变动价位：", _field_with_hint(
            self._pricetick_edit, "A 股填 0.01；沪深 ETF 填 0.001"))

        self._param_table = _ParamTable()
        self._param_table.setFixedHeight(160)
        form.addRow("策略参数：", _field_with_hint(
            self._param_table,
            "双击右列单元格直接修改参数值；切换策略时自动填入默认值"))

        self._pool_edit = QtWidgets.QPlainTextEdit()
        self._pool_edit.setFixedHeight(100)
        form.addRow("股票池：", _field_with_hint(
            self._pool_edit,
            "每行一个 vt_symbol，或逗号分隔。示例：600519.SSE"))

        mp_layout = QtWidgets.QHBoxLayout()
        self._mp_check = QtWidgets.QCheckBox("启用多进程")
        self._workers_spin = QtWidgets.QSpinBox()
        self._workers_spin.setRange(1, 64)
        self._workers_spin.setValue(4)
        self._workers_spin.setEnabled(False)
        self._mp_check.toggled.connect(self._workers_spin.setEnabled)
        mp_layout.addWidget(self._mp_check)
        mp_layout.addWidget(QtWidgets.QLabel("进程数："))
        mp_layout.addWidget(self._workers_spin)
        mp_layout.addStretch()

        mp_container = QtWidgets.QWidget()
        mp_vbox = QtWidgets.QVBoxLayout(mp_container)
        mp_vbox.setContentsMargins(0, 0, 0, 0)
        mp_vbox.setSpacing(2)
        mp_vbox.addLayout(mp_layout)
        mp_vbox.addWidget(_hint("≤ 50 只时串行更快；≥ 200 只时多进程明显提速"))
        form.addRow("并行：", mp_container)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(form)
        vbox.addWidget(btn_box)
        self.setLayout(vbox)

    def _populate_strategy_combo(self) -> None:
        self._strategy_map: dict[str, type] = {}
        try:
            import importlib
            import pkgutil
            from vnpy_ctastrategy.template import CtaTemplate
            import vnpy_ctastrategy.strategies as strat_pkg
            for _f, modname, _p in pkgutil.iter_modules(strat_pkg.__path__):
                try:
                    mod = importlib.import_module(
                        f"vnpy_ctastrategy.strategies.{modname}")
                    for attr in dir(mod):
                        cls = getattr(mod, attr)
                        if (isinstance(cls, type)
                                and issubclass(cls, CtaTemplate)
                                and cls is not CtaTemplate):
                            self._strategy_map[attr] = cls
                except Exception:
                    pass
        except Exception:
            pass
        if self._strategy_map:
            self._strategy_combo.addItems(sorted(self._strategy_map.keys()))
        else:
            self._strategy_combo.addItem("（未找到策略类）")

    def _on_strategy_changed(self, name: str) -> None:
        """切换策略时用该策略的默认参数填充表格。"""
        cls = self._strategy_map.get(name)
        if not cls:
            self._param_table.setRowCount(0)
            return
        self._param_table.load_params(cls)

    # ------------------------------------------------------------------ #
    #  Config persistence
    # ------------------------------------------------------------------ #

    def _load_config(self) -> None:
        if not _CONFIG_PATH.exists():
            return
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return

        if name := data.get("strategy_name", ""):
            idx = self._strategy_combo.findText(name)
            if idx >= 0:
                self._strategy_combo.setCurrentIndex(idx)

        for key, widget in [("start_date", self._start_edit),
                             ("end_date",   self._end_edit)]:
            if v := data.get(key):
                try:
                    from datetime import datetime as _dt
                    d = _dt.strptime(v, "%Y-%m-%d")
                    widget.setDate(QtCore.QDate(d.year, d.month, d.day))
                except ValueError:
                    pass

        if v := data.get("capital"):
            self._capital_spin.setValue(float(v))
        for key, widget in [
            ("rate",      self._rate_edit),
            ("slippage",  self._slippage_edit),
            ("size",      self._size_edit),
            ("pricetick", self._pricetick_edit),
        ]:
            if v := data.get(key):
                widget.setText(str(v))

        if setting := data.get("strategy_setting", {}):
            self._param_table.set_from_dict(setting)

        if symbols := data.get("symbols", []):
            self._pool_edit.setPlainText("\n".join(symbols))

        if data.get("use_multiprocess"):
            self._mp_check.setChecked(True)
        self._workers_spin.setValue(int(data.get("max_workers", 4)))

    def _save_config(self) -> None:
        import json as _json
        qs = self._start_edit.date()
        qe = self._end_edit.date()
        data = {
            "strategy_name":    self._strategy_combo.currentText(),
            "start_date":       f"{qs.year()}-{qs.month():02d}-{qs.day():02d}",
            "end_date":         f"{qe.year()}-{qe.month():02d}-{qe.day():02d}",
            "capital":          int(self._capital_spin.value()),
            "rate":             self._rate_edit.text().strip(),
            "slippage":         self._slippage_edit.text().strip(),
            "size":             self._size_edit.text().strip(),
            "pricetick":        self._pricetick_edit.text().strip(),
            "strategy_setting": self._param_table.get_setting(),
            "symbols":          self._parse_symbols(),
            "use_multiprocess": self._mp_check.isChecked(),
            "max_workers":      self._workers_spin.value(),
        }
        try:
            _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CONFIG_PATH.write_text(
                _json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _parse_symbols(self) -> list:
        raw = self._pool_edit.toPlainText()
        return [s.strip()
                for s in raw.replace(",", "\n").splitlines()
                if s.strip()]

    # ------------------------------------------------------------------ #
    #  Validation & accept
    # ------------------------------------------------------------------ #

    def _on_accept(self) -> None:
        errors = self._validate()
        if errors:
            QtWidgets.QMessageBox.warning(self, "参数错误", "\n".join(errors))
            return
        self._save_config()
        self.accept()

    def _validate(self) -> list:
        errors = []
        if not self._parse_symbols():
            errors.append("股票池不能为空")
        qs = self._start_edit.date()
        qe = self._end_edit.date()
        if (qs.year(), qs.month(), qs.day()) >= (qe.year(), qe.month(), qe.day()):
            errors.append("结束日期必须晚于开始日期")
        for label, widget in [
            ("手续费率",     self._rate_edit),
            ("滑点",         self._slippage_edit),
            ("合约乘数",     self._size_edit),
            ("最小变动价位", self._pricetick_edit),
        ]:
            try:
                float(widget.text())
            except ValueError:
                errors.append(f"{label}格式错误")
        return errors

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def get_config(self) -> dict:
        name = self._strategy_combo.currentText()
        strategy_class = self._strategy_map.get(name)
        qs = self._start_edit.date()
        qe = self._end_edit.date()
        return {
            "parameters": {
                "strategy_class":   strategy_class,
                "start":            datetime(qs.year(), qs.month(), qs.day()),
                "end":              datetime(qe.year(), qe.month(), qe.day()),
                "capital":          int(self._capital_spin.value()),
                "rate":             float(self._rate_edit.text()),
                "slippage":         float(self._slippage_edit.text()),
                "size":             float(self._size_edit.text()),
                "pricetick":        float(self._pricetick_edit.text()),
                "strategy_setting": self._param_table.get_setting(),
            },
            "symbols":          self._parse_symbols(),
            "use_multiprocess": self._mp_check.isChecked(),
            "max_workers":      self._workers_spin.value(),
        }

    def set_config(self, cfg: dict) -> None:
        params = cfg.get("parameters", {})
        if sc := params.get("strategy_class"):
            name = sc.__name__ if isinstance(sc, type) else str(sc)
            idx = self._strategy_combo.findText(name)
            if idx >= 0:
                self._strategy_combo.setCurrentIndex(idx)
        if d := params.get("start"):
            self._start_edit.setDate(QtCore.QDate(d.year, d.month, d.day))
        if d := params.get("end"):
            self._end_edit.setDate(QtCore.QDate(d.year, d.month, d.day))
        if v := params.get("capital"):
            self._capital_spin.setValue(float(v))
        for attr, widget in [
            ("rate",      self._rate_edit),
            ("slippage",  self._slippage_edit),
            ("size",      self._size_edit),
            ("pricetick", self._pricetick_edit),
        ]:
            if v := params.get(attr):
                widget.setText(str(v))
        if setting := params.get("strategy_setting", {}):
            self._param_table.set_from_dict(setting)
        if symbols := cfg.get("symbols", []):
            self._pool_edit.setPlainText("\n".join(symbols))
        if cfg.get("use_multiprocess"):
            self._mp_check.setChecked(True)
        if w := cfg.get("max_workers"):
            self._workers_spin.setValue(int(w))
