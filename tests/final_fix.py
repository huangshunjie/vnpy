"""final_fix.py — 彻底清理，改用 tooltip 方案"""
import pathlib, ast, re

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

# ── 1. 删除 TwoLineHeader 类 ──────────────────────────────────────
m = re.search(r"\nclass TwoLineHeader\(QtWidgets\.QHeaderView\):.*?(?=\nclass )", src, re.DOTALL)
if m:
    src = src[:m.start()] + src[m.end()-1:]
    print("TwoLineHeader removed")
else:
    print("TwoLineHeader not found, skip")

# ── 2. FIELD_NAME_MAP 改成 "中文" : ("中文", "英文") 结构 ─────────
# 先整体替换掉整个字典
MAP_START = src.find("FIELD_NAME_MAP: dict = {")
MAP_END   = src.find("\n}\n", MAP_START) + 3
assert MAP_START != -1 and MAP_END != -1

NEW_MAP = '''FIELD_NAME_MAP: dict = {
    "inited":           ("已初始化",    "inited"),
    "trading":          ("运行中",      "trading"),
    "pos":              ("持仓",        "pos"),
    "atr_length":       ("ATR周期",     "atr_length"),
    "atr_ma_length":    ("ATR均线周期", "atr_ma_length"),
    "rsi_length":       ("RSI周期",     "rsi_length"),
    "rsi_entry":        ("RSI入场阈值", "rsi_entry"),
    "trailing_percent": ("跟踪止损%",   "trailing_percent"),
    "fixed_size":       ("固定手数",    "fixed_size"),
    "atr_value":        ("ATR值",       "atr_value"),
    "atr_ma":           ("ATR均线值",   "atr_ma"),
    "rsi_value":        ("RSI值",       "rsi_value"),
    "rsi_buy":          ("RSI买入线",   "rsi_buy"),
    "rsi_sell":         ("RSI卖出线",   "rsi_sell"),
    "intra_trade_high": ("持仓最高价",  "intra_trade_high"),
    "intra_trade_low":  ("持仓最低价",  "intra_trade_low"),
    "fast_window":      ("快线周期",    "fast_window"),
    "slow_window":      ("慢线周期",    "slow_window"),
    "fast_ma0":         ("快线当前值",  "fast_ma0"),
    "fast_ma1":         ("快线前值",    "fast_ma1"),
    "slow_ma0":         ("慢线当前值",  "slow_ma0"),
    "slow_ma1":         ("慢线前值",    "slow_ma1"),
    "boll_window":      ("布林周期",    "boll_window"),
    "boll_dev":         ("布林偏差",    "boll_dev"),
    "cci_window":       ("CCI周期",     "cci_window"),
    "atr_window":       ("ATR窗口",     "atr_window"),
    "sl_multiplier":    ("止损倍数",    "sl_multiplier"),
    "boll_up":          ("布林上轨",    "boll_up"),
    "boll_down":        ("布林下轨",    "boll_down"),
    "cci_value":        ("CCI值",       "cci_value"),
    "k1":               ("上轨系数",    "k1"),
    "k2":               ("下轨系数",    "k2"),
    "upper_bound":      ("上轨价",      "upper_bound"),
    "lower_bound":      ("下轨价",      "lower_bound"),
    "kk_window":        ("KK周期",      "kk_window"),
    "kk_dev":           ("KK偏差",      "kk_dev"),
    "kk_up":            ("KK上轨",      "kk_up"),
    "kk_down":          ("KK下轨",      "kk_down"),
    "entry_window":     ("入场窗口",    "entry_window"),
    "exit_window":      ("出场窗口",    "exit_window"),
    "entry_up":         ("入场上轨",    "entry_up"),
    "entry_down":       ("入场下轨",    "entry_down"),
    "exit_up":          ("出场上轨",    "exit_up"),
    "exit_down":        ("出场下轨",    "exit_down"),
    "fast_ma":          ("快线均值",    "fast_ma"),
    "slow_ma":          ("慢线均值",    "slow_ma"),
    "last_price":       ("最新价",      "last_price"),
    "highest_price":    ("持仓最高价",  "highest_price"),
}
'''
src = src[:MAP_START] + NEW_MAP + src[MAP_END:]
print("FIELD_NAME_MAP replaced")

# ── 3. 修复 DataMonitor.init_ui 里的标签生成逻辑 ──────────────────
# 旧：labels = [FIELD_NAME_MAP.get(k, k) for k in ...]
# 新：labels = [FIELD_NAME_MAP.get(k, (k, k))[0] for k in ...]  只取中文
OLD_LABEL = '        labels: list = [FIELD_NAME_MAP.get(k, k) for k in self._data.keys()]'
NEW_LABEL = '        labels: list = [FIELD_NAME_MAP.get(k, (k, k))[0] for k in self._data.keys()]'
assert OLD_LABEL in src, f"label line not found"
src = src.replace(OLD_LABEL, NEW_LABEL, 1)
print("labels line updated")

# ── 4. 在 setItem 后加 tooltip 设置 ──────────────────────────────
OLD_CELLS = (
    "        for column, name in enumerate(self._data.keys()):\n"
    "            value = self._data[name]\n"
    "\n"
    "            cell: QtWidgets.QTableWidgetItem = QtWidgets.QTableWidgetItem(str(value))\n"
    "            cell.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)\n"
    "\n"
    "            self.setItem(0, column, cell)\n"
    "            self.cells[name] = cell\n"
)
NEW_CELLS = (
    "        for column, name in enumerate(self._data.keys()):\n"
    "            value = self._data[name]\n"
    "\n"
    "            cell: QtWidgets.QTableWidgetItem = QtWidgets.QTableWidgetItem(str(value))\n"
    "            cell.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)\n"
    "\n"
    "            self.setItem(0, column, cell)\n"
    "            self.cells[name] = cell\n"
    "\n"
    "            zh, en = FIELD_NAME_MAP.get(name, (name, name))\n"
    "            tip = QtWidgets.QTableWidgetItem()\n"
    "            tip.setToolTip(f\"{zh}\\n{en}\")\n"
    "            self.setHorizontalHeaderItem(column, tip)\n"
    "            self.horizontalHeaderItem(column).setText(zh)\n"
)
assert OLD_CELLS in src, "cells block not found"
src = src.replace(OLD_CELLS, NEW_CELLS, 1)
print("tooltip block added")

# ── 5. 清理残留的 TwoLineHeader 相关 header 设置，恢复原生 header ──
LEFTOVER_TWOROW = (
    "        self.horizontalHeader().setSectionResizeMode(\n"
    "            QtWidgets.QHeaderView.ResizeMode.ResizeToContents\n"
    "        )\n"
    "        self.horizontalHeader().setStretchLastSection(False)\n"
    "        self.horizontalHeader().setMinimumSectionSize(80)\n"
    "        self.horizontalHeader().setMinimumHeight(48)\n"
    "        self.horizontalHeader().setDefaultAlignment(\n"
    "            QtCore.Qt.AlignmentFlag.AlignCenter\n"
    "        )\n"
)
if LEFTOVER_TWOROW in src:
    src = src.replace(LEFTOVER_TWOROW, "", 1)
    print("leftover header block removed")

LEFTOVER_SCROLL = (
    "        self.setHorizontalScrollBarPolicy(\n"
    "            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded\n"
    "        )\n"
    "        self.setWordWrap(True)\n"
)
CLEAN_SCROLL = (
    "        self.setHorizontalScrollBarPolicy(\n"
    "            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded\n"
    "        )\n"
)
if LEFTOVER_SCROLL in src:
    src = src.replace(LEFTOVER_SCROLL, CLEAN_SCROLL, 1)
    print("setWordWrap removed")

# ── 6. 语法验证并写入 ─────────────────────────────────────────────
ast.parse(src)
P.write_text(src, encoding="utf-8")
print(f"Done. Total lines: {len(src.splitlines())}")
