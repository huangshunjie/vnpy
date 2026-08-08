"""修复条件满足率统计表在切换标的刷新后不更新的问题"""
import sys

filepath = "vnpy/quant_research/ui/behavior_monitor_tab.py"
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到 _on_symbol_changed 方法（第478行）和 _on_refresh 方法（第485行）
# 替换 478-488 行（_on_symbol_changed + _on_refresh）

new_block = '''\
    def set_refresh_callback(self, callback):
        """设置刷新回调函数，用于重新计算单个标的的数据"""
        self._refresh_callback = callback

    def _on_symbol_changed(self, symbol: str):
        """标的切换时重新渲染"""
        if not symbol:
            return
        self._current_symbol = symbol
        if symbol in self._monitor_data:
            self._render_monitor(symbol)

    def _on_refresh(self):
        """刷新当前标的 - 如果缓存中没有则通过回调重新计算"""
        symbol = self._symbol_combo.currentText().strip()
        if not symbol:
            return
        self._current_symbol = symbol

        # 如果有回调，先调用回调重新计算该标的的数据
        if hasattr(self, '_refresh_callback') and self._refresh_callback:
            self._refresh_callback(symbol)

        # 渲染（回调会更新 _monitor_data）
        if symbol in self._monitor_data:
            self._render_monitor(symbol)

'''

# 找到起止行
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "def _on_symbol_changed(self, symbol: str):" in line:
        start_idx = i
    if start_idx is not None and "def _render_monitor(self, symbol: str):" in line:
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print(f"ERROR: start={start_idx}, end={end_idx}")
    sys.exit(1)

print(f"Replacing lines {start_idx+1} to {end_idx} (before _render_monitor)")

# 替换
new_lines = lines[:start_idx] + [new_block] + lines[end_idx:]

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("OK - behavior_monitor_tab.py patched successfully")