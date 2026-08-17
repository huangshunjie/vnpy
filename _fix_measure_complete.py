# -*- coding: utf-8 -*-
"""
Complete fix for measure tool:
1. Add measure button to _KlineFullscreenWindow toolbar
2. Fix _on_measure_click in both KlineChartWidget and _FullscreenChart
   to show a floating TextItem annotation on the chart (not just info_bar)
"""

TARGET = "vnpy/strategy_condition/ui/kline_view.py"

with open(TARGET, "r", encoding="utf-8") as f:
    content = f.read()

# ================================================================
# FIX 1: Add measure button to _KlineFullscreenWindow toolbar
# Look for the close button area in _KlineFullscreenWindow
# The toolbar ends with close_btn and tl.addWidget(close_btn)
# We insert measure button before close_btn
# ================================================================

# Find the "退出全屏" button in _KlineFullscreenWindow
fs_close_marker = "close_btn = QtWidgets.QPushButton(\"× 关闭\")"
if fs_close_marker not in content:
    # Try alternative
    fs_close_marker = 'close_btn = QtWidgets.QPushButton("× 关闭")'

if fs_close_marker not in content:
    # Search for it
    import re
    m = re.search(r'(close_btn\s*=\s*QtWidgets\.QPushButton\(.+关闭.+\))', content)
    if m:
        fs_close_marker = m.group(1)
    else:
        print("[ERROR] Cannot find close_btn in _KlineFullscreenWindow")
        # Try "退出全屏"
        m2 = re.search(r'(.*QPushButton.*退出全屏.*)', content)
        if m2:
            fs_close_marker = m2.group(1).strip()
            print(f"  Found alternative: {fs_close_marker}")

if fs_close_marker in content:
    # Insert measure button before close_btn
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
    content = content.replace(fs_close_marker, measure_btn_code + "        " + fs_close_marker)
    print("[OK] Added measure button to _KlineFullscreenWindow toolbar")
else:
    print("[WARN] Could not find close button in fullscreen window, trying alternative approach")

# ================================================================
# FIX 2: Add _on_fs_measure_toggle method to _KlineFullscreenWindow
# This just delegates to self._chart._on_measure_toggle
# Find it near keyPressEvent in _KlineFullscreenWindow
# ================================================================

key_press_marker = "    def keyPressEvent(self, event) -> None:\n        if event.key() == QtCore.Qt.Key.Key_Escape:\n            self.close()"

if key_press_marker in content:
    fs_toggle_method = '''    def _on_fs_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode in fullscreen chart."""
        self._chart._on_measure_toggle(checked)

''' + key_press_marker
    content = content.replace(key_press_marker, fs_toggle_method)
    print("[OK] Added _on_fs_measure_toggle to _KlineFullscreenWindow")
else:
    print("[WARN] Could not find keyPressEvent marker")

# ================================================================
# FIX 3: Rewrite _on_measure_click in _FullscreenChart to add TextItem
# ================================================================

# Find the existing _on_measure_click in _FullscreenChart (after line 1583)
old_fs_measure_click = '''    def _on_measure_click(self, evt) -> None:
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
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None
        else:
            sx, sy = self._measure_start
            ex, ey = x_idx, y_price
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
            self._measure_line = pg.PlotDataItem(
                [sx, ex], [sy, ey],
                pen=pg.mkPen('#f38ba8', width=2, style=QtCore.Qt.PenStyle.DashLine))
            self._main_plot.addItem(self._measure_line)

            bars_diff = abs(ex - sx)
            price_diff = ey - sy
            pct = (price_diff / sy * 100) if sy != 0 else 0
            direction = "+" if price_diff >= 0 else ""
            self._info_bar.setText(
                f"  <b style='color:#f38ba8'>"
                f"[Measure] {bars_diff} bars | "
                f"{direction}{price_diff:.2f} ({direction}{pct:.2f}%)"
                f"</b>")
            self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)
            self._measure_start = None'''

new_fs_measure_click = '''    def _on_measure_click(self, evt) -> None:
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

if old_fs_measure_click in content:
    content = content.replace(old_fs_measure_click, new_fs_measure_click)
    print("[OK] Fixed _on_measure_click in _FullscreenChart (added TextItem annotation)")
else:
    print("[WARN] Could not find exact _FullscreenChart._on_measure_click, trying partial match")
    # Try to find and replace just the method body
    import re
    # Find from "def _on_measure_click" after _FullscreenChart class
    pattern = r'(    def _on_measure_click\(self, evt\) -> None:\n        """Handle mouse click for measure tool in fullscreen chart\."""\n(?:.*\n)*?            self\._measure_start = None)'
    match = re.search(pattern, content)
    if match:
        content = content.replace(match.group(0), new_fs_measure_click)
        print("[OK] Fixed _FullscreenChart._on_measure_click via regex")
    else:
        print("[ERROR] Could not fix _FullscreenChart._on_measure_click")

# ================================================================
# FIX 4: Rewrite _on_measure_click in KlineChartWidget (the first one)
# This is the one inserted earlier that also just updates info_bar
# ================================================================

old_kcw_measure_click = '''    def _on_measure_click(self, evt) -> None:
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
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None
        else:
            sx, sy = self._measure_start
            ex, ey = x_idx, y_price
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
            self._measure_line = pg.PlotDataItem(
                [sx, ex], [sy, ey],
                pen=pg.mkPen('#f38ba8', width=2, style=QtCore.Qt.PenStyle.DashLine))
            self._main_plot.addItem(self._measure_line)

            bars_diff = abs(ex - sx)
            price_diff = ey - sy
            pct = (price_diff / sy * 100) if sy != 0 else 0
            direction = "+" if price_diff >= 0 else ""
            self._info_bar.setText(
                f"  <b style='color:#f38ba8'>"
                f"[\\u6d4b\\u91cf] {bars_diff} \\u6839K\\u7ebf | "
                f"{direction}{price_diff:.2f} ({direction}{pct:.2f}%)"
                f"</b>")
            self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)
            self._measure_start = None'''

new_kcw_measure_click = '''    def _on_measure_click(self, evt) -> None:
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

if old_kcw_measure_click in content:
    content = content.replace(old_kcw_measure_click, new_kcw_measure_click)
    print("[OK] Fixed _on_measure_click in KlineChartWidget (added TextItem annotation)")
else:
    print("[WARN] Could not find exact KlineChartWidget._on_measure_click")
    # It may have unicode escapes - try different variant
    alt_old = old_kcw_measure_click.replace('\\\\u6d4b\\\\u91cf', '\\u6d4b\\u91cf').replace('\\\\u6839K\\\\u7ebf', '\\u6839K\\u7ebf')
    if alt_old in content:
        content = content.replace(alt_old, new_kcw_measure_click)
        print("[OK] Fixed KlineChartWidget._on_measure_click (alt match)")
    else:
        print("[ERROR] Could not fix KlineChartWidget._on_measure_click")

# ================================================================
# FIX 5: Also fix _on_measure_toggle to clean up label
# ================================================================

old_toggle = '''    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode on/off."""
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None'''

new_toggle = '''    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode on/off."""
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None
            if hasattr(self, '_measure_label') and self._measure_label:
                self._main_plot.removeItem(self._measure_label)
                self._measure_label = None'''

# Replace all occurrences (both KlineChartWidget and _FullscreenChart have this)
count = content.count(old_toggle)
content = content.replace(old_toggle, new_toggle)
print(f"[OK] Fixed _on_measure_toggle to also remove label ({count} occurrences)")

# Also handle variant without docstring
old_toggle_v2 = '''    def _on_measure_toggle(self, checked: bool) -> None:
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None'''

new_toggle_v2 = '''    def _on_measure_toggle(self, checked: bool) -> None:
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None
            if hasattr(self, '_measure_label') and self._measure_label:
                self._main_plot.removeItem(self._measure_label)
                self._measure_label = None'''

count2 = content.count(old_toggle_v2)
content = content.replace(old_toggle_v2, new_toggle_v2)
if count2:
    print(f"[OK] Fixed _on_measure_toggle variant ({count2} occurrences)")

# ================================================================
# Write back
# ================================================================
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n[DONE] All fixes applied. File size: {len(content)} chars")