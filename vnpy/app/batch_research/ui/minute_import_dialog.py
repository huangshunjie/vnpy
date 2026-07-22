"""
ui/minute_import_dialog.py

分钟线数据包导入对话框。

从本地目录批量读取分钟线 CSV 文件，导入到 VeighNa 数据库。

数据包目录结构约定：
    {root}/
    └── {year}/
        ├── 1分钟/
        │   ├── sz000001.csv
        │   ├── sh600000.csv
        │   └── bj920000.csv
        ├── 5分钟/
        ├── 15分钟/
        ├── 30分钟/
        └── 60分钟/

文件名规则：{交易所前缀}{股票代码}.csv
    sz → SZSE（深圳）
    sh → SSE（上海）
    bj → BSE（北京）

CSV 列名（中文）：
    日期,开盘,最高,最低,收盘,成交量(股),成交额(元),...
"""

from __future__ import annotations

import csv
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Generator
from zoneinfo import ZoneInfo

from vnpy.trader.ui import QtCore, QtWidgets
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.trader.database import get_database

_TZ = ZoneInfo("Asia/Shanghai")

# 交易所前缀映射
_PREFIX_TO_EXCHANGE: dict[str, Exchange] = {
    "sz": Exchange.SZSE,
    "sh": Exchange.SSE,
    "bj": Exchange.BSE,
}

# 目录名 → Interval 映射
_DIR_TO_INTERVAL: dict[str, Interval] = {
    "1分钟":  Interval.MINUTE,
    "5分钟":  Interval.MINUTE_5,
    "15分钟": Interval.MINUTE_15,
    "30分钟": Interval.MINUTE_30,
    "60分钟": Interval.HOUR,
}

# 中文列名 → 标准键
_CN_COLUMN_MAP: dict[str, str] = {
    "日期":       "datetime",
    "开盘":       "open",
    "最高":       "high",
    "最低":       "low",
    "收盘":       "close",
    "成交量(股)": "volume",
    "成交额(元)": "turnover",
}

# 常见时间格式
_DATETIME_FORMATS: list[str] = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y%m%d %H:%M:%S",
    "%Y%m%d",
]

# 每批写入数据库的条数（避免单次 INSERT 太大）
_BATCH_SIZE = 5000


def _parse_datetime(raw: str) -> datetime | None:
    """解析时间字符串。"""
    raw = raw.strip()
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _parse_exchange_symbol(filename: str) -> tuple[Exchange, str] | None:
    """
    从文件名解析交易所和股票代码。
    例如: 'sz000001.csv' → (Exchange.SZSE, '000001')
    """
    stem = Path(filename).stem.lower()
    for prefix, exchange in _PREFIX_TO_EXCHANGE.items():
        if stem.startswith(prefix):
            symbol = stem[len(prefix):]
            if symbol:
                return exchange, symbol
    return None


def _load_csv_bars(
    filepath: Path,
    symbol: str,
    exchange: Exchange,
    interval: Interval,
) -> Generator[BarData, None, None]:
    """
    逐行读取 CSV 并 yield BarData 对象。
    跳过无法解析的行。
    """
    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return

        # 建立列名映射（原始列名 → 标准键）
        col_map: dict[str, str] = {}
        for field_name in reader.fieldnames:
            stripped = field_name.strip()
            if stripped in _CN_COLUMN_MAP:
                col_map[stripped] = _CN_COLUMN_MAP[stripped]

        # 检查必需列是否存在
        required = {"datetime", "open", "high", "low", "close", "volume"}
        mapped_keys = set(col_map.values())
        if not required.issubset(mapped_keys):
            return

        # 反转映射：标准键 → 原始列名
        std_to_orig: dict[str, str] = {v: k for k, v in col_map.items()}

        for row in reader:
            try:
                raw_dt = row.get(std_to_orig["datetime"], "").strip()
                if not raw_dt:
                    continue

                dt = _parse_datetime(raw_dt)
                if dt is None:
                    continue
                dt = dt.replace(tzinfo=_TZ)

                open_price = float(row.get(std_to_orig["open"], 0) or 0)
                high_price = float(row.get(std_to_orig["high"], 0) or 0)
                low_price = float(row.get(std_to_orig["low"], 0) or 0)
                close_price = float(row.get(std_to_orig["close"], 0) or 0)
                volume = float(row.get(std_to_orig["volume"], 0) or 0)
                turnover = float(row.get(std_to_orig.get("turnover", ""), 0) or 0)

                if close_price <= 0:
                    continue

                yield BarData(
                    gateway_name="CSV_IMPORT",
                    symbol=symbol,
                    exchange=exchange,
                    datetime=dt,
                    interval=interval,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    turnover=turnover,
                )
            except (ValueError, KeyError, TypeError):
                continue


class _ImportWorker(QtCore.QThread):
    """后台线程：批量导入分钟线 CSV 到数据库。"""

    sig_log = QtCore.Signal(str)
    sig_progress = QtCore.Signal(int, int)          # (done_files, total_files)
    sig_done = QtCore.Signal(int, int, int, int)    # (success, failed, skipped, total_bars)

    def __init__(
        self,
        data_dir: str,
        interval_dir: str,
        interval: Interval,
    ) -> None:
        super().__init__()
        self._data_dir = data_dir
        self._interval_dir = interval_dir
        self._interval = interval
        self._stop_flag = False

    def stop(self) -> None:
        self._stop_flag = True

    def run(self) -> None:
        database = get_database()
        data_path = Path(self._data_dir)

        # 收集所有 CSV 文件
        csv_files = sorted(data_path.glob("*.csv"))
        total = len(csv_files)

        if total == 0:
            self.sig_log.emit(f"目录中没有找到 CSV 文件：{data_path}")
            self.sig_done.emit(0, 0, 0, 0)
            return

        self.sig_log.emit(f"找到 {total} 个 CSV 文件，开始导入...")

        success = 0
        failed = 0
        skipped = 0
        total_bars = 0

        for i, csv_file in enumerate(csv_files):
            if self._stop_flag:
                self.sig_log.emit("用户取消导入")
                break

            # 解析文件名
            parsed = _parse_exchange_symbol(csv_file.name)
            if parsed is None:
                skipped += 1
                self.sig_progress.emit(i + 1, total)
                continue

            exchange, symbol = parsed

            try:
                bars_batch: list[BarData] = []
                file_bar_count = 0

                for bar in _load_csv_bars(
                    csv_file, symbol, exchange, self._interval
                ):
                    bars_batch.append(bar)
                    file_bar_count += 1

                    if len(bars_batch) >= _BATCH_SIZE:
                        database.save_bar_data(bars_batch)
                        bars_batch.clear()

                # 保存剩余的
                if bars_batch:
                    database.save_bar_data(bars_batch)

                if file_bar_count > 0:
                    success += 1
                    total_bars += file_bar_count
                else:
                    skipped += 1

            except Exception as e:
                failed += 1
                self.sig_log.emit(f"导入失败 {csv_file.name}: {e}")

            self.sig_progress.emit(i + 1, total)

        self.sig_done.emit(success, failed, skipped, total_bars)


class MinuteImportDialog(QtWidgets.QDialog):
    """分钟线数据包导入对话框。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("导入分钟线数据包")
        self.setMinimumWidth(520)
        self._worker: _ImportWorker | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        # --- 数据目录选择 ---
        dir_group = QtWidgets.QGroupBox("数据源")
        dir_layout = QtWidgets.QFormLayout(dir_group)

        self._edit_root = QtWidgets.QLineEdit(r"D:\vnpy_data_min")
        btn_browse = QtWidgets.QPushButton("浏览...")
        btn_browse.clicked.connect(self._on_browse)

        root_hbox = QtWidgets.QHBoxLayout()
        root_hbox.addWidget(self._edit_root, 1)
        root_hbox.addWidget(btn_browse)
        dir_layout.addRow("数据包根目录：", root_hbox)

        # 年份选择
        self._combo_year = QtWidgets.QComboBox()
        self._combo_year.setMinimumWidth(100)
        dir_layout.addRow("年份：", self._combo_year)

        # 频率选择
        self._combo_freq = QtWidgets.QComboBox()
        self._combo_freq.addItems(["1分钟", "5分钟", "15分钟", "30分钟", "60分钟"])
        dir_layout.addRow("K线频率：", self._combo_freq)

        layout.addWidget(dir_group)

        # 刷新年份列表
        btn_refresh = QtWidgets.QPushButton("刷新目录")
        btn_refresh.clicked.connect(self._refresh_years)
        dir_layout.addRow("", btn_refresh)

        # --- 进度区域 ---
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        self._log_text = QtWidgets.QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(150)
        layout.addWidget(self._log_text)

        # --- 按钮 ---
        btn_layout = QtWidgets.QHBoxLayout()
        self._btn_start = QtWidgets.QPushButton("开始导入")
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop = QtWidgets.QPushButton("停止")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_close = QtWidgets.QPushButton("关闭")
        btn_close.clicked.connect(self.close)

        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_start)
        btn_layout.addWidget(self._btn_stop)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        # 初始化年份
        self._refresh_years()

    def _on_browse(self) -> None:
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "选择分钟线数据包根目录", self._edit_root.text()
        )
        if dir_path:
            self._edit_root.setText(dir_path)
            self._refresh_years()

    def _refresh_years(self) -> None:
        """扫描根目录下的年份子目录。"""
        self._combo_year.clear()
        root = Path(self._edit_root.text())
        if not root.is_dir():
            return
        for item in sorted(root.iterdir()):
            if item.is_dir() and item.name.isdigit():
                self._combo_year.addItem(item.name)

    def _get_data_path(self) -> Path | None:
        """根据当前选项组合完整的数据目录路径。"""
        root = Path(self._edit_root.text())
        year = self._combo_year.currentText()
        freq = self._combo_freq.currentText()

        if not year or not freq:
            return None

        path = root / year / freq
        if not path.is_dir():
            return None
        return path

    def _on_start(self) -> None:
        data_path = self._get_data_path()
        if data_path is None:
            QtWidgets.QMessageBox.warning(
                self, "路径无效",
                f"数据目录不存在，请检查：\n"
                f"{self._edit_root.text()}/{self._combo_year.currentText()}"
                f"/{self._combo_freq.currentText()}"
            )
            return

        freq_name = self._combo_freq.currentText()
        interval = _DIR_TO_INTERVAL.get(freq_name, Interval.MINUTE)

        self._log_text.clear()
        self._log(f"数据目录：{data_path}")
        self._log(f"导入频率：{freq_name} → Interval.{interval.name}")

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._progress_bar.setValue(0)

        self._worker = _ImportWorker(
            data_dir=str(data_path),
            interval_dir=freq_name,
            interval=interval,
        )
        self._worker.sig_log.connect(self._log)
        self._worker.sig_progress.connect(self._on_progress)
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker:
            self._worker.stop()
            self._log("正在停止...")

    def _on_progress(self, done: int, total: int) -> None:
        pct = int(done / total * 100) if total else 100
        self._progress_bar.setValue(pct)
        self._progress_bar.setFormat(f"{done}/{total} ({pct}%)")

    def _on_done(self, success: int, failed: int, skipped: int, total_bars: int) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress_bar.setValue(100)

        self._log("=" * 40)
        self._log(f"导入完成!")
        self._log(f"  成功：{success} 个文件")
        self._log(f"  失败：{failed} 个文件")
        self._log(f"  跳过：{skipped} 个文件（无法解析或无有效数据）")
        self._log(f"  共写入：{total_bars:,} 条 K 线数据")

        QtWidgets.QMessageBox.information(
            self, "导入完成",
            f"导入完成\n\n"
            f"成功：{success} 个文件\n"
            f"失败：{failed} 个文件\n"
            f"跳过：{skipped} 个文件\n"
            f"共写入：{total_bars:,} 条 K 线"
        )

    def _log(self, msg: str) -> None:
        self._log_text.append(msg)

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)
        super().closeEvent(event)