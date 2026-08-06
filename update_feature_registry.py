"""
更新引擎使用FeatureRegistryJSON
"""

import os

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")
registry_json_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "registry_json.py")

print("=" * 80)
print("更新引擎使用FeatureRegistryJSON")
print("=" * 80)

# 1. 更新registry_json.py的导入
print("\n[步骤1] 更新registry_json.py的导入...")
with open(registry_json_file, 'r', encoding='utf-8') as f:
    registry_content = f.read()

# 确保导入了FeatureRegistryJSON需要的模块
if "from .model.feature_model import FeatureRecord" not in registry_content:
    # 在文件顶部的导入区域添加
    import_line = "from .model.feature_model import FeatureRecord\n"
    # 找到model导入的位置
    import_pos = registry_content.find("from .model.dataset_model import DatasetRecord")
    if import_pos > 0:
        # 在DatasetRecord导入后添加
        insert_pos = registry_content.find("\n", import_pos) + 1
        registry_content = registry_content[:insert_pos] + import_line + registry_content[insert_pos:]
        
        with open(registry_json_file, 'w', encoding='utf-8') as f:
            f.write(registry_content)
        print("[OK] 已更新registry_json.py的导入")

# 2. 更新engine.py使用FeatureRegistryJSON
print("\n[步骤2] 更新engine.py使用FeatureRegistryJSON...")
with open(engine_file, 'r', encoding='utf-8') as f:
    engine_content = f.read()

# 更新导入语句
old_import = "from .registry_json import ExperimentRegistryJSON, DatasetRegistryJSON"
new_import = "from .registry_json import ExperimentRegistryJSON, DatasetRegistryJSON, FeatureRegistryJSON"

if old_import in engine_content and new_import not in engine_content:
    engine_content = engine_content.replace(old_import, new_import)
    print("[OK] 已更新导入语句")

# 更新Registry初始化
old_init = "self.feature_registry    = FeatureRegistry()"
new_init = "self.feature_registry    = FeatureRegistryJSON()     # JSON持久化"

if old_init in engine_content:
    engine_content = engine_content.replace(old_init, new_init)
    print("[OK] 已更新FeatureRegistry为JSON版本")

# 更新close()方法，注释掉feature_registry.clear()
old_close_line = "        self.feature_registry.clear()"
new_close_line = "        # self.feature_registry.clear()  # JSON持久化，不清空"

if old_close_line in engine_content and new_close_line not in engine_content:
    engine_content = engine_content.replace(old_close_line, new_close_line)
    print("[OK] 已更新close()方法")

# 写回文件
with open(engine_file, 'w', encoding='utf-8') as f:
    f.write(engine_content)

print("\n" + "=" * 80)
print("更新完成！")
print("=" * 80)

print("\n修改内容:")
print("  1. registry_json.py - 添加了FeatureRegistryJSON")
print("  2. engine.py - 导入FeatureRegistryJSON")
print("  3. engine.py - 使用FeatureRegistryJSON()而不是FeatureRegistry()")
print("  4. engine.py - close()方法不清空feature_registry")

print("\n特征数据将保存到:")
print("  C:\\Users\\11229\\.vnpy\\quant_research\\features.json")

print("\n" + "=" * 80)
print("请关闭卡住的对话框，然后重启VN Trader！")
print("=" * 80)
