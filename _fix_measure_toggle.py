"""Add _on_measure_toggle method to KlineChartWidget class"""

# Read the file
with open(r'vnpy\strategy_condition\ui\kline_view.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where to insert (after _on_x_range_changed method ends)
insert_pos = None
for i, line in enumerate(lines):
    if 'def _on_x_range_changed' in line:
        # Find the end of this method
        j = i + 1
        while j < len(lines):
            next_line = lines[j].strip()
            # Next method or class starts
            if next_line and not next_line.startswith('#') and (next_line.startswith('def ') or next_line.startswith('class ')):
                insert_pos = j
                break
            j += 1
        break

if insert_pos:
    # Insert the new method
    new_method = [
        '\n',
        '    def _on_measure_toggle(self, checked: bool) -> None:\n',
        '        """Toggle measure tool on/off"""\n',
        '        if self._measure_tool is not None:\n',
        '            self._measure_tool.set_active(checked)\n',
        '\n'
    ]
    
    lines[insert_pos:insert_pos] = new_method
    
    # Write back
    with open(r'vnpy\strategy_condition\ui\kline_view.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✓ Added _on_measure_toggle method at line {insert_pos+1}")
else:
    print("✗ Could not find insertion point")