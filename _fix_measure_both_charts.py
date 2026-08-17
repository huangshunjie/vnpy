# -*- coding: utf-8 -*-
"""
Fix measure tool: add methods to KlineChartWidget (which already has the button),
and ensure _FullscreenChart also has both button and methods.
"""
import sys

TARGET = "vnpy/strategy_condition/ui/kline_view.py"

with open(TARGET, "r", encoding="utf-8") as f:
    content = f.read()

# ═══════════════════════════════════════════════════════════════════════
# STEP 1: Add measure state vars to KlineChartWidget.__init__
# ═══════════════════════════════════════════════════════════════════════
old_kcw_init = "        self._show_candles:  bool = True\n        self._build_ui()"
new_kcw_init = """        self._show_candles:  bool = True
        self._measure_mode = False
        self._measure_start = None
        self._measure_line = None
        self._build_ui()"""

if old_kcw_init in content:
    content = content.replace(old_kcw_init, new_kcw_init, 1)
    print("[OK] Added measure state vars to KlineChartWidget.__init__")
else:
    # Maybe already added
    if "self._measure_mode = False" in content[:content.find("class _BarLoaderThread")]:
        print("[SKIP] KlineChartWidget already has measure state vars")
    else:
        print("[ERROR] Cannot find KlineChartWidget.__init__ pattern")
        sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════
# STEP 2: Connect mouse click in KlineChartWidget._build_ui
# (after the sigMouseMoved proxy)
# ═══════════════════════════════════════════════════════════════════════
kcw_end = content.find("class _BarLoaderThread")
proxy_str = "self._proxy = pg.SignalProxy(\n            self._main_plot.scene().sigMouseMoved,\n            rateLimit=60, slot=self._on_mouse_moved)"
proxy_idx = content.find(proxy_str)

if proxy_idx > 0 and proxy_idx < kcw_end:
    # Check if click connect already exists
    click_str = "sigMouseClicked.connect(self._on_measure_click)"
    if click_str not in content[:kcw_end]:
        insert_pos = proxy_idx + len(proxy_str)
        click_code = "\n\n        # Connect mouse click for measure tool\n        self._main_plot.scene().sigMouseClicked.connect(self._on_measure_click)\n"
        content = content[:insert_pos] + click_code + content[insert_pos:]
        print("[OK] Connected sigMouseClicked in KlineChartWidget")
    else:
        print("[SKIP] KlineChartWidget already has sigMouseClicked connected")
else:
    print("[WARN] Could not find proxy in KlineChartWidget")

# ═══════════════════════════════════════════════════════════════════════
# STEP 3: Add measure methods to KlineChartWidget
# Insert before class _BarLoaderThread
# ═══════════════════════════════════════════════════════════════════════
kcw_methods = '''
    # ── Measure tool methods (KlineChartWidget) ──────────────────────
    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode on/off."""
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None

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
            self._measure_start = None

'''

# Find insertion point - before class _BarLoaderThread
bar_loader_idx = content.find("\nclass _BarLoaderThread")
if bar_loader_idx < 0:
    print("[ERROR] Cannot find class _BarLoaderThread")
    sys.exit(1)

# Check if methods already exist in KlineChartWidget section
if "_on_measure_toggle" not in content[:bar_loader_idx]:
    content = content[:bar_loader_idx] + kcw_methods + content[bar_loader_idx:]
    print("[OK] Added measure methods to KlineChartWidget")
else:
    print("[SKIP] KlineChartWidget already has measure methods")

# ═══════════════════════════════════════════════════════════════════════
# STEP 4: Verify _FullscreenChart has its own measure tool
# ═══════════════════════════════════════════════════════════════════════
fs_start = content.find("class _FullscreenChart")
if fs_start < 0:
    print("[ERROR] Cannot find class _FullscreenChart")
    sys.exit(1)

# Check if _FullscreenChart has measure methods
if "_on_measure_toggle" in content[fs_start:]:
    print("[OK] _FullscreenChart already has measure methods")
else:
    print("[WARN] _FullscreenChart missing measure methods - adding...")
    # Append at end of file
    fs_measure = '''
    # ── Measure tool methods (_FullscreenChart) ──────────────────────
    def _on_measure_toggle(self, checked: bool) -> None:
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None

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
            self._measure_start = None
'''
    content = content.rstrip() + fs_measure + '\n'

# Write back
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n[DONE] File now has {len(content.splitlines())} lines")
print("Both KlineChartWidget and _FullscreenChart now have measure tool support.")