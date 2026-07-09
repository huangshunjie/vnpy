"""fix_download_dialog.py — 修复 DownloadDialog 的 datafeed/database 获取方式"""
import pathlib, ast

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

OLD = '''class DownloadDialog(QtWidgets.QDialog):
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
            self.download_btn.setEnabled(True)'''

NEW = '''class DownloadDialog(QtWidgets.QDialog):
    """下载历史数据对话框（内嵌在 CTA策略窗口）"""

    def __init__(self, main_engine: MainEngine, parent=None) -> None:
        super().__init__(parent)
        self.main_engine = main_engine
        self.setWindowTitle("下载历史数据")
        self.setMinimumWidth(380)
        self._init_ui()

    def _init_ui(self) -> None:
        from vnpy.trader.constant import Exchange, Interval
        form = QtWidgets.QFormLayout()

        self.symbol_edit = QtWidgets.QLineEdit("600519")
        form.addRow("代码", self.symbol_edit)

        self.exchange_combo = QtWidgets.QComboBox()
        for ex in Exchange:
            self.exchange_combo.addItem(ex.value, ex)
        self.exchange_combo.setCurrentText("SSE")
        form.addRow("交易所", self.exchange_combo)

        self.interval_combo = QtWidgets.QComboBox()
        for iv in Interval:
            self.interval_combo.addItem(iv.value, iv)
        self.interval_combo.setCurrentText("d")
        form.addRow("周期", self.interval_combo)

        self.start_edit = QtWidgets.QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDate(QtCore.QDate(2020, 1, 1))
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("开始日期", self.start_edit)

        btn_box = QtWidgets.QHBoxLayout()
        self.download_btn = QtWidgets.QPushButton("下载")
        self.download_btn.clicked.connect(self._on_download)
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(self.download_btn)
        btn_box.addWidget(close_btn)

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
        from vnpy.trader.datafeed import get_datafeed
        from vnpy.trader.database import get_database, DB_TZ
        from vnpy.trader.object import HistoryRequest
        from vnpy.trader.constant import Interval

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
            datafeed = get_datafeed()
            database = get_database()

            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=Interval(interval.value),
                start=datetime.combine(start, datetime.min.time()),
                end=datetime.now(DB_TZ),
            )
            data = datafeed.query_bar_history(req, self._log)

            if data:
                database.save_bar_data(data)
                self._log(f"下载完成，共 {len(data)} 根K线已存入数据库")
            else:
                self._log("未获取到数据，请检查代码和交易所是否正确")
        except Exception as e:
            self._log(f"下载失败: {e}")
        finally:
            self.download_btn.setEnabled(True)'''

assert OLD in src, "DownloadDialog class not found"
src = src.replace(OLD, NEW, 1)
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("fix OK, lines:", len(src.splitlines()))
