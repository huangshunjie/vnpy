# -*- coding: utf-8 -*-
"""Add measure tool to _FullscreenChart in kline_view.py"""
import sys
import os

TARGET = os.path.join("vnpy", "strategy_condition", "ui", "kline_view.py")

with open(TARGET, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add measure state vars to _FullscreenChart.__init__
old_init = "        self._show_candles = show_candles\n        self._build_ui()\n        self._redraw()"
new_init = """        self._show_candles = show_candles
        self._measure_mode = False
        self._measure_start = None
        self._measure_line = None
        self._build_ui()
        self._redraw()"""

if old_init not in content:
    print("ERROR: cannot find init block")
    sys.exit(1)
content = content.replace(old_init, new_init, 1)

# 2. Add toolbar with measure button to _build_ui
old_build = '''    def _build_ui(self) -> None:
        pg.setConfigOptions(antialias=False, background=_BG, foreground=_FG)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._info_bar = QtWidgets.QLabel("  \xe2\x80\x94 \xe7\xa7\xbb\xe5\x8a\xa8\xe9\xbc\xa0\xe6\xa0\x87\xe6\x9f\xa5\xe7\x9c\x8bK\xe7\xba\xbf\xe6\x95\xb0\xe6\x8d\xae \xe2\x80\x94")'''

# Try simpler match
old_build2 = '    def _build_ui(self) -> None:\n        pg.setConfigOptions(antialias=False, background=_BG, foreground=_FG)\n        layout = QtWidgets.QVBoxLayout(self)\n        layout.setContentsMargins(0, 0, 0, 0)\n        layout.setSpacing(0)\n\n        self._info_bar = QtWidgets.QLabel("  \u2014 \u79fb\u52a8\u9f20\u6807\u67e5\u770bK\u7ebf\u6570\u636e \u2014")'

if old_build2 not in content:
    print("ERROR: cannot find _build_ui block in _FullscreenChart")
    # Try to find it by searching for the pattern
    idx = content.find('class _FullscreenChart')
    if idx < 0:
        print("ERROR: cannot find _FullscreenChart class")
        sys.exit(1)
    # Find _build_ui after the class
    build_idx = content.find('def _build_ui(self) -> None:', idx)
    if build_idx < 0:
        print("ERROR: cannot find _build_ui method")
        sys.exit(1)
    # Find the info_bar line
    info_idx = content.find('self._info_bar = QtWidgets.QLabel', build_idx)
    if info_idx < 0:
        print("ERROR: cannot find info_bar line")
        sys.exit(1)
    # Get the line
    line_start = content.rfind('\n', 0, info_idx) + 1
    line_end = content.find('\n', info_idx)
    info_line = content[line_start:line_end]
    print(f"Found info_bar line: {repr(info_line[:80])}")
    
    # Insert toolbar code before info_bar
    toolbar_code = '''
        # Toolbar with measure tool
        _fs_toolbar = QtWidgets.QWidget()
        _fs_toolbar.setFixedHeight(36)
        _fs_toolbar.setStyleSheet(f"background:{_PANEL};border-bottom:1px solid {_BORD};")
        _tl = QtWidgets.QHBoxLayout(_fs_toolbar)
        _tl.setContentsMargins(10, 0, 10, 0)
        _tl.setSpacing(8)

        self._fs_measure_btn = QtWidgets.QPushButton('\\U0001f4cf \\u6d4b\\u91cf')
        self._fs_measure_btn.setCheckable(True)
        self._fs_measure_btn.setFixedHeight(28)
        self._fs_measure_btn.setStyleSheet(
            'QPushButton{background:#a6e3a1;color:#11111b;border:none;'
            'border-radius:4px;font-size:13px;font-weight:bold;padding:0 12px;}'
            'QPushButton:checked{background:#89b4fa;}')
        self._fs_measure_btn.clicked.connect(self._on_measure_toggle)
        _tl.addWidget(self._fs_measure_btn)
        _tl.addStretch()
        layout.addWidget(_fs_toolbar)

'''
    content = content[:line_start] + toolbar_code + content[line_start:]
else:
    new_build = '''    def _build_ui(self) -> None:
        pg.setConfigOptions(antialias=False, background=_BG, foreground=_FG)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar with measure tool
        _fs_toolbar = QtWidgets.QWidget()
        _fs_toolbar.setFixedHeight(36)
        _fs_toolbar.setStyleSheet(f"background:{_PANEL};border-bottom:1px solid {_BORD};")
        _tl = QtWidgets.QHBoxLayout(_fs_toolbar)
        _tl.setContentsMargins(10, 0, 10, 0)
        _tl.setSpacing(8)

        self._fs_measure_btn = QtWidgets.QPushButton('\U0001f4cf \u6d4b\u91cf')
        self._fs_measure_btn.setCheckable(True)
        self._fs_measure_btn.setFixedHeight(28)
        self._fs_measure_btn.setStyleSheet(
            'QPushButton{background:#a6e3a1;color:#11111b;border:none;'
            'border-radius:4px;font-size:13px;font-weight:bold;padding:0 12px;}'
            'QPushButton:checked{background:#89b4fa;}')
        self._fs_measure_btn.clicked.connect(self._on_measure_toggle)
        _tl.addWidget(self._fs_measure_btn)
        _tl.addStretch()
        layout.addWidget(_fs_toolbar)

        self._info_bar = QtWidgets.QLabel("  \u2014 \u79fb\u52a8\u9f20\u6807\u67e5\u770bK\u7ebf\u6570\u636e \u2014")'''
    content = content.replace(old_build2, new_build, 1)

# 3. Add measure methods before the last line of _on_mouse_moved
# Find end of file and append measure methods
measure_methods = '''
    # ── Measure tool methods ──────────────────────────────────────────
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
                f"[Measure] {bars_diff} bars | "
                f"{direction}{price_diff:.2f} ({direction}{pct:.2f}%)"
                f"</b>")
            self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)
            self._measure_start = None
'''

# Check if measure methods already exist
if '_on_measure_toggle' not in content[content.find('class _FullscreenChart'):]:
    content = content.rstrip() + measure_methods + '\n'

# 4. Add mouse click connection in _build_ui (after the proxy line)
proxy_line = "        self._proxy = pg.SignalProxy(\n            self._main_plot.scene().sigMouseMoved,\n            rateLimit=60, slot=self._on_mouse_moved)"
if proxy_line in content:
    # Find it only in _FullscreenChart section
    fs_start = content.find('class _FullscreenChart')
    proxy_idx = content.find(proxy_line, fs_start)
    if proxy_idx > 0:
        insert_pos = proxy_idx + len(proxy_line)
        click_code = "\n\n        # Connect mouse click for measure tool\n        self._main_plot.scene().sigMouseClicked.connect(self._on_measure_click)\n"
        if 'sigMouseClicked.connect(self._on_measure_click)' not in content[fs_start:]:
            content = content[:insert_pos] + click_code + content[insert_pos:]

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(content)

print("DONE - measure tool added to _FullscreenChart")
print(f"File now has {len(content.splitlines())} lines")