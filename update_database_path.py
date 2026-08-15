"""
更新 VeighNa 数据库路径配置
将数据库路径从 D 盘修改为 E 盘
"""
import json
from pathlib import Path

# 配置文件路径
config_path = Path.home() / ".vntrader" / "vt_setting.json"

print(f"正在读取配置文件: {config_path}")

# 读取配置
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# 显示当前配置
old_path = config.get("database.database", "")
print(f"当前数据库路径: {old_path}")

# 修改路径
new_path = "E:\\vnpy_data\\database.db"
config["database.database"] = new_path

# 保存配置
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print(f"已更新数据库路径: {new_path}")
print("\n配置文件已更新成功！")