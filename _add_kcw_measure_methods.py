# -*- coding: utf-8 -*-
"""Add measure methods to KlineChartWidget class"""

TARGET = "vnpy/strategy_condition/ui/kline_view.py"

with open(TARGET, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the end of _on_mouse_moved method in KlineChartWidget
# It ends with "self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)"
insert_idx = None
for i, line in enumerate(lines):
    if "self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)" in line:
        # Make sure this is in KlineChartWidget (before _BarLoaderThread)
        found_barloader = False
        for j in range(i, min(i+20, len(lines))):
            if "class _BarLoaderThread" in lines[j]:
                found_barloader = True
                break
        if found_barloader:
            insert_idx = i + 1
            break

if insert_idx is None:
    print("[ERROR] Cannot find insertion point")
    exit(1)

# Check if methods already exist
has_methods = False
for i in range(max(0, insert_idx-10), min(insert_idx+100, len(lines))):
    if "_on_measure_toggle" in lines[i] and i < lines.index("class _BarLoaderThread(QtCore.QThread):\n"):
        has_methods = True
        break

if has_methods:
    print("[SKIP] KlineChartWidget already has measure methods")
else:
    # Insert the methods
    method_code = """
    # ── Measure tool methods (KlineChartWidget) ──────────────────────
    def _on_measure_toggle(self, checked: bool) -> None:
        \"\"\"Toggle measure mode on/off.\"\"\"
        self._measure_mode = checked
        if not checked:
            self._measure_start = None
            if self._measure_line:
                self._main_plot.removeItem(self._measure_line)
                self._measure_line = None

    def _on_measure_click(self, evt) -> None:
        \"\"\"Handle mouse click for measure tool.\"\"\"
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

"""
    lines.insert(insert_idx, method_code)
    print(f"[OK] Added measure methods to KlineChartWidget at line {insert_idx}")

# Write back
with open(TARGET, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"\n[DONE] File now has {len(lines)} lines")