"""
ui/setting_dialog.py

参数配置对话框 — 让用户在界面上填写回测参数，不需要修改代码。

字段：
  - 策略类（动态扫描已安装的 CtaStrategy 子类）
  - 起止日期
  - 初始资金、手续费率、滑点、合约乘数、最小价格变动
  - 策略参数（key=value 文本框）
  - 多进程开关 + 进程数
  - 股票池输入（逗号分隔的 vt_symbol 列表）
"""

from __future__ import annotations

from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets


class SettingDialog(QtWidgets.QDialog):
    """
    Batch backtesting configuration dialog.

    Usage::

        dlg = SettingDialog(parent=self)
        if dlg.exec_() == SettingDialog.DialogCode.Accepted:
            cfg = dlg.get_config()
            engine.set_parameters(**cfg["parameters"])
            engine.set_stock_pool(cfg["symbols"])
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("批量回测配置")
        self.setMinimumWidth(560)
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  Build UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        # Strategy class combo ----------------------------------------- #
        self._strategy_combo = QtWidgets.QComboBox()
        self._strategy_combo.setMinimumWidth(260)
        self._populate_strategy_combo()
        form.addRow("策略类：", self._strategy_combo)

        # Date range ---------------------------------------------------- #
        self._start_edit = QtWidgets.QDateEdit(
            QtCore.QDate(2020, 1, 1)
        )
        self._start_edit.setCalendarPopup(True)
        self._start_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("开始日期：", self._start_edit)

        self._end_edit = QtWidgets.QDateEdit(
            QtCore.QDate.currentDate()
        )
        self._end_edit.setCalendarPopup(True)
        self._end_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("结束日期：", self._end_edit)

        # Capital & costs ----------------------------------------------- #
        self._capital_spin = QtWidgets.QDoubleSpinBox()
        self._capital_spin.setRange(1_000, 1_000_000_000)
        self._capital_spin.setValue(1_000_000)
        self._capital_spin.setSingleStep(100_000)
        self._capital_spin.setDecimals(0)
        form.addRow("初始资金：", self._capital_spin)

        self._rate_edit = QtWidgets.QLineEdit("0.0001")
        self._rate_edit.setToolTip("手续费率，如 0.0001")
        form.addRow("手续费率：", self._rate_edit)

        self._slippage_edit = QtWidgets.QLineEdit("0.02")
        form.addRow("滑点（元）：", self._slippage_edit)

        self._size_edit = QtWidgets.QLineEdit("1.0")
        form.addRow("合约乘数：", self._size_edit)

        self._pricetick_edit = QtWidgets.QLineEdit("0.01")
        form.addRow("最小变动价位：", self._pricetick_edit)

        # Strategy parameters (JSON / key=value) ------------------------ #
        self._setting_edit = QtWidgets.QPlainTextEdit()
        self._setting_edit.setPlaceholderText(
            'key=value，每行一个，例如：\natr_length=22\natr_ma_length=10'
        )
        self._setting_edit.setFixedHeight(90)
        form.addRow("策略参数：", self._setting_edit)

        # Stock pool ---------------------------------------------------- #
        self._pool_edit = QtWidgets.QPlainTextEdit()
        self._pool_edit.setPlaceholderText(
            "vt_symbol 列表（每行一个或逗号分隔），例如：\n"
            "000001.SZSE\n600519.SSE"
        )
        self._pool_edit.setFixedHeight(90)
        form.addRow("股票池：", self._pool_edit)

        # Multiprocess -------------------------------------------------- #
        mp_layout = QtWidgets.QHBoxLayout()
        self._mp_check = QtWidgets.QCheckBox("启用多进程")
        self._mp_check.setToolTip("大池子（300+）建议开启；小池子串行更快")
        self._workers_spin = QtWidgets.QSpinBox()
        self._workers_spin.setRange(1, 64)
        self._workers_spin.setValue(4)
        self._workers_spin.setEnabled(False)
        self._mp_check.toggled.connect(self._workers_spin.setEnabled)
        mp_layout.addWidget(self._mp_check)
        mp_layout.addWidget(QtWidgets.QLabel("进程数："))
        mp_layout.addWidget(self._workers_spin)
        mp_layout.addStretch()
        form.addRow("并行：", mp_layout)

        # Buttons ------------------------------------------------------- #
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
        """Scan installed CtaTemplate subclasses and populate the combo."""
        self._strategy_map: dict[str, type] = {}
        try:
            import importlib
            import pkgutil
            from vnpy_ctastrategy.template import CtaTemplate

            # Try to load all strategies from vnpy_ctastrategy.strategies
            import vnpy_ctastrategy.strategies as strat_pkg
            pkg_path = strat_pkg.__path__
            for _finder, modname, _ispkg in pkgutil.iter_modules(pkg_path):
                try:
                    mod = importlib.import_module(
                        f"vnpy_ctastrategy.strategies.{modname}"
                    )
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
            self._strategy_combo.addItem("（未找到策略类，请手动填写）")

    # ------------------------------------------------------------------ #
    #  Validation & result extraction
    # ------------------------------------------------------------------ #

    def _on_accept(self) -> None:
        errors = self._validate()
        if errors:
            QtWidgets.QMessageBox.warning(
                self, "参数错误", "\n".join(errors)
            )
            return
        self.accept()

    def _validate(self) -> list[str]:
        errors: list[str] = []
        if not self._pool_edit.toPlainText().strip():
            errors.append("股票池不能为空")
        qs = self._start_edit.date()
        qe = self._end_edit.date()
        start = (qs.year(), qs.month(), qs.day())
        end   = (qe.year(), qe.month(), qe.day())
        if start >= end:
            errors.append("结束日期必须晚于开始日期")
        try:
            float(self._rate_edit.text())
        except ValueError:
            errors.append("手续费率格式错误")
        try:
            float(self._slippage_edit.text())
        except ValueError:
            errors.append("滑点格式错误")
        return errors

    def get_config(self) -> dict:
        """
        Return a dict with two keys:
          - 'parameters': kwargs for BatchResearchEngine.set_parameters()
          - 'symbols':    list[str] for BatchResearchEngine.set_stock_pool()
          - 'use_multiprocess': bool
          - 'max_workers': int
        """
        name = self._strategy_combo.currentText()
        strategy_class = self._strategy_map.get(name)

        # Parse strategy settings
        setting: dict = {}
        for line in self._setting_edit.toPlainText().splitlines():
            line = line.strip()
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v_str = v.strip()
                try:
                    setting[k] = int(v_str)
                except ValueError:
                    try:
                        setting[k] = float(v_str)
                    except ValueError:
                        setting[k] = v_str

        # Parse symbol list
        raw = self._pool_edit.toPlainText()
        symbols = [
            s.strip()
            for s in raw.replace(",", "\n").splitlines()
            if s.strip()
        ]

        qstart = self._start_edit.date()
        qend = self._end_edit.date()

        return {
            "parameters": {
                "strategy_class":    strategy_class,
                "start":             datetime(qstart.year(), qstart.month(), qstart.day()),
                "end":               datetime(qend.year(), qend.month(), qend.day()),
                "capital":           int(self._capital_spin.value()),
                "rate":              float(self._rate_edit.text()),
                "slippage":          float(self._slippage_edit.text()),
                "size":              float(self._size_edit.text()),
                "pricetick":         float(self._pricetick_edit.text()),
                "strategy_setting":  setting,
            },
            "symbols":           symbols,
            "use_multiprocess":  self._mp_check.isChecked(),
            "max_workers":       self._workers_spin.value(),
        }

    def set_config(self, cfg: dict) -> None:
        """Pre-fill the dialog from a config dict (for editing)."""
        params = cfg.get("parameters", {})
        if "strategy_class" in params:
            name = params["strategy_class"].__name__
            idx = self._strategy_combo.findText(name)
            if idx >= 0:
                self._strategy_combo.setCurrentIndex(idx)

        if "start" in params:
            d = params["start"]
            self._start_edit.setDate(QtCore.QDate(d.year, d.month, d.day))
        if "end" in params:
            d = params["end"]
            self._end_edit.setDate(QtCore.QDate(d.year, d.month, d.day))
        if "capital" in params:
            self._capital_spin.setValue(float(params["capital"]))
        if "rate" in params:
            self._rate_edit.setText(str(params["rate"]))
        if "slippage" in params:
            self._slippage_edit.setText(str(params["slippage"]))
        if "size" in params:
            self._size_edit.setText(str(params["size"]))
        if "pricetick" in params:
            self._pricetick_edit.setText(str(params["pricetick"]))

        setting = params.get("strategy_setting", {})
        if setting:
            lines = "\n".join(f"{k}={v}" for k, v in setting.items())
            self._setting_edit.setPlainText(lines)

        symbols = cfg.get("symbols", [])
        if symbols:
            self._pool_edit.setPlainText("\n".join(symbols))

        if cfg.get("use_multiprocess"):
            self._mp_check.setChecked(True)
            self._workers_spin.setValue(cfg.get("max_workers", 4))
