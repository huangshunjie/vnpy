"""
修复feature_tab的UI刷新问题
让创建特征后立即显示在列表中
"""

import os
import re

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
feature_tab_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "ui", "feature_tab.py")

print("=" * 80)
print("修复feature_tab的UI刷新问题")
print("=" * 80)

with open(feature_tab_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已有事件刷新逻辑
if 'def _on_event' in content:
    print("[信息] feature_tab已有_on_event方法")
    
    # 检查延迟时间
    if 'QTimer.singleShot(100' in content:
        print("[修复] 将刷新延迟从100ms改为10ms")
        content = content.replace('QTimer.singleShot(100', 'QTimer.singleShot(10')
    elif 'QTimer.singleShot' not in content:
        print("[修复] _on_event方法中没有使用QTimer，添加延迟刷新")
        # 查找_on_event方法，添加QTimer延迟刷新
        pattern = r'(def _on_event\(self, event: Event\):)\s*\n\s*self\._refresh\(\)'
        replacement = r'\1\n        from PySide6.QtCore import QTimer\n        QTimer.singleShot(10, self._refresh)  # 延迟刷新避免卡顿'
        content = re.sub(pattern, replacement, content)
else:
    print("[警告] feature_tab没有_on_event方法，需要添加")
    # 这种情况需要更复杂的修复

# 检查_on_new方法，在创建后添加立即刷新
if 'def _on_new(self):' in content:
    # 查找register_feature调用后是否有立即刷新
    pattern = r'(self\._engine\.register_feature\([^)]+\))\s*\n(?!\s*self\._refresh)'
    
    if re.search(pattern, content):
        print("[修复] 在_on_new方法的register_feature后添加立即刷新")
        replacement = r'\1\n            self._refresh()  # 立即刷新显示'
        content = re.sub(pattern, replacement, content)

# 写回文件
with open(feature_tab_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "=" * 80)
print("修复完成！")
print("=" * 80)

print("\n修改内容:")
print("  1. 优化事件刷新延迟（如果存在）")
print("  2. 在创建特征后添加立即刷新（如果缺失）")

print("\n建议操作:")
print("  1. 先点击【重置】按钮刷新列表")
print("  2. 或者重启VN Trader")
print("  3. 之后创建新特征时应该立即显示")

print("\n" + "=" * 80)
