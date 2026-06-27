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

        self._setting_edit = QtWidgets.QPlainTextEdit()
        self._setting_edit.setFixedHeight(90)
        form.addRow("策略参数：", _field_with_hint(
            self._setting_edit,
            "格式：key=value，每行一个。示例：atr_length=22"))

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

    # ------------------------------------------------------------------ #
    #  Config persistence
    # ------------------------------------------------------------------ #

    def _load_config(self) -> None:
        """从磁盘恢复上次配置，文件不存在则静默跳过。"""
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
            self._setting_edit.setPlainText(
                "\n".join(f"{k}={v}" for k, v in setting.items()))

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
            "strategy_setting": self._parse_setting(),
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

    def _parse_setting(self) -> dict:
        out: dict = {}
        for line in self._setting_edit.toPlainText().splitlines():
            line = line.strip()
            if "=" in line:
                k, _, v_str = line.partition("=")
                k, v_str = k.strip(), v_str.strip()
                try:
                    out[k] = int(v_str)
                except ValueError:
                    try:
                        out[k] = float(v_str)
                    except ValueError:
                        out[k] = v_str
        return out

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
            QtWidgets.QMessageBox.warning(
                self, "参数错误", "\n".join(errors))
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
                "strategy_setting": self._parse_setting(),
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
            self._setting_edit.setPlainText(
                "\n".join(f"{k}={v}" for k, v in setting.items()))
        if symbols := cfg.get("symbols", []):
            self._pool_edit.setPlainText("\n".join(symbols))
        if cfg.get("use_multiprocess"):
            self._mp_check.setChecked(True)
        if w := cfg.get("max_workers"):
            self._workers_spin.setValue(int(w))
