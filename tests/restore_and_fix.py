"""restore_and_fix.py — 恢复文件并精确修改 FIELD_NAME_MAP"""
import pathlib, ast

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

# ── 1. 找到 FIELD_NAME_MAP 的起止位置，只替换字典内容 ────────────
MAP_START = "FIELD_NAME_MAP: dict = {"
MAP_END   = "}\n\n\nclass CtaManager"

start_idx = src.find(MAP_START)
end_idx   = src.find(MAP_END, start_idx) + 1  # 包含 "}"

assert start_idx != -1, "FIELD_NAME_MAP start not found"
assert end_idx   != -1, "FIELD_NAME_MAP end not found"

NEW_MAP = '''FIELD_NAME_MAP: dict = {
    "inited":            "已初始化\\ninited",
    "trading":           "运行中\\ntrading",
    "pos":               "持仓\\npos",
    "atr_length":        "ATR周期\\natr_length",
    "atr_ma_length":     "ATR均线周期\\natr_ma_length",
    "rsi_length":        "RSI周期\\nrsi_length",
    "rsi_entry":         "RSI入场阈值\\nrsi_entry",
    "trailing_percent":  "跟踪止损%\\ntrailing_percent",
    "fixed_size":        "固定手数\\nfixed_size",
    "atr_value":         "ATR值\\natr_value",
    "atr_ma":            "ATR均线值\\natr_ma",
    "rsi_value":         "RSI值\\nrsi_value",
    "rsi_buy":           "RSI买入线\\nrsi_buy",
    "rsi_sell":          "RSI卖出线\\nrsi_sell",
    "intra_trade_high":  "持仓最高价\\nintra_trade_high",
    "intra_trade_low":   "持仓最低价\\nintra_trade_low",
    "fast_window":       "快线周期\\nfast_window",
    "slow_window":       "慢线周期\\nslow_window",
    "fast_ma0":          "快线当前\\nfast_ma0",
    "fast_ma1":          "快线前值\\nfast_ma1",
    "slow_ma0":          "慢线当前\\nslow_ma0",
    "slow_ma1":          "慢线前值\\nslow_ma1",
    "boll_window":       "布林周期\\nboll_window",
    "boll_dev":          "布林偏差\\nboll_dev",
    "cci_window":        "CCI周期\\ncci_window",
    "atr_window":        "ATR窗口\\natr_window",
    "sl_multiplier":     "止损倍数\\nsl_multiplier",
    "boll_up":           "布林上轨\\nboll_up",
    "boll_down":         "布林下轨\\nboll_down",
    "cci_value":         "CCI值\\ncci_value",
    "k1":                "上轨系数\\nk1",
    "k2":                "下轨系数\\nk2",
    "upper_bound":       "上轨价\\nupper_bound",
    "lower_bound":       "下轨价\\nlower_bound",
    "kk_window":         "KK周期\\nkk_window",
    "kk_dev":            "KK偏差\\nkk_dev",
    "kk_up":             "KK上轨\\nkk_up",
    "kk_down":           "KK下轨\\nkk_down",
    "entry_window":      "入场窗口\\nentry_window",
    "exit_window":       "出场窗口\\nexit_window",
    "entry_up":          "入场上轨\\nentry_up",
    "entry_down":        "入场下轨\\nentry_down",
    "exit_up":           "出场上轨\\nexit_up",
    "exit_down":         "出场下轨\\nexit_down",
    "fast_ma":           "快线均值\\nfast_ma",
    "slow_ma":           "慢线均值\\nslow_ma",
    "last_price":        "最新价\\nlast_price",
    "highest_price":     "持仓最高价\\nhighest_price",
}'''

src = src[:start_idx] + NEW_MAP + src[end_idx:]

# ── 2. DataMonitor.init_ui：设置 wordwrap + 行高，不用 TwoLineHeader ──
# 找到 setHorizontalHeader 相关块，确保使用默认 header + wordwrap
OLD_TWOROW = (
    "        two_line_header = TwoLineHeader(\n"
    "            QtCore.Qt.Orientation.Horizontal, self\n"
    "        )\n"
    "        two_line_header.setSectionResizeMode(\n"
    "            QtWidgets.QHeaderView.ResizeMode.ResizeToContents\n"
    "        )\n"
    "        two_line_header.setStretchLastSection(False)\n"
    "        two_line_header.setMinimumSectionSize(80)\n"
    "        self.setHorizontalHeader(two_line_header)\n"
    "        self.horizontalHeader().setMinimumHeight(44)\n"
)
NEW_NATIVE = (
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
if OLD_TWOROW in src:
    src = src.replace(OLD_TWOROW, NEW_NATIVE, 1)
    print("TwoLineHeader block replaced with native header")
elif NEW_NATIVE in src:
    print("Native header block already present")
else:
    print("WARNING: header block not found, check manually")

# ── 3. 确保有 setWordWrap ─────────────────────────────────────────
if "self.setWordWrap(True)" not in src:
    OLD_SCROLL = (
        "        self.setHorizontalScrollBarPolicy(\n"
        "            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded\n"
        "        )\n"
    )
    NEW_SCROLL = (
        "        self.setHorizontalScrollBarPolicy(\n"
        "            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded\n"
        "        )\n"
        "        self.setWordWrap(True)\n"
    )
    if OLD_SCROLL in src:
        src = src.replace(OLD_SCROLL, NEW_SCROLL, 1)
        print("setWordWrap(True) added")

# ── 4. 语法验证并写入 ─────────────────────────────────────────────
ast.parse(src)
P.write_text(src, encoding="utf-8")
print(f"Done. Total lines: {len(src.splitlines())}")
