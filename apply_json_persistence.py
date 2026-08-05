"""
应用JSON持久化到引擎
"""

import os

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

print("=" * 80)
print("应用JSON持久化到引擎")
print("=" * 80)

# 读取文件
with open(engine_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到导入Registry的位置
modified = False
new_lines = []

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # 在导入Registry后添加JSON Registry导入
    if 'from .registry import' in line and not modified:
        # 找到完整的导入块结束位置
        j = i + 1
        while j < len(lines) and (lines[j].strip().endswith(',') or lines[j].strip() == ')'):
            new_lines.append(lines[j])
            j += 1
        
        # 添加JSON持久化导入
        new_lines.append("\n# 导入JSON持久化版本\n")
        new_lines.append("from .registry_json import ExperimentRegistryJSON, DatasetRegistryJSON\n")
        
        # 跳过已经添加的行
        for k in range(i + 1, j):
            lines[k] = ''
        
        modified = True
        continue

# 修改Registry初始化
result_lines = []
for line in new_lines:
    if 'self.experiment_registry = ExperimentRegistry()' in line:
        result_lines.append('        self.experiment_registry = ExperimentRegistryJSON()  # JSON持久化\n')
    elif 'self.dataset_registry    = DatasetRegistry()' in line or 'self.dataset_registry = DatasetRegistry()' in line:
        result_lines.append('        self.dataset_registry    = DatasetRegistryJSON()     # JSON持久化\n')
    elif line.strip():  # 跳过空行
        result_lines.append(line)

# 写回文件
with open(engine_file, 'w', encoding='utf-8') as f:
    f.writelines(result_lines)

print("[完成] JSON持久化已应用到引擎")
print("\n修改内容:")
print("  1. 导入 ExperimentRegistryJSON 和 DatasetRegistryJSON")
print("  2. 使用JSON持久化Registry替代内存Registry")
print("\n数据保存位置:")
print("  - 实验: C:\\Users\\11229\\.vnpy\\quant_research\\experiments.json")
print("  - 数据集: C:\\Users\\11229\\.vnpy\\quant_research\\datasets.json")

print("\n" + "=" * 80)
print("重启VN Trader后，数据将自动保存并在重启后恢复！")
print("=" * 80)
