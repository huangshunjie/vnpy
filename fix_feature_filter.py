"""
修复FeatureRegistryJSON的filter方法
"""

import os
import re

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
registry_json_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "registry_json.py")

print("=" * 80)
print("修复FeatureRegistryJSON的filter方法")
print("=" * 80)

with open(registry_json_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复filter方法，添加author参数
old_filter = """    def filter(self, status=None, category=None, tag=None):
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if category:
            result = [r for r in result if r.category == category]
        if tag:
            result = [r for r in result if tag in r.tags]
        return result"""

new_filter = """    def filter(self, status=None, category=None, tag=None, author=None):
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if category:
            result = [r for r in result if r.category == category]
        if tag:
            result = [r for r in result if tag in r.tags]
        if author:
            result = [r for r in result if author.lower() in r.author.lower()]
        return result"""

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    
    with open(registry_json_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[完成] filter方法已修复，添加了author参数")
else:
    print("[警告] 未找到准确匹配，尝试正则表达式替换...")
    
    # 使用正则表达式查找并替换
    pattern = r'def filter\(self, status=None, category=None, tag=None\):'
    replacement = r'def filter(self, status=None, category=None, tag=None, author=None):'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        
        # 在return result之前添加author过滤
        pattern2 = r'(if tag:\s+result = \[r for r in result if tag in r\.tags\]\s+)(return result)'
        replacement2 = r'\1if author:\n            result = [r for r in result if author.lower() in r.author.lower()]\n        \2'
        content = re.sub(pattern2, replacement2, content)
        
        with open(registry_json_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("[完成] 已使用正则表达式修复")
    else:
        print("[错误] 无法找到filter方法")

print("\n" + "=" * 80)
print("修复完成！")
print("=" * 80)
print("\n修改内容:")
print("  - filter()方法添加了author参数")
print("  - 添加了author过滤逻辑")
print("\n现在重启VN Trader应该可以正常进入了！")
print("=" * 80)
