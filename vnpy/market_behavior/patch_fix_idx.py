import pathlib

p = pathlib.Path(r'C:\Users\hdec\Documents\GitHub\vnpy\vnpy\vnpy\market_behavior\ui\behavior_editor.py')
lines = p.read_text(encoding='utf-8', errors='replace').splitlines()

# 第158行（0-based 157）：改为从 currentData() 取数据
# 第160行（0-based 159）：hint 文字标签（保持不动）
# 第164行（0-based 163）：currentData()[0] → currentData()[0] 不变，但要加 None 检查

# 修改第158行
lines[157] = '        data = self.cond_type.currentData()'
# 在其后插入 None guard + 取字段
lines.insert(158, '        if data is None:')
lines.insert(159, '            return')
lines.insert(160, '        _, default, unit, hint = data')
# 159行（原 self.threshold...）现在偏移到161，不用动

p.write_text('\n'.join(lines), encoding='utf-8')
print(f'done: {len(lines)} lines')

# 验证
lines2 = p.read_text(encoding='utf-8').splitlines()
for i in range(155, 167):
    print(f'{i+1}: {lines2[i]}')
