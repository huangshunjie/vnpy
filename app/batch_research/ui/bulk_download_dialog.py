"""
ui/bulk_download_dialog.py

全市场 A 股日线数据批量下载对话框。

下载模式
────────
incremental  增量续接：从本地最新日期续接，已是最新则跳过
fill_gap     补全缺口：按指定区间下载并合并，不影响其他区间已有数据  ★
force_full   强制全量：忽略本地数据，重新下载指定区间
"""

from __future__ import annotations
import time
from datetime import datetime, timedelta

from vnpy.trader.ui import QtCore, QtGui, QtWidgets
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.database import get_database

MODE_INCREMENTAL = "incremental"
MODE_FILL_GAP    = "fill_gap"
MODE_FORCE_FULL  = "force_full"

_TS_EX_MAP = {
    "SSE":  Exchange.SSE,
    "SZSE": Exchange.SZSE,
    "BSE":  Exchange.BSE,
}


def _get_stock_list(token: str, exchange_filter: str) -> list[tuple[str, Exchange]]:
    import tushare as ts
    pro = ts.pro_api(token)
    stocks: list[tuple[str, Exchange]] = []
    for ts_ex, vt_ex in _TS_EX_MAP.items():
        if exchange_filter and exchange_filter != vt_ex.value:
            continue
        df = pro.stock_basic(
            exchange=ts_ex, list_status="L",
            fields="ts_code,symbol,name,exchange")
        for _, row in df.iterrows():
            stocks.append((row["symbol"], vt_ex))
    return stocks


class _DownloadWorker(QtCore.QThread):
    sig_log      = QtCore.Signal(str)
    sig_progress = QtCore.Signal(int, int)
    sig_done     = QtCore.Signal(int, int, int)

    def __init__(self, token, exchange_filter, start_dt, end_dt,
                 mode, batch_size, sleep_sec):
        super().__init__()
        self._token           = token
        self._exchange_filter = exchange_filter
        self._start_dt        = start_dt
        self._end_dt          = end_dt
        self._mode            = mode
        self._batch_size      = batch_size
        self._sleep_sec       = sleep_sec
        self._stop_flag       = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        datafeed = get_datafeed()
        database = get_database()

        overviews = database.get_bar_overview()
        have_end: dict[str, datetime] = {
            f"{o.symbol}.{o.exchange.value}": o.end
            for o in overviews if o.interval == Interval.DAILY
        }

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
        mode_desc = {"incremental": "增量续接",
                     "fill_gap":    "补全缺口",
                     "force_full":  "强制全量"}.get(self._mode, self._mode)

        self.sig_log.emit(
            f"共 {total} 只股票，开始下载 "
            f"{self._start_dt.date()} ~ {self._end_dt.date()}  模式：{mode_desc}")

        for i, (symbol, exchange) in enumerate(stocks):
            if self._stop_flag:
                self.sig_log.emit("用户已停止下载。")
                break

            vt_symbol = f"{symbol}.{exchange.value}"

            if self._mode == MODE_INCREMENTAL:
                if vt_symbol in have_end:
                    dl_start = have_end[vt_symbol] + timedelta(days=1)
                    if dl_start >= self._end_dt:
                        skipped += 1
                        self.sig_progress.emit(i + 1, total)
                        continue
                else:
                    dl_start = self._start_dt
            else:
                # fill_gap 和 force_full 都按指定区间下载
                dl_start = self._start_dt

            req = HistoryRequest(
                symbol=symbol, exchange=exchange,
                start=dl_start, end=self._end_dt,
                interval=Interval.DAILY)
            try:
                bars = datafeed.query_bar_history(req)
                if bars:
                    database.save_bar_data(bars)
                    success += 1
                    self.sig_log.emit(
                        f"[{i+1:4}/{total}] OK    {vt_symbol:<14} "
                        f"{len(bars):4} 根  "
                        f"{str(bars[0].datetime)[:10]} ~ {str(bars[-1].datetime)[:10]}")
                else:
                    skipped += 1
                    self.sig_log.emit(f"[{i+1:4}/{total}] EMPTY {vt_symbol}")
            except Exception as e:
                failed += 1
                self.sig_log.emit(f"[{i+1:4}/{total}] ERR   {vt_symbol}  {e}")

            self.sig_progress.emit(i + 1, total)
            if (i + 1) % self._batch_size == 0:
                time.sleep(self._sleep_sec)

        self.sig_done.emit(success, skipped, failed)


class BulkDownloadDialog(QtWidgets.QDialog):
    """全市场 A 股日线数据批量下载对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载全市场日线数据")
        self.setMinimumWidth(680)
        self.setMinimumHeight(560)
        self._worker = None
        self._init_ui()
        self._load_token()

    def _init_ui(self):
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(8)

        # 交易所
        self._ex_combo = QtWidgets.QComboBox()
        self._ex_combo.addItem("全部（SSE + SZSE + BSE）", "")
        self._ex_combo.addItem("沪市 SSE",   "SSE")
        self._ex_combo.addItem("深市 SZSE",  "SZSE")
        self._ex_combo.addItem("北交所 BSE", "BSE")
        form.addRow("交易所：", self._ex_combo)

        # 开始日期
        self._start_edit = QtWidgets.QDateEdit(QtCore.QDate(2010, 1, 1))
        self._start_edit.setCalendarPopup(True)
        self._start_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("开始日期：", self._start_edit)

        # 结束日期 + 今天按钮
        self._end_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self._end_edit.setCalendarPopup(True)
        self._end_edit.setDisplayFormat("yyyy-MM-dd")
        today_btn = QtWidgets.QPushButton("今天")
        today_btn.setFixedWidth(52)
        today_btn.setToolTip("将结束日期重置为今天")
        today_btn.clicked.connect(
            lambda: self._end_edit.setDate(QtCore.QDate.currentDate()))
        end_row = QtWidgets.QHBoxLayout()
        end_row.addWidget(self._end_edit)
        end_row.addWidget(today_btn)
        form.addRow("结束日期：", end_row)

        # ── 下载模式（三选一）──────────────────────────────────
        mode_group = QtWidgets.QGroupBox("下载模式")
        mode_vbox  = QtWidgets.QVBoxLayout(mode_group)
        mode_vbox.setSpacing(6)

        self._radio_incremental = QtWidgets.QRadioButton(
            "增量续接  —  从本地最新日期续接，已是最新则跳过")
        self._radio_fill_gap    = QtWidgets.QRadioButton(
            "补全缺口  —  按指定区间下载并写入，补充历史缺失数据  ★")
        self._radio_force_full  = QtWidgets.QRadioButton(
            "强制全量  —  忽略本地数据，重新下载指定区间全部数据")
        self._radio_incremental.setChecked(True)

        for r in [self._radio_incremental, self._radio_fill_gap, self._radio_force_full]:
            mode_vbox.addWidget(r)

        self._mode_hint = QtWidgets.QLabel()
        self._mode_hint.setWordWrap(True)
        self._mode_hint.setStyleSheet(
            "color:#888; font-size:11px; padding:2px 4px;")
        mode_vbox.addWidget(self._mode_hint)

        for r in [self._radio_incremental, self._radio_fill_gap, self._radio_force_full]:
            r.toggled.connect(self._update_mode_hint)
        self._update_mode_hint()

        # 高级参数
        adv_group = QtWidgets.QGroupBox("高级参数（Tushare 免费版保持默认即可）")
        adv_form  = QtWidgets.QFormLayout(adv_group)
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

        # 进度
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("就绪")
        self._progress_bar.setMinimumHeight(22)

        self._status_label = QtWidgets.QLabel("点击 [开始下载] 启动任务")
        self._status_label.setStyleSheet("color:#aaaaaa;")

        # 日志
        self._log_text = QtWidgets.QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumBlockCount(5000)
        self._log_text.setFont(QtGui.QFont("Consolas", 9))
        self._log_text.setMinimumHeight(200)

        # 按钮
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

        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(8)
        vbox.addLayout(form)
        vbox.addWidget(mode_group)
        vbox.addWidget(adv_group)
        vbox.addWidget(self._progress_bar)
        vbox.addWidget(self._status_label)
        vbox.addWidget(QtWidgets.QLabel("下载日志："))
        vbox.addWidget(self._log_text)
        vbox.addLayout(btn_row)
        self.setLayout(vbox)

    def _update_mode_hint(self):
        hints = {
            self._radio_incremental:
                "适合每天增量更新。本地已有 2026 年数据时，本日之前的全部跳过。",
            self._radio_fill_gap:
                "适合补充历史缺口（如补 2010~2020 的数据）。"
                "按指定区间下载并写入数据库，已有的自动合并，缺失的补入。"
                "不影响 2020 年以后已有的数据。",
            self._radio_force_full:
                "强制重新下载指定区间全部数据，耗时较长，仅在数据损坏时使用。",
        }
        for radio, hint in hints.items():
            if radio.isChecked():
                self._mode_hint.setText(hint)
                break

    def _load_token(self):
        try:
            from vnpy.trader.setting import SETTINGS
            self._token = SETTINGS.get("datafeed.password", "")
        except Exception:
            self._token = ""

    def _current_mode(self):
        if self._radio_fill_gap.isChecked():
            return MODE_FILL_GAP
        if self._radio_force_full.isChecked():
            return MODE_FORCE_FULL
        return MODE_INCREMENTAL

    def _on_start(self):
        if not self._token:
            QtWidgets.QMessageBox.warning(
                self, "缺少 Token",
                "未找到 Tushare Token。\n"
                "请在 VeighNa 主窗口 → 配置 → 全局配置 中填写：\n"
                "  datafeed.name     = tushare\n"
                "  datafeed.password = <你的 token>")
            return

        qs = self._start_edit.date()
        qe = self._end_edit.date()
        start_dt = datetime(qs.year(), qs.month(), qs.day())
        end_dt   = datetime(qe.year(), qe.month(), qe.day())

        if start_dt >= end_dt:
            QtWidgets.QMessageBox.warning(
                self, "日期错误", "结束日期必须晚于开始日期")
            return

        mode = self._current_mode()

        # 增量模式下，结束日期比今天早超过 30 天时提醒
        if mode == MODE_INCREMENTAL:
            today = datetime.today().replace(
                hour=0, minute=0, second=0, microsecond=0)
            days_behind = (today - end_dt).days
            if days_behind > 30:
                ret = QtWidgets.QMessageBox.warning(
                    self, "结束日期偏早",
                    f"增量模式下，结束日期 {end_dt.date()} 比今天早了 {days_behind} 天。\n\n"
                    "本地已有 2026 年数据时，所有股票都会被跳过。\n\n"
                    "建议改用「补全缺口」模式，或将结束日期改为今天。\n\n"
                    f"是否将结束日期自动改为今天（{today.date()}）并继续？",
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No
                    | QtWidgets.QMessageBox.StandardButton.Cancel)
                if ret == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return
                if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                    end_dt = today
                    self._end_edit.setDate(
                        QtCore.QDate(today.year, today.month, today.day))

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
            mode            = mode,
            batch_size      = self._batch_spin.value(),
            sleep_sec       = self._sleep_spin.value(),
        )
        self._worker.sig_log.connect(self._on_log)
        self._worker.sig_progress.connect(self._on_progress)
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()

    def _on_stop(self):
        if self._worker:
            self._worker.stop()
        self._btn_stop.setEnabled(False)
        self._status_label.setText("正在等待当前任务完成后停止...")

    def _on_log(self, msg):
        self._log_text.appendPlainText(msg)
        sb = self._log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_progress(self, completed, total):
        pct = int(completed / total * 100) if total else 0
        self._progress_bar.setValue(pct)
        self._progress_bar.setFormat(f"完成 {pct}%")
        self._status_label.setText(f"已处理 {completed} / {total} 只")

    def _on_done(self, success, skipped, failed):
        total = success + skipped + failed
        self._progress_bar.setValue(100)
        self._progress_bar.setFormat("完成 100%")
        self._status_label.setText(
            f"完成：成功 {success}  跳过 {skipped}  失败 {failed}  共 {total} 只")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._log_text.appendPlainText(
            f"\n{'─'*50}\n"
            f"下载完成：成功 {success} / 跳过 {skipped} / 失败 {failed} / 共 {total} 只\n"
            f"{'─'*50}")

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            ret = QtWidgets.QMessageBox.question(
                self, "下载进行中",
                "下载任务还在运行，确定要关闭吗？\n关闭后当前批次完成后会自动停止。",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No)
            if ret == QtWidgets.QMessageBox.StandardButton.No:
                event.ignore()
                return
            self._worker.stop()
        event.accept()
