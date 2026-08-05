"""
快速修复 USE_DATABASE 未定义错误
"""

import os

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

print("正在修复 USE_DATABASE 错误...")

# 读取文件
with open(engine_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找插入位置
insert_index = None
for i, line in enumerate(lines):
    if 'class ResearchEngine(BaseEngine):' in line:
        insert_index = i
        break

if insert_index is None:
    print("[错误] 未找到 ResearchEngine 类定义")
else:
    # 在类定义之前插入导入和变量定义
    new_lines = [
        "\n",
        "# 尝试导入数据库版本的Registry\n",
        "try:\n",
        "    from .registry_db import ExperimentRegistryDB, DatasetRegistryDB\n",
        "    USE_DATABASE = True\n",
        "except ImportError:\n",
        "    USE_DATABASE = False\n",
        "\n\n"
    ]
    
    # 在类定义前插入
    lines = lines[:insert_index] + new_lines + lines[insert_index:]
    
    # 写回文件
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("[完成] USE_DATABASE 变量已添加")
    print("请重新运行平台")
