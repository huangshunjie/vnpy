"""
临时修复：禁用数据库功能，让应用正常显示
"""

import os

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

print("=" * 80)
print("临时禁用数据库功能")
print("=" * 80)

# 读取文件
with open(engine_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 强制禁用数据库
old_code = """# 尝试导入数据库版本的Registry
try:
    from .registry_db import ExperimentRegistryDB, DatasetRegistryDB
    USE_DATABASE = True
except ImportError:
    USE_DATABASE = False"""

new_code = """# 尝试导入数据库版本的Registry
# 临时禁用数据库功能，避免启动超时
USE_DATABASE = False

# try:
#     from .registry_db import ExperimentRegistryDB, DatasetRegistryDB
#     USE_DATABASE = True
# except ImportError:
#     USE_DATABASE = False"""

if old_code in content:
    content = content.replace(old_code, new_code)
    
    # 写回文件
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[完成] 数据库功能已临时禁用")
    print("\n说明:")
    print("  - 应用现在应该能正常显示了")
    print("  - 数据会保存在内存中（重启会丢失）")
    print("  - 这是临时方案，稍后我们会修复数据库问题")
    
else:
    print("[错误] 未找到目标代码")

print("\n" + "=" * 80)
print("请重启VN Trader，应用应该会重新出现")
print("=" * 80)
