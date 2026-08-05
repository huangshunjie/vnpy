"""
为 kline_view.py 添加 Y轴自适应 开关功能。
- KlineChartWidget 添加 _auto_yaxis 标志和 set_auto_yaxis() 方法
- _on_x_range_changed 检查标志
- KlineViewTab 工具栏添加 "Y轴自适应" 复选框
"""
import os

filepath = os.path.join(os.path.dirname(__file__), '..', 
                        'vnpy', 'strategy_condition', 'ui', 'kline_view.py')
filepath = os.path.abspath(filepath)

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

changed = False

# ═══════════════════════════════════════════════════════════════════════
# Part 1: Add _auto_yaxis flag in KlineChartWidget.__init__
# ═══════════════════════════════════════════════════════════════════════
if '_auto_yaxis' not in content:
    # Find the place where self._bars = [] is initialized
    anchor = '        self._bars: list = []'
    if anchor in content:
        replacement = anchor + '\n        self._auto_yaxis: bool = True  # Y轴自适应开关'
        content = content.replace(anchor, replacement, 1)
        changed = True
        print("Part 1: _auto_yaxis flag added to __init__")
    else:
        print("Part 1 FAILED: anchor not found")
        # Try alternative
        anchor2 = 'self._bars: list = []'
        idx = content.find(anchor2)
        if idx >= 0:
            print(f"  Found at char {idx}, context: {repr(content[idx-20:idx+50])}")
else:
    print("Part 1: _auto_yaxis already exists")

# ═══════════════════════════════════════════════════════════════════════
# Part 2: Add set_auto_yaxis method (before _on_x_range_changed)
# ═══════════════════════════════════════════════════════════════════════
if 'def set_auto_yaxis' not in content:
    anchor = '    def _on_x_range_changed(self, *_args) -> None:'
    if anchor in content:
        method = '''    def set_auto_yaxis(self, enabled: bool) -> None:
        """开启/关闭Y轴自适应模式。"""
        self._auto_yaxis = enabled
        if enabled:
            # 立即触发一次Y轴更新
            self._on_x_range_changed()
        else:
            # 关闭时恢复Y轴自由拖拽（autoRange）
            self._main_plot.enableAutoRange(axis='y', enable=True)
            self._vol_plot.enableAutoRange(axis='y', enable=True)

'''
        content = content.replace(anchor, method + anchor, 1)
        changed = True
        print("Part 2: set_auto_yaxis method added")
    else:
        print("Part 2 FAILED: _on_x_range_changed anchor not found")
else:
    print("Part 2: set_auto_yaxis already exists")

# ═══════════════════════════════════════════════════════════════════════
# Part 3: Guard _on_x_range_changed with _auto_yaxis check
# ═══════════════════════════════════════════════════════════════════════
guard_line = '        if not self._auto_yaxis:'
if guard_line not in content:
    # Add guard right after method signature's docstring
    anchor = '    def _on_x_range_changed(self, *_args) -> None:\n        """X轴范围变化时动态更新Y轴范围。"""'
    if anchor in content:
        replacement = anchor + '\n        if not self._auto_yaxis:\n            return'
        content = content.replace(anchor, replacement, 1)
        changed = True
        print("Part 3: _auto_yaxis guard added to _on_x_range_changed")
    else:
        print("Part 3 FAILED: anchor not found")
        # debug
        idx = content.find('def _on_x_range_changed')
        if idx >= 0:
            snippet = content[idx:idx+200]
            print(f"  Found method at char {idx}: {repr(snippet[:150])}")
else:
    print("Part 3: guard already exists")

# ═══════════════════════════════════════════════════════════════════════
# Part 4: Add checkbox in KlineViewTab toolbar (before fullscreen button)
# ═══════════════════════════════════════════════════════════════════════
if '_yaxis_chk' not in content:
    anchor = "        self._fullscreen_btn = QtWidgets.QPushButton('\u26f6 全屏')"
    if anchor in content:
        checkbox_code = """        self._yaxis_chk = QtWidgets.QCheckBox('Y轴自适应')
        self._yaxis_chk.setChecked(True)
        self._yaxis_chk.setStyleSheet('color:#94e2d5;font-size:14px;background:transparent;')
        self._yaxis_chk.stateChanged.connect(self._on_yaxis_toggle)
        tl.addWidget(self._yaxis_chk)

"""
        content = content.replace(anchor, checkbox_code + anchor, 1)
        changed = True
        print("Part 4: Y轴自适应 checkbox added to toolbar")
    else:
        print("Part 4 FAILED: fullscreen button anchor not found")
        # Try to find it
        idx = content.find('_fullscreen_btn')
        if idx >= 0:
            print(f"  Found at char {idx}: {repr(content[idx:idx+80])}")
else:
    print("Part 4: _yaxis_chk already exists")

# ═══════════════════════════════════════════════════════════════════════
# Part 5: Add _on_yaxis_toggle method in KlineViewTab
# ═══════════════════════════════════════════════════════════════════════
if 'def _on_yaxis_toggle' not in content:
    # Add after _on_vol_toggle or _on_ma_toggle
    anchor = '    def _on_vol_toggle(self'
    if anchor in content:
        method = '''    def _on_yaxis_toggle(self, state: int) -> None:
        """切换Y轴自适应模式。"""
        enabled = bool(state)
        self._chart.set_auto_yaxis(enabled)

'''
        content = content.replace(anchor, method + anchor, 1)
        changed = True
        print("Part 5: _on_yaxis_toggle method added")
    else:
        print("Part 5 FAILED: _on_vol_toggle anchor not found")
        # Try alternative
        idx = content.find('_on_vol_toggle')
        if idx >= 0:
            print(f"  Found at char {idx}: {repr(content[idx:idx+60])}")
        else:
            # Try _on_ma_toggle
            idx2 = content.find('def _on_ma_toggle')
            if idx2 >= 0:
                print(f"  Found _on_ma_toggle at {idx2}")
else:
    print("Part 5: _on_yaxis_toggle already exists")

# ═══════════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════════
if changed:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\nFile saved!")
else:
    print("\nNo changes needed.")

# Syntax check
import ast
try:
    ast.parse(content)
    print("Syntax check: OK")
except SyntaxError as e:
    print(f"Syntax ERROR: {e}")