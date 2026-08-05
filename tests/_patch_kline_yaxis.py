"""
验证并应用 kline_view.py 的 Y轴动态更新修改。
"""
import os

filepath = os.path.join(os.path.dirname(__file__), '..', 
                        'vnpy', 'strategy_condition', 'ui', 'kline_view.py')
filepath = os.path.abspath(filepath)

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

found_signal = '_on_x_range_changed' in content
found_connect = 'sigXRangeChanged' in content
found_vol_p95 = 'vol_p95' in content

print(f"File: {filepath}")
print(f"Length: {len(content)} chars")
print(f"Has _on_x_range_changed: {found_signal}")
print(f"Has sigXRangeChanged: {found_connect}")
print(f"Has vol_p95: {found_vol_p95}")

if found_signal and found_connect and found_vol_p95:
    print("\nAll modifications already applied!")
else:
    print("\nApplying modifications...")
    
    # Step 1: Add sigXRangeChanged connection
    if not found_connect:
        old1 = '        self._proxy = pg.SignalProxy(\n            self._main_plot.scene().sigMouseMoved,\n            rateLimit=60, slot=self._on_mouse_moved)'
        new1 = old1 + '\n\n        # -- Dynamic Y-axis: auto-update when user scrolls/zooms X axis --\n        self._main_plot.sigXRangeChanged.connect(self._on_x_range_changed)'
        if old1 in content:
            content = content.replace(old1, new1, 1)
            print("  Step 1: sigXRangeChanged connect added")
        else:
            print("  Step 1 FAILED: target string not found")
    
    # Step 2: Add _on_x_range_changed method before _on_mouse_moved
    if not found_signal:
        old2 = '    def _on_mouse_moved(self, evt) -> None:'
        method_code = '''    def _on_x_range_changed(self, *_args) -> None:
        """X轴范围变化时动态更新Y轴范围。"""
        if not self._bars:
            return
        n = len(self._bars)
        xmin, xmax = self._main_plot.viewRange()[0]
        i_start = max(0, int(xmin))
        i_end = min(n, int(xmax) + 1)
        if i_start >= i_end:
            return

        # K线Y轴：可见区间的 low/high + 5% padding
        vis_bars = self._bars[i_start:i_end]
        if vis_bars:
            price_lo = min(b[2] for b in vis_bars)
            price_hi = max(b[1] for b in vis_bars)
            price_range = price_hi - price_lo
            if price_range <= 0:
                price_range = price_hi * 0.1 or 1.0
            padding = price_range * 0.05
            self._main_plot.setYRange(
                price_lo - padding, price_hi + padding, padding=0)

        # 成交量Y轴：可见区间的P95百分位 + 5% padding
        vis_vols = self._volumes[i_start:i_end]
        if vis_vols:
            import numpy as np
            vols_arr = np.array([v for v in vis_vols if v > 0])
            if len(vols_arr) > 0:
                vol_p95 = float(np.percentile(vols_arr, 95))
                vol_max = float(vols_arr.max())
                vol_ceiling = max(vol_p95, vol_max * 0.6)
                vol_padding = vol_ceiling * 0.05
                self._vol_plot.setYRange(0, vol_ceiling + vol_padding, padding=0)

'''
        new2 = method_code + '    def _on_mouse_moved(self, evt) -> None:'
        if old2 in content:
            content = content.replace(old2, new2, 1)
            print("  Step 2: _on_x_range_changed method added")
        else:
            print("  Step 2 FAILED: target string not found")
    
    # Step 3: Add initial volume P95 in _redraw
    if not found_vol_p95:
        old3 = '        # \xe6\x88\x90\xe4\xba\xa4\xe9\x87\x8f\n        vol_item = VolumeItem(self._volumes, closes)\n        self._vol_plot.addItem(vol_item)'
        # Try unicode version
        old3_u = '        # 成交量\n        vol_item = VolumeItem(self._volumes, closes)\n        self._vol_plot.addItem(vol_item)'
        
        vol_patch = '''\n
        # 成交量Y轴：P95百分位截断 + 5% padding
        vis_vols = self._volumes[max(0, n - 120):n]
        if vis_vols:
            vols_pos = [v for v in vis_vols if v > 0]
            if vols_pos:
                import numpy as np
                vols_arr = np.array(vols_pos)
                vol_p95 = float(np.percentile(vols_arr, 95))
                vol_max = float(vols_arr.max())
                vol_ceiling = max(vol_p95, vol_max * 0.6)
                vol_padding = vol_ceiling * 0.05
                self._vol_plot.setYRange(0, vol_ceiling + vol_padding, padding=0)
        self._vol_plot.setMouseEnabled(x=True, y=False)
        self._vol_plot.enableAutoRange(axis='y', enable=False)'''
        
        if old3_u in content:
            content = content.replace(old3_u, old3_u + vol_patch, 1)
            print("  Step 3: Volume P95 in _redraw added")
        else:
            print("  Step 3 FAILED: target string not found")
            # Debug: search for vol_item
            idx = content.find('vol_item = VolumeItem')
            if idx >= 0:
                snippet = content[max(0, idx-50):idx+100]
                print(f"  Found vol_item at char {idx}, context: {repr(snippet[:80])}")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\nFile saved!")

# Final syntax check
import ast
try:
    ast.parse(content)
    print("Syntax check: OK")
except SyntaxError as e:
    print(f"Syntax ERROR: {e}")