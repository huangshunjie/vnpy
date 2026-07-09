"""patch_cta_i18n.py — 给 DataMonitor 列标题加中文翻译"""
import pathlib, ast

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

# ── 1. 在文件顶部 import 块之后插入翻译字典 ───────────────────────
DICT_CODE = '''
FIELD_NAME_MAP: dict = {
    "inited":            "已初始化 inited",
    "trading":           "运行中 trading",
    "pos":               "持仓 pos",
    "atr_length":        "ATR周期 atr_length",
    "atr_ma_length":     "ATR均线周期 atr_ma_length",
    "rsi_length":        "RSI周期 rsi_length",
    "rsi_entry":         "RSI入场阈值 rsi_entry",
    "trailing_percent":  "跟踪止损% trailing_percent",
    "fixed_size":        "固定手数 fixed_size",
    "atr_value":         "ATR值 atr_value",
    "atr_ma":            "ATR均线值 atr_ma",
    "rsi_value":         "RSI值 rsi_value",
    "rsi_buy":           "RSI买入线 rsi_buy",
    "rsi_sell":          "RSI卖出线 rsi_sell",
    "intra_trade_high":  "持仓最高价 intra_trade_high",
    "intra_trade_low":   "持仓最低价 intra_trade_low",
    "fast_window":       "快线周期 fast_window",
    "slow_window":       "慢线周期 slow_window",
    "fast_ma0":          "快线当前 fast_ma0",
    "fast_ma1":          "快线前值 fast_ma1",
    "slow_ma0":          "慢线当前 slow_ma0",
    "slow_ma1":          "慢线前值 slow_ma1",
    "boll_window":       "布林周期 boll_window",
    "boll_dev":          "布林偏差 boll_dev",
    "cci_window":        "CCI周期 cci_window",
    "atr_window":        "ATR窗口 atr_window",
    "sl_multiplier":     "止损倍数 sl_multiplier",
    "boll_up":           "布林上轨 boll_up",
    "boll_down":         "布林下轨 boll_down",
    "cci_value":         "CCI值 cci_value",
    "k1":                "上轨系数 k1",
    "k2":                "下轨系数 k2",
    "upper_bound":       "上轨价 upper_bound",
    "lower_bound":       "下轨价 lower_bound",
    "kk_window":         "KK周期 kk_window",
    "kk_dev":            "KK偏差 kk_dev",
    "kk_up":             "KK上轨 kk_up",
    "kk_down":           "KK下轨 kk_down",
    "entry_window":      "入场窗口 entry_window",
    "exit_window":       "出场窗口 exit_window",
    "entry_up":          "入场上轨 entry_up",
    "entry_down":        "入场下轨 entry_down",
    "exit_up":           "出场上轨 exit_up",
    "exit_down":         "出场下轨 exit_down",
    "fast_ma":           "快线均值 fast_ma",
    "slow_ma":           "慢线均值 slow_ma",
    "last_price":        "最新价 last_price",
    "highest_price":     "持仓最高价 highest_price",
}
'''

# 找插入点：from .rollover import RolloverTool 之后
INSERT_ANCHOR = "from .rollover import RolloverTool"
assert INSERT_ANCHOR in src, "anchor not found"

if "FIELD_NAME_MAP" not in src:
    src = src.replace(
        INSERT_ANCHOR,
        INSERT_ANCHOR + "\n" + DICT_CODE,
        1
    )
    print("FIELD_NAME_MAP inserted")
else:
    print("FIELD_NAME_MAP already present, skipping insert")

# ── 2. 修改 DataMonitor.init_ui：用翻译字典替换列标题 ─────────────
OLD_LABELS = "        labels: list = list(self._data.keys())\n        self.setColumnCount(len(labels))\n        self.setHorizontalHeaderLabels(labels)"
NEW_LABELS = "        labels: list = [FIELD_NAME_MAP.get(k, k) for k in self._data.keys()]\n        self.setColumnCount(len(labels))\n        self.setHorizontalHeaderLabels(labels)"

if OLD_LABELS in src:
    src = src.replace(OLD_LABELS, NEW_LABELS, 1)
    print("DataMonitor labels patched")
elif NEW_LABELS in src:
    print("DataMonitor labels already patched")
else:
    # 尝试找到实际内容（防空白差异）
    import re
    pattern = r'(        labels: list = list\(self\._data\.keys\(\)\)\n        self\.setColumnCount\(len\(labels\)\)\n        self\.setHorizontalHeaderLabels\(labels\))'
    if re.search(pattern, src):
        src = re.sub(pattern, NEW_LABELS, src, count=1)
        print("DataMonitor labels patched via regex")
    else:
        print("ERROR: DataMonitor label pattern not found, printing context:")
        idx = src.find("setHorizontalHeaderLabels")
        print(repr(src[idx-200:idx+100]))
        raise AssertionError("Cannot find DataMonitor label block")

# ── 3. 语法验证并写入 ─────────────────────────────────────────────
ast.parse(src)
P.write_text(src, encoding="utf-8")
print(f"Done. Total lines: {len(src.splitlines())}")
