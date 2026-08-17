# -*- coding: utf-8 -*-
"""Replace _FullscreenChart's measure methods (lines 1557 to EOF)."""

path = 'vnpy/strategy_condition/ui/kline_view.py'
lines = open(path, 'r', encoding='utf-8').readlines()

# Locate _on_measure_toggle in _FullscreenChart (the SECOND occurrence)
count = 0
toggle_line = None
for i, ln in enumerate(lines):
    if 'def _on_measure_toggle' in ln:
        count += 1
        if count == 2:
            toggle_line = i
            break

print(f'Second _on_measure_toggle at line {toggle_line+1}')

# Replace from toggle_line to end of file with MeasureTool-based methods
new_code = '''    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode using MeasureTool."""
        if not hasattr(self, '_measure_tool') or self._measure_tool is None:
            self._measure_tool = MeasureTool(self._main_plot, self._bars, self._dates)
        self._measure_tool.set_active(checked)
'''

new_lines = lines[:toggle_line] + [new_code]

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'Done. Original: {len(lines)} lines -> New: {len(new_lines)} entries')

# Verify by counting occurrences
content = ''.join(new_lines)
print(f'\n_on_measure_toggle count: {content.count("def _on_measure_toggle")}')
print(f'_on_measure_click count: {content.count("def _on_measure_click")}')
print(f'MeasureTool( count: {content.count("MeasureTool(")}')
print(f'_measure_mode count: {content.count("_measure_mode")}')
print(f'_measure_start count: {content.count("_measure_start")}')
print(f'_measure_line count: {content.count("_measure_line")}')
print(f'_measure_label count: {content.count("_measure_label")}')