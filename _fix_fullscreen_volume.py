#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复全屏K线图无法显示成交量的问题

问题：_FullscreenChart._build_ui() 中 line 1369 设置 self._glw_vol.setVisible(False)
修复：改为 setVisible(True)，因为工具栏的"成交量"复选框默认勾选
"""

import os
import sys

def fix_fullscreen_volume():
    file_path = 'vnpy/strategy_condition/ui/kline_view.py'
    
    if not os.path.exists(file_path):
        print(f"错误：找不到文件 {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 _FullscreenChart 类
    class_marker = 'class _FullscreenChart'
    class_pos = content.find(class_marker)
    
    if class_pos == -1:
        print(f"错误：找不到 {class_marker}")
        return False
    
    # 在类定义之后查找 setVisible(False)
    target = 'self._glw_vol.setVisible(False)'
    target_pos = content.find(target, class_pos)
    
    if target_pos == -1:
        print("错误：找不到 self._glw_vol.setVisible(False)")
        print("可能已经修复过了")
        return False
    
    # 替换
    new_content = content[:target_pos] + 'self._glw_vol.setVisible(True)' + content[target_pos + len(target):]
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # 显示修改位置的上下文
    line_num = content[:target_pos].count('\n') + 1
    print(f"✓ 修复成功！")
    print(f"文件：{file_path}")
    print(f"行号：约 {line_num}")
    print(f"修改：setVisible(False) → setVisible(True)")
    
    return True

if __name__ == '__main__':
    success = fix_fullscreen_volume()
    sys.exit(0 if success else 1)