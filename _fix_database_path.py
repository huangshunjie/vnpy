# -*- coding: utf-8 -*-
"""修复数据库路径配置问题"""
import os
import sys
from pathlib import Path

# 强制使用UTF-8输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("数据库路径诊断与修复")
print("=" * 60)

# 1. 检查配置文件
config_file = Path.home() / ".vntrader" / "vt_setting.json"
print(f"\n1. 配置文件: {config_file}")
print(f"   存在: {config_file.exists()}")

if config_file.exists():
    import json
    with open(config_file, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    
    db_path_in_config = settings.get("database.database", "未设置")
    print(f"   配置的数据库路径: {db_path_in_config}")
    
    if db_path_in_config != "未设置":
        db_exists = os.path.exists(db_path_in_config)
        if db_exists:
            size_mb = os.path.getsize(db_path_in_config) / 1024 / 1024
            print(f"   [OK] 数据库文件存在")
            print(f"   大小: {size_mb:.2f} MB")
        else:
            print(f"   [ERR] 数据库文件不存在")

# 2. 检查程序实际使用的路径
print(f"\n2. 程序实际使用的数据库:")
from vnpy.trader.database import get_database

db = get_database()
print(f"   类型: {type(db).__name__}")

# 尝试找到实际路径
actual_path = None
for attr in ['db_path', 'db_file', 'filepath', 'db_name', 'database_path']:
    if hasattr(db, attr):
        val = getattr(db, attr)
        if val and isinstance(val, (str, Path)):
            actual_path = str(val)
            print(f"   实际路径 ({attr}): {actual_path}")
            break

if not actual_path:
    # 检查是否有 engine 属性
    if hasattr(db, 'engine'):
        engine_url = str(db.engine.url) if hasattr(db.engine, 'url') else None
        if engine_url:
            print(f"   Engine URL: {engine_url}")
            if 'sqlite' in engine_url:
                # 提取路径
                actual_path = engine_url.replace('sqlite:///', '').replace('/', '\\')
                print(f"   提取的路径: {actual_path}")

if not actual_path:
    print("   [WARN] 无法确定实际路径，检查所有包含路径的属性:")
    for attr in dir(db):
        if 'path' in attr.lower() or 'file' in attr.lower():
            try:
                val = getattr(db, attr)
                if isinstance(val, (str, Path)) and val:
                    print(f"      {attr}: {val}")
            except:
                pass

# 3. 测试能否查询数据
print(f"\n3. 测试数据库查询:")
try:
    overview = db.get_bar_overview()
    count = len(overview)
    print(f"   [OK] 查询成功")
    print(f"   合约数量: {count}")
    
    if count == 0:
        print(f"   [WARN] 数据库为空！")
    else:
        # 统计交易所
        from collections import Counter
        exchanges = Counter(key.exchange.value for key in overview.keys())
        print(f"   交易所分布:")
        for ex, cnt in exchanges.most_common():
            print(f"      {ex}: {cnt} 只")
except Exception as e:
    print(f"   [ERR] 查询失败: {e}")

# 4. 解决方案
print(f"\n" + "=" * 60)
print("解决方案:")
print("=" * 60)

if config_file.exists():
    with open(config_file, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    
    config_db = settings.get("database.database", "")
    
    if config_db and os.path.exists(config_db):
        print(f"\n[OK] 配置文件正确指向: {config_db}")
        print(f"\n但是程序可能没有重启加载配置。")
        print(f"\n请执行以下操作:")
        print(f"  1. 完全关闭当前运行的程序")
        print(f"  2. 重新启动程序")
        print(f"  3. 再次测试股票池功能")
    else:
        print(f"\n需要修复配置文件")
        
        # 检查E盘数据库
        e_db = r"E:\vnpy_data\database.db"
        if os.path.exists(e_db):
            print(f"\n找到E盘数据库: {e_db}")
            settings["database.database"] = e_db
            
            # 备份原配置
            backup_file = config_file.with_suffix('.json.bak')
            with open(config_file, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            print(f"[OK] 已备份原配置到: {backup_file}")
            
            # 写入新配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            print(f"[OK] 已更新配置文件")
            print(f"\n请重启程序以加载新配置！")
        else:
            print(f"[ERR] 未找到E盘数据库: {e_db}")
            print(f"请检查数据库文件位置")

print("\n" + "=" * 60)
