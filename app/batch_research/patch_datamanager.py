from datetime import datetime, timedelta
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from vnpy_datamanager.engine import ManagerEngine
from vnpy_datamanager.ui.widget import ManagerWidget
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import DB_TZ
from vnpy.trader.object import HistoryRequest
from vnpy.trader.ui import QtCore, QtWidgets

from .ui.bulk_download_dialog import BulkDownloadDialog

_A_SHARE_EXCHANGES = {Exchange.SSE, Exchange.SZSE, Exchange.BSE}

# 2000 积分：每分钟 200 次，留 5% 安全余量 → 190 次/分钟
_REQUESTS_PER_MINUTE = 190
_MAX_WORKERS         = 10   # 并发线程数


class _TokenBucket:
    """令牌桶：控制每分钟最大请求次数。"""

    def __init__(self, rate_per_minute: int) -> None:
        self._interval = 60.0 / rate_per_minute
        self._lock     = threading.Lock()
        self._next_allowed = time.monotonic()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                if now >= self._next_allowed:
                    self._next_allowed = now + self._interval
                    return
                wait = self._next_allowed - now
            time.sleep(wait)


def _bulk_download(self: ManagerWidget) -> None:
    dlg = BulkDownloadDialog(parent=self)
    dlg.exec_()


def _patched_init_ui(self: ManagerWidget) -> None:
    _original_init_ui(self)
    main_layout: QtWidgets.QVBoxLayout = self.layout()
    hbox: QtWidgets.QHBoxLayout = main_layout.itemAt(0).layout()

    bulk_btn = QtWidgets.QPushButton("下载全市场")
    bulk_btn.setToolTip("从 Tushare 批量下载全 A 股日线数据到本地数据库")
    bulk_btn.clicked.connect(lambda: _bulk_download(self))
    hbox.addWidget(bulk_btn)

    export_all_btn = QtWidgets.QPushButton("导出全部")
    export_all_btn.setToolTip("将数据库中所有 K 线数据导出为 CSV 文件（每只股票一个文件）")
    export_all_btn.clicked.connect(lambda: _export_all(self))
    hbox.addWidget(export_all_btn)


def _ensure_db_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=DB_TZ)
    return dt.astimezone(DB_TZ)


def _step(interval: Interval) -> timedelta:
    if interval == Interval.DAILY:
        return timedelta(days=1)
    if interval == Interval.HOUR:
        return timedelta(hours=1)
    if interval == Interval.MINUTE:
        return timedelta(minutes=1)
    return timedelta(0)


def _query_and_save_bars(
    self: ManagerEngine,
    symbol: str,
    exchange,
    interval: Interval,
    start: datetime,
    end: datetime,
    output,
) -> int:
    if start >= end:
        return 0

    req = HistoryRequest(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        start=start,
        end=end,
    )

    vt_symbol = f"{symbol}.{exchange.value}"
    contract = self.main_engine.get_contract(vt_symbol)

    if contract and contract.history_data:
        data = self.main_engine.query_history(req, contract.gateway_name)
    else:
        data = self.datafeed.query_bar_history(req, output)

    if data:
        self.database.save_bar_data(data)
        return len(data)
    return 0


def _patched_download_bar_data(
    self: ManagerEngine,
    symbol: str,
    exchange,
    interval,
    start: datetime,
    output,
) -> int:
    interval_obj = Interval(interval)
    start = _ensure_db_tz(start)

    if interval_obj == Interval.TICK or exchange not in _A_SHARE_EXCHANGES:
        return _original_download_bar_data(self, symbol, exchange, interval, start, output)

    now = datetime.now(DB_TZ)
    if start >= now:
        return 0

    try:
        overview = None
        for item in self.database.get_bar_overview():
            if (
                item.symbol == symbol
                and item.exchange == exchange
                and item.interval == interval_obj
            ):
                overview = item
                break
    except Exception as e:
        output(f"检查本地已有数据失败，将按原始开始日期下载：{e}")
        return _original_download_bar_data(self, symbol, exchange, interval_obj, start, output)

    if not overview:
        return _query_and_save_bars(
            self, symbol, exchange, interval_obj, start, now, output
        )

    step = _step(interval_obj)
    local_start = _ensure_db_tz(overview.start)
    local_end   = _ensure_db_tz(overview.end)
    total_count = 0

    if start < local_start:
        pre_end = local_start - step
        total_count += _query_and_save_bars(
            self, symbol, exchange, interval_obj, start, pre_end, output
        )

    post_start = max(start, local_end + step)
    if post_start < now:
        total_count += _query_and_save_bars(
            self, symbol, exchange, interval_obj, post_start, now, output
        )

    return total_count


class _UpdateWorker(QtCore.QThread):
    """多线程并发更新，令牌桶限速到 _REQUESTS_PER_MINUTE 次/分钟。"""

    sig_progress = QtCore.Signal(int, int)   # (done, total)
    sig_done     = QtCore.Signal(int, int)   # (updated, skipped)

    def __init__(self, engine: ManagerEngine) -> None:
        super().__init__()
        self._engine = engine
        self._stop   = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        overviews = [
            ov for ov in self._engine.get_bar_overview()
            if ov.exchange in _A_SHARE_EXCHANGES
        ]
        total   = len(overviews)
        updated = 0
        skipped = 0
        done    = 0
        lock    = threading.Lock()

        bucket = _TokenBucket(_REQUESTS_PER_MINUTE)

        def fetch_one(ov) -> int:
            """在工作线程里执行，返回下载到的 K 线条数。"""
            if self._stop:
                return -1
            bucket.acquire()            # 限速
            if self._stop:
                return -1
            try:
                return self._engine.download_bar_data(
                    ov.symbol, ov.exchange, ov.interval, ov.end,
                    lambda msg: None,   # 多线程里不弹窗
                )
            except Exception:
                return 0

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {pool.submit(fetch_one, ov): ov for ov in overviews}

            for future in as_completed(futures):
                if self._stop:
                    break

                count = future.result()
                with lock:
                    done += 1
                    if count and count > 0:
                        updated += 1
                    else:
                        skipped += 1
                self.sig_progress.emit(done, total)

        self.sig_done.emit(updated, skipped)


def _patched_update_data(self: ManagerWidget) -> None:
    overviews = self.engine.get_bar_overview()
    non_a = sum(1 for ov in overviews if ov.exchange not in _A_SHARE_EXCHANGES)

    dialog = QtWidgets.QProgressDialog("历史数据更新中", "取消", 0, 100)
    dialog.setWindowTitle("更新进度")
    dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
    dialog.setMinimumWidth(360)
    dialog.setValue(0)

    worker = _UpdateWorker(self.engine)

    def on_progress(done: int, total: int) -> None:
        if dialog.wasCanceled():
            worker.stop()
            return
        pct = int(done / total * 100) if total else 100
        elapsed_hint = f"  ({_REQUESTS_PER_MINUTE}次/分并发)"
        dialog.setValue(pct)
        dialog.setLabelText(f"历史数据更新中  {done}/{total}{elapsed_hint}")
        QtWidgets.QApplication.processEvents()

    def on_done(updated: int, skipped: int) -> None:
        dialog.close()
        QtWidgets.QMessageBox.information(
            self, "更新完成",
            f"更新完成\n"
            f"有新数据：{updated} 只\n"
            f"已是最新（无新增）：{skipped} 只\n"
            f"跳过（非 A 股品种）：{non_a} 只"
        )

    worker.sig_progress.connect(on_progress)
    worker.sig_done.connect(on_done)
    worker.start()
    dialog.exec()

    if not worker.isFinished():
        worker.stop()
        worker.wait(5000)



class _ExportAllWorker(QtCore.QThread):
    """后台线程：将数据库中所有 K 线数据导出为 CSV 文件。"""

    sig_progress = QtCore.Signal(int, int)    # (done, total)
    sig_done     = QtCore.Signal(int, int, int)  # (success, failed, skipped)

    def __init__(self, engine: ManagerEngine, output_dir: str) -> None:
        super().__init__()
        self._engine     = engine
        self._output_dir = output_dir
        self._stop       = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        import csv as _csv
        from pathlib import Path as _Path

        overviews = self._engine.get_bar_overview()
        total   = len(overviews)
        success = 0
        failed  = 0
        skipped = 0

        for i, ov in enumerate(overviews):
            if self._stop:
                break

            fname = f"{ov.symbol}.{ov.exchange.value}_{ov.interval.value}.csv"
            fpath = str(_Path(self._output_dir) / fname)

            result = self._engine.output_data_to_csv(
                fpath,
                ov.symbol,
                ov.exchange,
                ov.interval,
                ov.start,
                ov.end,
            )
            if result:
                success += 1
            else:
                failed += 1

            self.sig_progress.emit(i + 1, total)

        self.sig_done.emit(success, failed, skipped)


def _export_all(self: ManagerWidget) -> None:
    """一键导出数据库中所有 K 线数据到选定目录，每只股票一个 CSV 文件。"""
    overviews = self.engine.get_bar_overview()
    if not overviews:
        QtWidgets.QMessageBox.information(self, "无数据", "数据库中暂无 K 线数据。")
        return

    output_dir = QtWidgets.QFileDialog.getExistingDirectory(
        self, "选择导出目录", ""
    )
    if not output_dir:
        return

    dialog = QtWidgets.QProgressDialog("正在导出数据...", "取消", 0, 100)
    dialog.setWindowTitle("导出进度")
    dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
    dialog.setMinimumWidth(400)
    dialog.setValue(0)

    worker = _ExportAllWorker(self.engine, output_dir)

    def on_progress(done: int, total: int) -> None:
        if dialog.wasCanceled():
            worker.stop()
            return
        pct = int(done / total * 100) if total else 100
        dialog.setValue(pct)
        dialog.setLabelText(f"正在导出数据...  {done}/{total}")
        QtWidgets.QApplication.processEvents()

    def on_done(success: int, failed: int, skipped: int) -> None:
        dialog.close()
        msg = (
            f"导出完成\n"
            f"成功：{success} 只\n"
            f"失败（文件被占用）：{failed} 只\n"
            f"输出目录：{output_dir}"
        )
        QtWidgets.QMessageBox.information(self, "导出完成", msg)

    worker.sig_progress.connect(on_progress)
    worker.sig_done.connect(on_done)
    worker.start()
    dialog.exec()

    if not worker.isFinished():
        worker.stop()
        worker.wait(5000)


_original_init_ui           = ManagerWidget.init_ui
_original_download_bar_data = ManagerEngine.download_bar_data

ManagerWidget.init_ui           = _patched_init_ui
ManagerWidget.update_data       = _patched_update_data
ManagerEngine.download_bar_data = _patched_download_bar_data
