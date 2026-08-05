"""
诊断数据库持久化问题
"""

import sys
sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')

print("=" * 80)
print("数据库持久化诊断")
print("=" * 80)

# 1. 测试数据库Registry导入
print("\n[测试1] 导入数据库Registry...")
try:
    from vnpy.quant_research.registry_db import ExperimentRegistryDB, DatasetRegistryDB
    print("  [OK] ExperimentRegistryDB 导入成功")
    print("  [OK] DatasetRegistryDB 导入成功")
except Exception as e:
    print(f"  [FAIL] 导入失败: {e}")
    import traceback
    traceback.print_exc()

# 2. 测试数据库连接
print("\n[测试2] 测试数据库连接...")
try:
    from vnpy.quant_research.database import get_database
    db = get_database()
    print(f"  [OK] 数据库连接成功: {db.db_path}")
except Exception as e:
    print(f"  [FAIL] 数据库连接失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 测试创建实验
print("\n[测试3] 测试创建实验...")
try:
    from vnpy.quant_research.registry_db import ExperimentRegistryDB
    from vnpy.quant_research.model.experiment_model import ExperimentRecord
    from vnpy.quant_research.constant import ExperimentStatus
    from datetime import datetime
    
    registry = ExperimentRegistryDB()
    
    # 创建测试实验
    test_exp = ExperimentRecord(
        experiment_id="TEST-DIAG-001",
        name="诊断测试实验",
        description="用于测试数据库持久化",
        status=ExperimentStatus.DRAFT,
        tags=["测试"],
        params={},
        metrics={},
        notes="",
        starred=False,
        created_by="诊断脚本",
        parent_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # 保存到数据库
    registry.create(test_exp)
    print("  [OK] 实验创建成功")
    
    # 查询实验
    loaded_exp = registry.get("TEST-DIAG-001")
    if loaded_exp:
        print(f"  [OK] 实验查询成功: {loaded_exp.name}")
    else:
        print("  [FAIL] 无法查询到刚创建的实验")
    
    # 列出所有实验
    all_exps = registry.list_all()
    print(f"  [OK] 数据库中共有 {len(all_exps)} 个实验")
    
    for exp in all_exps:
        print(f"    - {exp.experiment_id}: {exp.name}")
    
    # 删除测试数据
    registry.delete("TEST-DIAG-001")
    print("  [OK] 测试数据已清理")
    
except Exception as e:
    print(f"  [FAIL] 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 检查引擎是否使用数据库
print("\n[测试4] 检查引擎配置...")
try:
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy.quant_research.engine import ResearchEngine
    
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    research_engine = ResearchEngine(main_engine, event_engine)
    
    registry_type = type(research_engine.experiment_registry).__name__
    print(f"  [INFO] 实验Registry类型: {registry_type}")
    
    if 'DB' in registry_type:
        print("  [OK] 引擎正在使用数据库版本")
    else:
        print("  [WARNING] 引擎使用的是内存版本！")
        print("  [INFO] 这是数据不持久化的原因")
    
    # 清理
    main_engine.close()
    event_engine.stop()
    
except Exception as e:
    print(f"  [FAIL] 引擎测试失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 检查数据库文件
print("\n[测试5] 检查数据库文件...")
from pathlib import Path
import os

db_file = Path.home() / ".vnpy" / "quant_research" / "research.db"
print(f"  路径: {db_file}")
print(f"  存在: {db_file.exists()}")
if db_file.exists():
    size = os.path.getsize(db_file)
    print(f"  大小: {size:,} bytes ({size/1024:.2f} KB)")

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)
