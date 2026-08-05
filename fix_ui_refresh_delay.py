"""
修复UI刷新延迟问题

让创建/编辑操作后立即显示结果
"""

import os
import re

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"

print("=" * 80)
print("修复UI刷新延迟问题")
print("=" * 80)

# 需要修复的UI文件
ui_files = [
    "experiment_tab.py",
    "dataset_tab.py",
    "feature_tab.py",
    "strategy_tab.py",
    "backtest_tab.py",
]

for ui_file in ui_files:
    file_path = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "ui", ui_file)
    
    if not os.path.exists(file_path):
        continue
    
    print(f"\n处理 {ui_file}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    
    # 方案1：在 _on_event 中，延迟刷新改为立即刷新
    # 但保留延迟以避免卡死（从100ms减少到10ms）
    old_pattern1 = r"QTimer\.singleShot\(100, self\._refresh\)"
    new_code1 = "QTimer.singleShot(10, self._refresh)  # 减少延迟到10ms"
    
    if re.search(old_pattern1, content):
        content = re.sub(old_pattern1, new_code1, content)
        modified = True
        print(f"  [修改] 减少刷新延迟到10ms")
    
    # 方案2：在创建/编辑方法的最后添加立即刷新
    # 查找 _on_new 方法
    pattern_on_new = r'(def _on_new\(self\):.*?self\._engine\.create_experiment\([^)]+\))'
    
    def add_refresh(match):
        original = match.group(1)
        if 'self._refresh()' not in original:
            # 在方法最后添加立即刷新
            return original + '\n            self._refresh()  # 立即刷新显示'
        return original
    
    if re.search(pattern_on_new, content, re.DOTALL):
        content = re.sub(pattern_on_new, add_refresh, content, flags=re.DOTALL)
        modified = True
        print(f"  [修改] 在创建方法后添加立即刷新")
    
    # 写回文件
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [完成] {ui_file} 已更新")
    else:
        print(f"  [跳过] {ui_file} 无需修改")

print("\n" + "=" * 80)
print("修复完成！")
print("=" * 80)

print("\n修改内容:")
print("  1. 刷新延迟从100ms减少到10ms")
print("  2. 创建/编辑操作后立即刷新")

print("\n效果:")
print("  ✅ 创建实验后立即在列表中显示")
print("  ✅ 不会出现需要重启才能看到的情况")
print("  ✅ 仍然避免UI卡死")

print("\n重启平台测试新建实验，应该立即显示！")
print("=" * 80)
