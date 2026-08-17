# -*- coding: utf-8 -*-
"""
正确恢复测量工具功能：
1. 使用原有的 MeasureTool 类（支持多条线、吸附、双击删除）
2. 在全屏窗口工具栏添加测量按钮
3. 移除之前的简化实现
"""

TARGET = "vnpy/strategy_condition/ui/kline_view.py"

with open(TARGET, "r", encoding="utf-8") as f:
    lines = f.readlines()

# ================================================================
# STEP 1: Add import for MeasureTool at top of file
# ================================================================
import_added = False
for i, line in enumerate(lines):
    if line.strip().startswith("from vnpy.trader.ui import"):
        # Add import after this line
        lines.insert(i + 1, "from .measure_tool import MeasureTool\n")
        import_added = True
        print(f"[OK] Added MeasureTool import at line {i+2}")
        break

if not import_added:
    print("[WARN] Could not find import location, adding at top")
    lines.insert(0, "from .measure_tool import MeasureTool\n")

content = "".join(lines)

# ================================================================
# STEP 2: Remove old simplified implementations
# Remove _measure_mode, _measure_start, _measure_line, _measure_label
# from both KlineChartWidget and _FullscreenChart __init__
# ================================================================

# Remove from KlineChartWidget.__init__
old_kcw_measure_init = """        self._measure_mode = False
        self._measure_start = None
        self._measure_line = None"""

if old_kcw_measure_init in content:
    content = content.replace(old_kcw_measure_init, "")
    print("[OK] Removed old measure vars from KlineChartWidget.__init__")

# Remove from _FullscreenChart.__init__
old_fs_measure_init = """        self._measure_mode = False
        self._measure_start = None
        self._measure_line = None"""

count = content.count(old_fs_measure_init)
content = content.replace(old_fs_measure_init, "")
if count > 0:
    print(f"[OK] Removed old measure vars from _FullscreenChart.__init__ ({count} occurrences)")

# ================================================================
# STEP 3: Replace KlineChartWidget measure methods with MeasureTool
# Find _on_measure_toggle in KlineChartWidget and replace entire section
# ================================================================

# Pattern: from _on_measure_toggle to _on_measure_click
old_kcw_methods = '''    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode on/off."""
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None
            if hasattr(self, '_measure_label') and self._measure_label:
                self._main_plot.removeItem(self._measure_label)
                self._measure_label = None

    def _on_measure_click(self, evt) -> None:
        """Handle mouse click for measure tool."""
        if not self._measure_mode:
            return
        pos = evt.scenePos()
        if not self._main_plot.sceneBoundingRect().contains(pos):
            return
        mp = self._main_plot.vb.mapSceneToView(pos)
        x_idx = int(round(mp.x()))
        y_price = mp.y()

        if self._measure_start is None:
            self._measure_start = (x_idx, y_price)
            # Remove previous measure items
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None
            if hasattr(self, '_measure_label') and self._measure_label:
                self._main_plot.removeItem(self._measure_label)
                self._measure_label = None
        else:
            sx, sy = self._measure_start
            ex, ey = x_idx, y_price
            # Remove old items
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
            if hasattr(self, '_measure_label') and self._measure_label:
                self._main_plot.removeItem(self._measure_label)

            # Draw dashed line
            self._measure_line = pg.PlotDataItem(
                [sx, ex], [sy, ey],
                pen=pg.mkPen('#FFA500', width=2, style=QtCore.Qt.PenStyle.DashLine))
            self._main_plot.addItem(self._measure_line)

            # Calculate measurement data
            bars_diff = abs(ex - sx)
            price_diff = ey - sy
            pct = (price_diff / sy * 100) if sy != 0 else 0
            sign = "+" if price_diff >= 0 else ""

            # Create floating annotation TextItem on chart
            label_text = (
                f"时间: {bars_diff} 根K线\\n"
                f"价格: {sy:.2f} → {ey:.2f}\\n"
                f"涨跌: {sign}{pct:.2f}% ({sign}{price_diff:.2f})")
            mid_x = (sx + ex) / 2
            mid_y = (sy + ey) / 2
            self._measure_label = pg.TextItem(
                label_text, color='#cdd6f4', anchor=(0.5, 0.5))
            self._measure_label.setPos(mid_x, mid_y)
            self._measure_label.fill = pg.mkBrush(30, 30, 46, 220)
            self._measure_label.border = pg.mkPen('#FFA500', width=1)
            self._main_plot.addItem(self._measure_label)

            # Also update info bar
            self._info_bar.setText(
                f"  <b style='color:#FFA500'>"
                f"[测量] {bars_diff} 根K线 | "
                f"{sign}{price_diff:.2f} ({sign}{pct:.2f}%)"
                f"</b>")
            self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)
            self._measure_start = None'''

new_kcw_methods = '''    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode using MeasureTool."""
        if not hasattr(self, '_measure_tool'):
            self._measure_tool = MeasureTool(self._main_plot, self._bars, self._dates)
        self._measure_tool.set_active(checked)'''

if old_kcw_methods in content:
    content = content.replace(old_kcw_methods, new_kcw_methods)
    print("[OK] Replaced KlineChartWidget measure methods with MeasureTool")
else:
    print("[WARN] Could not find exact KlineChartWidget measure methods")

# ================================================================
# STEP 4: Replace _FullscreenChart measure methods with MeasureTool
# ================================================================

old_fs_methods = '''    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode on/off."""
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None
            if hasattr(self, '_measure_label') and self._measure_label:
                self._main_plot.removeItem(self._measure_label)
                self._measure_label = None

    def _on_measure_click(self, evt) -> None:
        """Handle mouse click for measure tool in fullscreen chart."""
        if not self._measure_mode:
            return
        pos = evt.scenePos()
        if not self._main_plot.sceneBoundingRect().contains(pos):
            return
        mp = self._main_plot.vb.mapSceneToView(pos)
        x_idx = int(round(mp.x()))
        y_price = mp.y()

        if self._measure_start is None:
            self._measure_start = (x_idx, y_price)
            # Remove previous measure items
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None
            if hasattr(self, '_measure_label') and self._measure_label:
                self._main_plot.removeItem(self._measure_label)
                self._measure_label = None
        else:
            sx, sy = self._measure_start
            ex, ey = x_idx, y_price
            # Remove old items
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
            if hasattr(self, '_measure_label') and self._measure_label:
                self._main_plot.removeItem(self._measure_label)

            # Draw dashed line
            self._measure_line = pg.PlotDataItem(
                [sx, ex], [sy, ey],
                pen=pg.mkPen('#FFA500', width=2, style=QtCore.Qt.PenStyle.DashLine))
            self._main_plot.addItem(self._measure_line)

            # Calculate measurement data
            bars_diff = abs(ex - sx)
            price_diff = ey - sy
            pct = (price_diff / sy * 100) if sy != 0 else 0
            sign = "+" if price_diff >= 0 else ""

            # Create floating annotation TextItem on chart
            label_text = (
                f"时间: {bars_diff} 根K线\\n"
                f"价格: {sy:.2f} → {ey:.2f}\\n"
                f"涨跌: {sign}{pct:.2f}% ({sign}{price_diff:.2f})")
            mid_x = (sx + ex) / 2
            mid_y = (sy + ey) / 2
            self._measure_label = pg.TextItem(
                label_text, color='#cdd6f4', anchor=(0.5, 0.5))
            self._measure_label.setPos(mid_x, mid_y)
            self._measure_label.fill = pg.mkBrush(30, 30, 46, 220)
            self._measure_label.border = pg.mkPen('#FFA500', width=1)
            self._main_plot.addItem(self._measure_label)

            # Also update info bar
            self._info_bar.setText(
                f"  <b style='color:#FFA500'>"
                f"[测量] {bars_diff} 根K线 | "
                f"{sign}{price_diff:.2f} ({sign}{pct:.2f}%)"
                f"</b>")
            self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)
            self._measure_start = None'''

new_fs_methods = '''    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode using MeasureTool."""
        if not hasattr(self, '_measure_tool'):
            self._measure_tool = MeasureTool(self._main_plot, self._bars, self._dates)
        self._measure_tool.set_active(checked)'''

if old_fs_methods in content:
    content = content.replace(old_fs_methods, new_fs_methods)
    print("[OK] Replaced _FullscreenChart measure methods with MeasureTool")
else:
    print("[WARN] Could not find exact _FullscreenChart measure methods")

# ================================================================
# STEP 5: Remove _on_measure_click from scene connection
# Since MeasureTool handles its own mouse events
# ================================================================

# In KlineChartWidget.__init__, remove the sigMouseClicked connection
old_connection = "        self._main_plot.scene().sigMouseClicked.connect(self._on_measure_click)"
if old_connection in content:
    content = content.replace(old_connection, "")
    print("[OK] Removed _on_measure_click connection from KlineChartWidget")

# In _FullscreenChart.__init__, remove the sigMouseClicked connection
old_fs_connection = "        self._main_plot.scene().sigMouseClicked.connect(self._on_measure_click)"
count = content.count(old_fs_connection)
content = content.replace(old_fs_connection, "")
if count > 0:
    print(f"[OK] Removed _on_measure_click connection from _FullscreenChart ({count} occurrences)")

# ================================================================
# STEP 6: Ensure fullscreen window has measure button (was added before)
# Check if it exists
# ================================================================

if '_fs_measure_btn = QtWidgets.QPushButton("📏 测量")' in content:
    print("[OK] Fullscreen measure button already exists")
else:
    print("[WARN] Fullscreen measure button not found, need to add it")
    # Add it before close button
    close_marker = 'close_btn = QtWidgets.QPushButton("× 关闭")'
    if close_marker in content:
        measure_btn_code = '''
        # 测量工具按钮
        self._fs_measure_btn = QtWidgets.QPushButton("📏 测量")
        self._fs_measure_btn.setCheckable(True)
        self._fs_measure_btn.setFixedHeight(28)
        self._fs_measure_btn.setStyleSheet(
            "QPushButton{background:#313244;color:#cdd6f4;border:1px solid #45475a;"
            "border-radius:4px;padding:2px 10px;font-size:13px;}"
            "QPushButton:hover{background:#45475a;}"
            "QPushButton:checked{background:#FFA500;color:#1e1e2e;border-color:#FFA500;}")
        self._fs_measure_btn.clicked.connect(self._on_fs_measure_toggle)
        tl.addWidget(self._fs_measure_btn)

'''
        content = content.replace(close_marker, measure_btn_code + "        " + close_marker)
        print("[OK] Added measure button to fullscreen toolbar")

# Check if _on_fs_measure_toggle method exists
if 'def _on_fs_measure_toggle(self, checked: bool)' in content:
    print("[OK] _on_fs_measure_toggle method already exists")
else:
    print("[WARN] _on_fs_measure_toggle method not found, need to add it")
    key_press_marker = "    def keyPressEvent(self, event) -> None:\n        if event.key() == QtCore.Qt.Key.Key_Escape:\n            self.close()"
    if key_press_marker in content:
        fs_toggle_method = '''    def _on_fs_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode in fullscreen chart."""
        self._chart._on_measure_toggle(checked)

''' + key_press_marker
        content = content.replace(key_press_marker, fs_toggle_method)
        print("[OK] Added _on_fs_measure_toggle method")

# ================================================================
# Write back
# ================================================================
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n[DONE] Restored MeasureTool properly. File size: {len(content)} chars")