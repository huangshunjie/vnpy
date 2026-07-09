"""patch_cta_widget.py — 给 CTA策略窗口加"下载数据"按钮"""
import pathlib, ast

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

# ── 1. hbox1 里在 roll_button 后加 download_button ────────────────
old_hbox = (
        "        hbox1.addWidget(roll_button)\n"
)
new_hbox = (
        "        hbox1.addWidget(roll_button)\n"
        "        hbox1.addWidget(download_button)\n"
)
assert old_hbox in src, "hbox1 pattern not found"
src = src.replace(old_hbox, new_hbox, 1)

# ── 2. 在 roll_button 定义后面插入 download_button 定义 ───────────
old_btn = (
        "        roll_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_(\"移仓助手\"))\n"
        "        roll_button.clicked.connect(self.roll)\n"
)
new_btn = (
        "        roll_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_(\"移仓助手\"))\n"
        "        roll_button.clicked.connect(self.roll)\n"
        "\n"
        "        download_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_(\"下载数据\"))\n"
        "        download_button.clicked.connect(self.download_data)\n"
)
assert old_btn in src, "roll_button pattern not found"
src = src.replace(old_btn, new_btn, 1)

# ── 3. 在 roll() 方法后面插入 download_data() 方法 ────────────────
old_roll = (
        "    def roll(self) -> None:\n"
        "        \"\"\"\"\"\"\n"
        "        dialog: RolloverTool = RolloverTool(self)\n"
        "        dialog.exec_()\n"
)
new_roll = (
        "    def roll(self) -> None:\n"
        "        \"\"\"\"\"\"\n"
        "        dialog: RolloverTool = RolloverTool(self)\n"
        "        dialog.exec_()\n"
        "\n"
        "    def download_data(self) -> None:\n"
        "        \"\"\"\"\"\"\n"
        "        dialog: DownloadDialog = DownloadDialog(self.main_engine, self)\n"
        "        dialog.exec_()\n"
)
assert old_roll in src, "roll() pattern not found"
src = src.replace(old_roll, new_roll, 1)

# ── 4. 在文件末尾追加 DownloadDialog 类 ──────────────────────────
DIALOG_CLS = '''

class DownloadDialog(QtWidgets.QDialog):
    """下载历史数据对话框（内嵌在 CTA策略窗口）"""

    def __init__(self, main_engine: MainEngine, parent=None) -> None:
        super().__init__(parent)
        self.main_engine = main_engine
        self.setWindowTitle("下载历史数据")
        self.setMinimumWidth(360)
        self._init_ui()

    def _init_ui(self) -> None:
        form = QtWidgets.QFormLayout()

        # 代码
        self.symbol_edit = QtWidgets.QLineEdit("600519")
        form.addRow("代码", self.symbol_edit)

        # 交易所
        self.exchange_combo = QtWidgets.QComboBox()
        from vnpy.trader.constant import Exchange
        for ex in Exchange:
            self.exchange_combo.addItem(ex.value, ex)
        self.exchange_combo.setCurrentText("SSE")
        form.addRow("交易所", self.exchange_combo)

        # 周期
        self.interval_combo = QtWidgets.QComboBox()
        from vnpy.trader.constant import Interval
        for iv in Interval:
            self.interval_combo.addItem(iv.value, iv)
        self.interval_combo.setCurrentText("d")
        form.addRow("周期", self.interval_combo)

        # 开始日期
        self.start_edit = QtWidgets.QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDate(QtCore.QDate(2020, 1, 1))
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("开始日期", self.start_edit)

        # 按钮行
        btn_box = QtWidgets.QHBoxLayout()
        self.download_btn = QtWidgets.QPushButton("下载")
        self.download_btn.clicked.connect(self._on_download)
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(self.download_btn)
        btn_box.addWidget(close_btn)

        # 日志区
        self.log_edit = QtWidgets.QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFixedHeight(120)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addLayout(form)
        vbox.addLayout(btn_box)
        vbox.addWidget(self.log_edit)

    def _log(self, msg: str) -> None:
        self.log_edit.append(
            f"[{datetime.now().strftime('%H:%M:%S')}]  {msg}"
        )
        QtWidgets.QApplication.processEvents()

    def _on_download(self) -> None:
        from vnpy.trader.constant import Exchange, Interval
        from vnpy.trader.object import HistoryRequest

        symbol   = self.symbol_edit.text().strip()
        exchange = self.exchange_combo.currentData()
        interval = self.interval_combo.currentData()
        start    = self.start_edit.date().toPython()

        if not symbol:
            QtWidgets.QMessageBox.warning(self, "提示", "请填写合约代码")
            return

        self.download_btn.setEnabled(False)
        self._log(f"开始下载 {symbol}.{exchange.value} {interval.value} 从 {start}")

        try:
            datafeed = self.main_engine.datafeed
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=datetime.combine(start, datetime.min.time()),
                end=datetime.now(),
            )
            data = datafeed.query_bar_history(req, self._log)

            if data:
                database = self.main_engine.database
                database.save_bar_data(data)
                self._log(f"下载完成，共 {len(data)} 根K线已存入数据库")
            else:
                self._log("未获取到数据，请检查代码和交易所是否正确")
        except Exception as e:
            self._log(f"下载失败: {e}")
        finally:
            self.download_btn.setEnabled(True)
'''

if "class DownloadDialog" not in src:
    src = src.rstrip() + "\n" + DIALOG_CLS + "\n"

# ── 5. 语法验证 ───────────────────────────────────────────────────
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("patch OK, lines:", len(src.splitlines()))
