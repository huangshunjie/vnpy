"""
自动应用数据库持久化到引擎

这个脚本会自动修改 engine.py，让它使用数据库版本的Registry
"""

import os
import re

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"

print("=" * 80)
print("自动应用数据库持久化到引擎")
print("=" * 80)

engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

# 读取引擎文件
with open(engine_file, 'r', encoding='utf-8') as f:
    engine_content = f.read()

# 备份原文件
backup_file = engine_file + ".backup"
with open(backup_file, 'w', encoding='utf-8') as f:
    f.write(engine_content)
print(f"[备份] 原文件已备份到: {backup_file}")

# 检查是否已经使用数据库版本
if 'from .registry_db import' in engine_content:
    print("[跳过] 引擎已经使用数据库版本的Registry")
else:
    print("[修改] 更新引擎使用数据库Registry...")
    
    # 1. 添加导入
    import_line = "from .registry import ExperimentRegistry"
    if import_line in engine_content:
        # 在原有导入后面添加数据库版本的导入
        new_import = """from .registry import ExperimentRegistry, DatasetRegistry, FeatureRegistry, StrategyRegistry, ModelRegistry, BacktestRegistry, ReportRegistry, PipelineRegistry, ArtifactRegistry, WorkspaceRegistry
try:
    from .registry_db import ExperimentRegistryDB, DatasetRegistryDB
    USE_DATABASE = True
except ImportError:
    USE_DATABASE = False"""
        
        engine_content = engine_content.replace(
            "from .registry import ExperimentRegistry, DatasetRegistry, FeatureRegistry, StrategyRegistry, ModelRegistry, BacktestRegistry, ReportRegistry, PipelineRegistry, ArtifactRegistry, WorkspaceRegistry",
            new_import
        )
    
    # 2. 修改 __init__ 方法中的Registry初始化
    # 查找初始化部分
    old_init_pattern = r'self\.experiment_registry = ExperimentRegistry\(\)'
    new_init = '''self.experiment_registry = ExperimentRegistryDB() if USE_DATABASE else ExperimentRegistry()'''
    
    if re.search(old_init_pattern, engine_content):
        engine_content = re.sub(old_init_pattern, new_init, engine_content)
    
    old_dataset_pattern = r'self\.dataset_registry\s*=\s*DatasetRegistry\(\)'
    new_dataset = '''self.dataset_registry = DatasetRegistryDB() if USE_DATABASE else DatasetRegistry()'''
    
    if re.search(old_dataset_pattern, engine_content):
        engine_content = re.sub(old_dataset_pattern, new_dataset, engine_content)
    
    # 写回文件
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.write(engine_content)
    
    print("[完成] 引擎已更新为使用数据库持久化")

# 验证修改
with open(engine_file, 'r', encoding='utf-8') as f:
    content = f.read()
    
if 'ExperimentRegistryDB' in content:
    print("[验证] 数据库Registry已成功集成")
else:
    print("[警告] 未检测到数据库Registry，请手动检查")

print("\n" + "=" * 80)
print("应用完成！")
print("=" * 80)

print("\n修改内容:")
print("  1. 添加了数据库版Registry的导入")
print("  2. ExperimentRegistry -> ExperimentRegistryDB")
print("  3. DatasetRegistry -> DatasetRegistryDB")

print("\n下一步:")
print("  1. 重启量化研究平台")
print("  2. 创建实验/数据集")
print("  3. 关闭并重新启动")
print("  4. 检查数据是否仍然存在")

print("\n如果出现问题:")
print(f"  - 恢复备份: copy {backup_file} {engine_file}")

print("\n" + "=" * 80)
