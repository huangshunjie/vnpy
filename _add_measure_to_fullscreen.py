"""
为全屏K线图添加测量工具支持
"""
import re

# 读取文件
with open('vnpy/strategy_condition/ui/kline_view.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 _KlineFullscreenWindow 的工具栏中添加测量按钮
# 找到 self._trig_chk 定义后面，添加测量按钮
pattern1 = r"(self\._trig_chk\.setStyleSheet\('color:#c084fc;font-size:13px;background:transparent;'\)\s+tl\.addWidget\(self\._trig_chk\))"
replacement1 = r"""\1
        
        # 测量工具按钮
        self._measure_btn = QtWidgets.QPushButton("📏 测量")
        self._measure_btn.setCheckable(True)
        self._measure_btn.setFixedHeight(26)
        self._measure_btn.setStyleSheet(
            'background:#a6e3a1;color:#11111b;border:none;'
            'border-radius:4px;font-size:13px;font-weight:bold;padding:0 10px;')
        self._measure_btn.clicked.connect(self._on_measure_toggle)
        tl.addWidget(self._measure_btn)"""

content = re.sub(pattern1, replacement1, content)

# 2. 添加 _on_measure_toggle 方法到 _KlineFullscreenWindow
pattern2 = r"(def keyPressEvent\(self, event\) -> None:)"
replacement2 = r"""def _on_measure_toggle(self, checked: bool) -> None:
        \"\"\"切换测量工具\"\"\"
        # 更新按钮样式
        if checked:
            self._measure_btn.setStyleSheet(
                'background:#89b4fa;color:#11111b;border:none;'
                'border-radius:4px;font-size:13px;font-weight:bold;padding:0 10px;')
        else:
            self._measure_btn.setStyleSheet(
                'background:#a6e3a1;color:#11111b;border:none;'
                'border-radius:4px;font-size:13px;font-weight:bold;padding:0 10px;')
        # 通知图表组件
        self._chart._measure_tool.set_active(checked)

    \1"""

content = re.sub(pattern2, replacement2, content)

# 3. 修改 _FullscreenChart.__init__，初始化 MeasureTool
pattern3 = r"(self\._show_triggers = show_triggers\s+self\._show_candles = show_candles\s+self\._measure_mode = False\s+self\._measure_start = None\s+self\._measure_line = None)"
replacement3 = r"""self._show_triggers = show_triggers
        self._show_candles = show_candles
        self._measure_tool = None  # 将在 _build_ui 后初始化"""

content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)

# 4. 在 _build_ui 结尾初始化 MeasureTool
pattern4 = r"(# Connect mouse click for measure tool\s+self\._main_plot\.scene\(\)\.sigMouseClicked\.connect\(self\._on_measure_click\))"
replacement4 = r"""# 初始化测量工具
        from .measure_tool import MeasureTool
        self._measure_tool = MeasureTool(self._main_plot, self._bars, self._dates)"""

content = re.sub(pattern4, replacement4, content)

# 5. 在 _redraw 开始时更新 MeasureTool 的数据
pattern5 = r"(def _redraw\(self\) -> None:\s+self\._main_plot\.clear\(\)\s+self\._vol_plot\.clear\(\))"
replacement5 = r"""\1
        
        # 更新测量工具数据
        if self._measure_tool:
            self._measure_tool.update_data(self._bars, self._dates)"""

content = re.sub(pattern5, replacement5, content)

# 6. 删除旧的测量工具相关方法
# 删除 _on_measure_toggle 和 _on_measure_click
pattern6 = r"    # ── Measure tool methods ──────────────────────────────────────────\s+def _on_measure_toggle\(self, checked: bool\).*?def _on_measure_click\(self, evt\).*?self\._measure_start = None\s+"
content = re.sub(pattern6, "", content, flags=re.DOTALL)

# 写回文件
with open('vnpy/strategy_condition/ui/kline_view.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ 已为全屏K线图添加测量工具支持")
print("  - 在工具栏添加了'📏 测量'按钮")
print("  - 用 MeasureTool 替换了旧的简单实现")
print("  - 支持双击删除测量线")