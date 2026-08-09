# -*- coding: utf-8 -*-
"""修复 _on_pool_loaded：QMessageBox 应在 else 块内"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\behavior_tab.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到问题区域
# 结构应该是:
#   if symbols:
#       self._pool_edit.setPlainText(...)
#       self._pool_count_lbl.setText(...)
#   else:
#       self._pool_edit.setPlainText("")
#       from ... import QMessageBox
#       QMessageBox.warning(...)
#
# 但现在 from 和 QMessageBox 在 else 块外面

for i in range(len(lines)):
    if '_on_pool_loaded' in lines[i] and 'def ' in lines[i]:
        # 找到方法开始，向下搜索修复
        for j in range(i, min(i + 30, len(lines))):
            # 找到 else: 行
            if lines[j].strip() == 'else:' and j > i:
                # else 后面应有正确缩进的内容
                # 找到 from PySide6... 和 QMessageBox.warning
                for k in range(j + 1, min(j + 10, len(lines))):
                    if 'from PySide6.QtWidgets import QMessageBox' in lines[k]:
                        # 确保缩进正确（应在 else 块内，12个空格）
                        lines[k] = '            from PySide6.QtWidgets import QMessageBox\n'
                        print(f"Fixed import indent at line {k+1}")
                    if 'QMessageBox.warning' in lines[k] and '\u7b5b\u9009\u7ed3\u679c' in lines[k]:
                        lines[k] = '            QMessageBox.warning(self, "\u7b5b\u9009\u7ed3\u679c", f"\u672a\u627e\u5230 \'{label}\' \u7684\u80a1\u7968\u6570\u636e")\n'
                        print(f"Fixed QMessageBox indent at line {k+1}")
                break
        break

# 同时删掉 else 和 from 之间的多余空行（只保留格式整洁）
# 重新读取修改后的行
content = ''.join(lines)

# 清理：把 else 块中的空白行问题处理好
old_pattern = '''        else:\n\n            self._pool_edit.setPlainText("")\n\n        from PySide6.QtWidgets import QMessageBox\n        \n        QMessageBox.warning'''
new_pattern = '''        else:\n\n            self._pool_edit.setPlainText("")\n\n            from PySide6.QtWidgets import QMessageBox\n\n            QMessageBox.warning'''

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    print("Also fixed via pattern replacement")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
