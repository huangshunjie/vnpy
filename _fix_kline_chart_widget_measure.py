"""Fix KlineChartWidget to properly integrate MeasureTool"""

with open('vnpy/strategy_condition/ui/kline_view.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # 删除错误添加的toolbar代码（237-255行附近）
    if i < len(lines) - 10 and '# Toolbar with measure tool' in line and '_fs_toolbar' in lines[i+1]:
        # Skip the entire toolbar block until we hit info_bar
        while i < len(lines) and 'self._info_bar = QtWidgets.QLabel' not in lines[i]:
            i += 1
        continue
    
    new_lines.append(line)
    i += 1

# Write back
with open('vnpy/strategy_condition/ui/kline_view.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Removed incorrect toolbar code from KlineChartWidget")
print(f"File now has {len(new_lines)} lines (was {len(lines)} lines)")