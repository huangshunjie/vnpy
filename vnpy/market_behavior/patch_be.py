import pathlib

p = pathlib.Path(r'C:\Users\hdec\Documents\GitHub\vnpy\vnpy\vnpy\market_behavior\ui\behavior_editor.py')
src = p.read_text(encoding='utf-8', errors='replace')

# ── 1. 替换 COND_OPTIONS 为分组结构 ──────────────────────────────────
OLD_OPTS = '''COND_OPTIONS = [
    ("综合强度  kline_strength", "kline_strength", 0.40, "0\u22121\u5f97\u5206", "\u8d8a\u63a50\u6ee1\u5206\uff0c\u8d8a\u63a51\u8d8a\u5f3a"),
    ("\u4e0a\u6da8\u5929\u6570  rise_days",      "rise_days",      0.50, "0\u22121\u6bd4\u7387", "0.5 = \u7a97\u53e3\u5185\u81f3\u5c1150%\u5929\u6536\u6da8"),
    ("\u5927\u6da8\u6b21\u6570  rise_pct",       "rise_pct",       3.00, "% \u6da8\u5e45",   "3.0 = \u5355\u65e5\u6da8\u5e45\u22653%\uff0c\u81f3\u5c11\u51fa\u73b01\u6b21"),
    ("\u5927\u9633\u7ebf\u6570  big_yang_count", "big_yang_count", 2.00, "\u6b21\uff08\u6839\uff09",   "2.0 = \u7a97\u53e3\u5185\u81f3\u5c11\u51fa\u73b02\u6839\u5927\u9633\u7ebf"),
    ("\u6da8\u505c\u6b21\u6570  limit_up_count", "limit_up_count", 1.00, "\u6b21\u6570",     "1.0 = \u7a97\u53e3\u5185\u81f3\u5c11\u6da8\u505c1\u6b21"),
    ("\u7a81\u7834\u6b21\u6570  breakout_count", "breakout_count", 3.00, "\u6b21\u6570",     "3.0 = \u7a97\u53e3\u5185\u7a81\u7834\u65b0\u9ad8/\u5747\u7ebf\u22653\u6b21"),
    ("\u6ce2\u52a8\u5f3a\u5ea6  volatility",     "volatility",     2.00, "% \u632f\u5e45",   "2.0 = \u65e5\u5747\u632f\u5e45\u22652%"),
    ("\u8fde\u7eed\u4e0a\u6da8  continuous",     "continuous",     3.00, "\u5929\u6570",     "3.0 = \u672b\u5c3e\u8fde\u7eed\u6536\u6da8\u22653\u5929"),
]'''

NEW_OPTS = '''# ── 条件分组（Phase 10.1）format: (label, cond_type, default, unit, hint)
COND_GROUPS = [
    ("📈 趋势行为  Trend", [
        ("  连续上涨  continuous",    "continuous",    3.00, "天数",     "末尾连续收涨 >= N 天"),
        ("  上涨天数  rise_days",     "rise_days",     0.50, "0-1比率",  "窗口内上涨天数占比 >= N"),
        ("  均线多头  ma_alignment",  "ma_alignment",  0.00, "（无阈值）", "MA5>MA10>MA20>MA60 多头排列"),
        ("  趋势斜率  trend_slope",   "trend_slope",   0.10, "% / 天",   "MA20斜率 >= N%/天，正值代表上升"),
    ]),
    ("🔥 强势行为  Momentum", [
        ("  综合强度  kline_strength","kline_strength", 0.40, "0-1得分",  "行为因子综合强度 >= N"),
        ("  大涨次数  rise_pct",      "rise_pct",       3.00, "% 涨幅",   "单日涨幅 >= N%，窗口内至少1次"),
        ("  N日收益   return_n_days", "return_n_days", 10.00, "% 收益",   "过去N日累计涨幅 >= N%"),
    ]),
    ("🚀 突破行为  Breakout", [
        ("  突破次数  breakout_count","breakout_count", 3.00, "次数",     "窗口内突破新高/均线 >= N次"),
        ("  新高突破  new_high_n",    "new_high_n",     0.00, "（无阈值）", "收盘价突破N日最高价"),
    ]),
    ("🕯 K线形态  Pattern", [
        ("  大阳线数  big_yang_count","big_yang_count", 2.00, "次（根）",  "窗口内大阳线根数 >= N"),
    ]),
    ("📊 量价行为  Volume", [
        ("  放量上涨  volume_price_confirm","volume_price_confirm",1.50,"倍（均量）","涨幅>=3%且成交量>=均量N倍"),
    ]),
    ("🔥 涨停行为  Limit", [
        ("  涨停次数  limit_up_count","limit_up_count", 1.00, "次数",     "窗口内涨停次数 >= N"),
    ]),
    ("🌊 波动行为  Volatility", [
        ("  波动强度  volatility",    "volatility",     2.00, "% 振幅",   "日均振幅 >= N%"),
    ]),
]
# 向后兼容
COND_OPTIONS = [item for _, group in COND_GROUPS for item in group]'''

if 'COND_OPTIONS = [' in src and 'COND_GROUPS' not in src:
    # 找完整的 COND_OPTIONS 块：从 "COND_OPTIONS = [" 到 "]" 的闭合
    start = src.index('COND_OPTIONS = [')
    depth = 0
    end = start
    for i in range(start, len(src)):
        if src[i] == '[':
            depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    src = src[:start] + NEW_OPTS + src[end:]
    print('1: COND_OPTIONS replaced')
else:
    print('1: skip')

# ── 2. 把 ComboBox 填充改为分组带标题 ────────────────────────────────
OLD_FILL = '        for label, val, default, unit, hint in COND_OPTIONS:\n            self.cond_type.addItem(label, (val, unit, hint))'
NEW_FILL = '''        for group_name, items in COND_GROUPS:
            # 分组标题（灰色、不可选）
            self.cond_type.addItem(group_name, None)
            header_idx = self.cond_type.count() - 1
            item = self.cond_type.model().item(header_idx)
            item.setEnabled(False)
            from vnpy.trader.ui import QtGui as _QtGui
            item.setForeground(_QtGui.QColor("#6c7086"))
            # 分组内条件
            for label, val, default, unit, hint in items:
                self.cond_type.addItem(label, (val, unit, hint))'''

if OLD_FILL in src:
    src = src.replace(OLD_FILL, NEW_FILL)
    print('2: ComboBox fill updated')
else:
    print('2: anchor not found')

# ── 3. _on_type_changed 里跳过分组标题（userData=None）────────────────
# 找 _on_type_changed 方法并在开头加 guard
OLD_TYPE = '    def _on_type_changed(self, idx):'
NEW_TYPE = '''    def _on_type_changed(self, idx):
        data = self.cond_type.currentData()
        if data is None:
            # 选中了分组标题，自动跳到下一个可选项
            next_idx = idx + 1
            while next_idx < self.cond_type.count():
                if self.cond_type.itemData(next_idx) is not None:
                    self.cond_type.setCurrentIndex(next_idx)
                    return
                next_idx += 1
            return'''

if OLD_TYPE in src and 'data = self.cond_type.currentData()' not in src:
    src = src.replace(OLD_TYPE, NEW_TYPE)
    print('3: _on_type_changed guard added')
else:
    print('3: skip')

p.write_text(src, encoding='utf-8')
print(f'behavior_editor.py saved: {len(src.splitlines())} lines')
