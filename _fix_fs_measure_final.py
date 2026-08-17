# -*- coding: utf-8 -*-
"""Replace _FullscreenChart's _on_measure_toggle and _on_measure_click by line range."""

path = 'vnpy/strategy_condition/ui/kline_view.py'
lines = open(path, 'r', encoding='utf-8').readlines()

# Find _FullscreenChart class start
fs_start = None
for i, ln in enumerate(lines):
    if 'class _FullscreenChart' in ln:
        fs_start = i
        break

# Find _on_measure_toggle in _FullscreenChart
toggle_start = None
for i in range(fs_start, len(lines)):
    if 'def _on_measure_toggle' in lines[i]:
        toggle_start = i
        break

# Find end of _on_measure_click (next 'def ' at same indent level, or class)
end_line = None
for i in range(toggle_start + 1, len(lines)):
    ln = lines[i]
    # Method at 4-space indent = new method in same class
    if ln.startswith('    def ') and 'def _on_measure_click' not in ln:
        end_line = i
        break
    # Or class definition
    if ln.startswith('class '):
        end_line = i
        break

print(f'_FullscreenChart starts at line {fs_start+1}')
print(f'_on_measure_toggle at line {toggle_start+1}')
print(f'End (next method) at line {end_line+1}')
print(f'\nWill delete lines {toggle_start+1} to {end_line} (inclusive)')
print(f'First deleted line: {lines[toggle_start].rstrip()}')
print(f'Last deleted line:  {lines[end_line-1].rstrip()}')
print(f'Next kept line:     {lines[end_line].rstrip()}')

# Replace with MeasureTool version
new_code = '''    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode using MeasureTool."""
        if not hasattr(self, '_measure_tool'):
            self._measure_tool = MeasureTool(self._main_plot, self._bars, self._dates)
        self._measure_tool.set_active(checked)

'''

new_lines = lines[:toggle_start] + [new_code] + lines[end_line:]

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'\n[DONE] Replaced {end_line - toggle_start} lines with MeasureTool call')
print(f'Original: {len(lines)} lines -> New: {len(new_lines)} lines (with 1 replacement block)')