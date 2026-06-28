"""
ui/bulk_download_dialog.py

全市场 A 股日线数据批量下载对话框。
- 后台线程下载，不阻塞 UI
- 实时进度条 + 日志窗口
- 支持增量更新（自动跳过已有数据）
- 支持暂停/继续/停止
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from vnpy.trader.ui import QtCore, QtGui, QtWidgets
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.database import get_database

if TYPE_CHECKING:
    pass

# Tushare 交易所代码 → VeighNa Exchange
_TS_EX_MAP = {
    "SSE":  Exchange.SSE,
    "SZSE": Exchange.SZSE,
    "BSE":  Exchange.BSE,
}


def _get_stock_list(token: str, exchange_filter: str) -> list[tuple[str, Exchange]]:
    """从 Tushare 获取全部上市 A 股列表。"""
    import tushare as ts
    pro = ts.pro_api(token)
    stocks: list[tuple[str, Exchange]] = []
    for ts_ex, vt_ex in _TS_EX_MAP.items():
        if exchange_filter and exchange_filter != vt_ex.value:
            continue
        df = pro.stock_basic(
            exchange=ts_ex,
            list_status="L",
            fields="ts_code,symbol,name,exchange",
        )
        for _, row in df.iterrows():
            stocks.append((row["symbol"], vt_ex))
    return stocks


class _DownloadWorker(QtCore.QThread):
    """后台下载线程，通过 Signal 向 UI 汇报进度。"""

    sig_log      = QtCore.Signal(str)          # 日志文本
    sig_progress = QtCore.Signal(int, int)     # (completed, total)
    sig_done     = QtCore.Signal(int, int, int)  # (success, skipped, failed)

    def __init__(
        self,
        token: str,
        exchange_filter: str,
        start_dt: datetime,
        end_dt: datetime,
        update_mode: bool,
        batch_size: int,
        sleep_sec: float,
    ) -> None:
        super().__init__()
        self._token          = token
        self._exchange_filter = exchange_filter
        self._start_dt       = start_dt
        self._end_dt         = end_dt
        self._update_mode    = update_mode
        self._batch_size     = batch_size
        self._sleep_sec      = sleep_sec
        self._stop_flag      = False

    def stop(self) -> None:
        self._stop_flag = True

    def run(self) -> None:
        datafeed = get_datafeed()
        database = get_database()

        # 查询已有数据
        overviews = database.get_bar_overview()
        have: dict[str, datetime] = {
            f"{o.symbol}.{o.exchange.value}": o.end
            for o in overviews if o.interval == Interval.DAILY
        }

        # 获取股票列表
        self.sig_log.emit("正在获取 A 股列表...")
        try:
            stocks = _get_stock_list(self._token, self._exchange_filter)
        except Exception as e:
            self.sig_log.emit(f"获取股票列表失败：{e}")
            self.sig_done.emit(0, 0, 0)
            return

        total   = len(stocks)
        success = 0
        skipped = 0
        failed  = 0

        self.sig_log.emit(
            f"共 {total} 只股票，开始下载 "
            f"{self._start_dt.date()} ~ {self._end_dt.date()}"
        )

        for i, (symbol, exchange) in enumerate(stocks):
            if self._stop_flag:
                self.sig_log.emit("用户已停止下载。")
                break

            vt_symbol = f"{symbol}.{exchange.value}"

            # 增量模式：已有且不需要更新 → 跳过
            if not self._update_mode and vt_symbol in have:
                skipped += 1
                self.sig_progress.emit(i + 1, total)
                continue

            # 增量更新：只下最新日期之后的数据
            dl_start = self._start_dt
            if self._update_mode and vt_symbol in have:
                dl_start = have[vt_symbol] + timedelta(days=1)
                if dl_start >= self._end_dt:
                    skipped += 1
                    self.sig_progress.emit(i + 1, total)
                    continue

            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                start=dl_start,
                end=self._end_dt,
                interval=Interval.DAILY,
            )
            try:
                bars = datafeed.query_bar_history(req)
                if bars:
                    database.save_bar_data(bars)
                    success += 1
                    self.sig_log.emit(
                        f"[{i+1:4}/{total}] OK    {vt_symbol:<14} "
                        f"{len(bars):4} 根  "
                        f"{str(bars[0].datetime)[:10]} ~ {str(bars[-1].datetime)[:10]}"
                    )
                else:
                    failed += 1
                    self.sig_log.emit(f"[{i+1:4}/{total}] EMPTY {vt_symbol}")
            except Exception as e:
                failed += 1
                self.sig_log.emit(f"[{i+1:4}/{total}] ERR   {vt_symbol}  {e}")

            self.sig_progress.emit(i + 1, total)

            # 批次限频
            if (i + 1) % self._batch_size == 0:
                time.sleep(self._sleep_sec)

        self.sig_done.emit(success, skipped, failed)


class BulkDownloadDialog(QtWidgets.QDialog):
    """
    全市场 A 股日线数据批量下载对话框。
    点击"开始下载"后在后台线程执行，UI 保持响应。
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("下载全市场日线数据")
        self.setMinimumWidth(660)
        self.setMinimumHeight(520)
        self._worker: _DownloadWorker | None = None
        self._init_ui()
        self._load_token()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        # ── 参数区 ──────────────────────────────────────────────
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(6)

        # 交易所
        self._ex_combo = QtWidgets.QComboBox()
        self._ex_combo.addItem("全部（SSE + SZSE + BSE）", "")
        self._ex_combo.addItem("沪市 SSE",  "SSE")
        self._ex_combo.addItem("深市 SZSE", "SZSE")
        self._ex_combo.addItem("北交所 BSE","BSE")
        form.addRow("交易所：", self._ex_combo)

        # 时间范围
        self._start_edit = QtWidgets.QDateEdit(QtCore.QDate(2020, 1, 1))
        self._start_edit.setCalendarPopup(True)
        self._start_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("开始日期：", self._start_edit)

        self._end_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self._end_edit.setCalendarPopup(True)
        self._end_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("结束日期：", self._end_edit)

        # 模式
        self._update_check = QtWidgets.QCheckBox(
            "增量更新（自动跳过已有数据，只下最新部分）")
        self._update_check.setChecked(True)
        form.addRow("下载模式：", self._update_check)

        # 高级参数
        adv_group = QtWidgets.QGroupBox("高级参数（Tushare 免费版保持默认即可）")
        adv_form = QtWidgets.QFormLayout(adv_group)
        adv_form.setVerticalSpacing(4)

        self._batch_spin = QtWidgets.QSpinBox()
        self._batch_spin.setRange(1, 200)
        self._batch_spin.setValue(20)
        adv_form.addRow("每批只数：", self._batch_spin)

        self._sleep_spin = QtWidgets.QDoubleSpinBox()
        self._sleep_spin.setRange(0.5, 30.0)
        self._sleep_spin.setValue(1.2)
        self._sleep_spin.setSingleStep(0.1)
        adv_form.addRow("批间休眠(秒)：", self._sleep_spin)

        # ── 进度区 ──────────────────────────────────────────────
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("就绪")
        self._progress_bar.setMinimumHeight(22)

        self._status_label = QtWidgets.QLabel('点击 [开始下载] 启动任务')
        self._status_label.setStyleSheet("color: #aaaaaa;")

        # ── 日志区 ──────────────────────────────────────────────
        self._log_text = QtWidgets.QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumBlockCount(5000)
        self._log_text.setFont(QtGui.QFont("Consolas", 9))
        self._log_text.setMinimumHeight(220)

        # ── 按钮区 ──────────────────────────────────────────────
        self._btn_start = QtWidgets.QPushButton("▶ 开始下载")
        self._btn_start.setDefault(True)
        self._btn_start.clicked.connect(self._on_start)

        self._btn_stop = QtWidgets.QPushButton("■ 停止")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)

        self._btn_close = QtWidgets.QPushButton("关闭")
        self._btn_close.clicked.connect(self.close)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_close)

        # ── 整体布局 ─────────────────────────────────────────────
        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(8)
        vbox.addLayout(form)
        vbox.addWidget(adv_group)
        vbox.addWidget(self._progress_bar)
        vbox.addWidget(self._status_label)
        vbox.addWidget(QtWidgets.QLabel("下载日志："))
        vbox.addWidget(self._log_text)
        vbox.addLayout(btn_row)
        self.setLayout(vbox)

    def _load_token(self) -> None:
        """从 VeighNa 全局配置读取 Tushare token。"""
        try:
            from vnpy.trader.setting import SETTINGS
            self._token = SETTINGS.get("datafeed.password", "")
        except Exception:
            self._token = ""

    # ------------------------------------------------------------------ #
    #  Slots
    # ------------------------------------------------------------------ #

    def _on_start(self) -> None:
        if not self._token:
            QtWidgets.QMessageBox.warning(
                self, "缺少 Token",
                "未找到 Tushare Token。\n"
                "请在 VeighNa 主窗口 → 配置 → 全局配置 中填写：\n"
                "  datafeed.name     = tushare\n"
                "  datafeed.password = <你的 token>"
            )
            return

        qs = self._start_edit.date()
        qe = self._end_edit.date()
        start_dt = datetime(qs.year(), qs.month(), qs.day())
        end_dt   = datetime(qe.year(), qe.month(), qe.day())

        if start_dt >= end_dt:
            QtWidgets.QMessageBox.warning(self, "日期错误", "结束日期必须晚于开始日期")
            return

        self._log_text.clear()
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("0%")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)

        self._worker = _DownloadWorker(
            token           = self._token,
            exchange_filter = self._ex_combo.currentData(),
            start_dt        = start_dt,
            end_dt          = end_dt,
            update_mode     = self._update_check.isChecked(),
            batch_size      = self._batch_spin.value(),
            sleep_sec       = self._sleep_spin.value(),
        )
        self._worker.sig_log.connect(self._on_log)
        self._worker.sig_progress.connect(self._on_progress)
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker:
            self._worker.stop()
        self._btn_stop.setEnabled(False)
        self._status_label.setText("正在等待当前任务完成后停止...")

    def _on_log(self, msg: str) -> None:
        self._log_text.appendPlainText(msg)
        sb = self._log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_progress(self, completed: int, total: int) -> None:
        pct = int(completed / total * 100) if total else 0
        self._progress_bar.setValue(pct)
        self._progress_bar.setFormat(f"{pct}%  {completed}/{total}")
        self._status_label.setText(f"已处理 {completed} / {total} 只")

    def _on_done(self, success: int, skipped: int, failed: int) -> None:
        total = success + skipped + failed
        self._progress_bar.setValue(100)
        self._progress_bar.setFormat("完成 100%")
        self._status_label.setText(
            f"完成：成功 {success}  跳过 {skipped}  失败 {failed}  共 {total} 只"
        )
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._log_text.appendPlainText(
            f"\n{'─'*50}\n"
            f"下载完成：成功 {success} / 跳过 {skipped} / 失败 {failed} / 共 {total} 只\n"
            f"{'─'*50}"
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._worker and self._worker.isRunning():
            ret = QtWidgets.QMessageBox.question(
                self, "下载进行中",
                "下载任务还在运行，确定要关闭吗？\n关闭后当前批次完成后会自动停止。",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            if ret == QtWidgets.QMessageBox.StandardButton.No:
                event.ignore()
                return
            self._worker.stop()
        event.accept()
