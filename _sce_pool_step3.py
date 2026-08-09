# -*- coding: utf-8 -*-
"""调整 SCE 股票池名称显示到数据源位置"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\ui\widget.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 第1步：从标题行删除 _pool_count_lbl 声明和添加
removed = 0
for i in range(len(lines)):
    if 'self._pool_count_lbl = _lbl(' in lines[i] and i < 600:
        lines[i] = ''
        removed += 1
    elif 'pool_hdr.addWidget(self._pool_count_lbl)' in lines[i] and i < 600:
        lines[i] = ''
        removed += 1

print(f'Step 1: Removed {removed} lines from header')

# 第2步：将 _data_src_lbl 声明替换为 _pool_count_lbl
for i in range(len(lines)):
    if '_data_src_lbl = _lbl(' in lines[i] and i > 650 and i < 700:
        # 将这行和下一行替换为新的pool_count声明
        lines[i] = '        self._pool_count_lbl = _lbl(\n'
        # 下一行应该是原文本内容
        if i + 1 < len(lines):
            lines[i + 1] = '            "\u6570\u636e\u6e90\uff1aVeighNa \u6570\u636e\u5e93", _MUT, 10)\n'
        print(f'Step 2: Replaced _data_src_lbl at line {i+1}')
        break

# 第3步：替换 setWordWrap 和 addWidget
for i in range(len(lines)):
    if '_data_src_lbl.setWordWrap' in lines[i] and i > 650 and i < 710:
        lines[i] = lines[i].replace('_data_src_lbl', '_pool_count_lbl')
        print(f'Step 3a: Fixed at line {i+1}')
    elif 'addWidget(self._data_src_lbl)' in lines[i] and i > 650 and i < 710:
        lines[i] = lines[i].replace('_data_src_lbl', '_pool_count_lbl')
        print(f'Step 3b: Fixed at line {i+1}')

# 第4步：将后面所有 _data_src_lbl 替换为 _pool_count_lbl
content = ''.join(lines)
count = content.count('self._data_src_lbl')
content = content.replace('self._data_src_lbl', 'self._pool_count_lbl')
print(f'Step 4: Replaced {count} remaining references')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
