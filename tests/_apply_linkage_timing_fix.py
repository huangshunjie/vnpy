# -*- coding: utf-8 -*-
"""应用日线分钟联动时序修复"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

file_path = os.path.join(project_root, 'vnpy', 'strategy_condition', 'ui', 'kline_view.py')

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要修改的位置（在 _on_chart_bar_clicked 方法中）
modified = False
for i in range(len(lines)):
    # 查找 "self._pending_focus_signals = signals" 这一行
    if 'self._pending_focus_signals = signals' in lines[i] and 'self._pending_focus_date = target_date' in lines[i-1]:
        # 在其后插入缓存清除代码
        indent = ' ' * 12  # 12个空格缩进
        insert_lines = [
            '\n',
            f'{indent}# 清除缓存键，强制重新加载\n',
            f'{indent}self._cache_key = ()\n',
        ]
        lines[i+1:i+1] = insert_lines
        modified = True
        print(f"已在第 {i+2} 行添加缓存清除代码")
        break

if not modified:
    print("未找到插入点，检查代码结构")
    sys.exit(1)

# 找到 blockSignals(False) 后插入 processEvents
for i in range(len(lines)):
    if 'self._interval_cb.blockSignals(False)' in lines[i]:
        # 在 finally 块后插入 processEvents
        for j in range(i+1, min(i+5, len(lines))):
            if lines[j].strip() == '':
                indent = ' ' * 12
                insert_lines = [
                    f'{indent}# 强制处理GUI事件，确保下拉框状态更新完成\n',
                    f'{indent}from vnpy.trader.ui import QtWidgets\n',
                    f'{indent}QtWidgets.QApplication.processEvents()\n',
                    '\n',
                ]
                lines[j:j] = insert_lines
                print(f"已在第 {j+1} 行添加 processEvents 调用")
                break
        break

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\n修复已成功应用到: {file_path}")
print("\n修复内容:")
print("1. 在切换周期前清除缓存键 (_cache_key = ())，强制重新加载")
print("2. 调用 processEvents() 确保GUI状态完全更新")
print("\n这样后台线程读取周期索引时能获取到正确的5分钟周期值")
