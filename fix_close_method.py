"""
修复 close() 方法清空数据库的问题
"""

import os
import re

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

print("正在修复 close() 方法...")

# 读取文件
with open(engine_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换 close() 方法
old_close = '''    def close(self) -> None:
        self.experiment_registry.clear()
        self.dataset_registry.clear()
        self.feature_registry.clear()
        self.strategy_registry.clear()
        self.model_registry.clear()
        self.backtest_registry.clear()
        self.report_registry.clear()
        self.pipeline_registry.clear()
        self.artifact_registry.clear()
        self.workspace_registry.clear()'''

new_close = '''    def close(self) -> None:
        # 注意：使用数据库持久化时，不应该清空数据
        # 只有内存版本的Registry才需要清空
        
        # 如果使用数据库，关闭数据库连接
        if USE_DATABASE:
            try:
                from .database import get_database
                get_database().close()
            except:
                pass
        else:
            # 内存版本才清空数据
            self.experiment_registry.clear()
            self.dataset_registry.clear()
            self.feature_registry.clear()
            self.strategy_registry.clear()
            self.model_registry.clear()
            self.backtest_registry.clear()
            self.report_registry.clear()
            self.pipeline_registry.clear()
            self.artifact_registry.clear()
            self.workspace_registry.clear()'''

if old_close in content:
    content = content.replace(old_close, new_close)
    
    # 写回文件
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[完成] close() 方法已修复")
    print("\n修改内容:")
    print("  - 使用数据库时不再清空数据")
    print("  - 只关闭数据库连接")
    print("  - 内存版本仍然会清空数据")
    print("\n现在重启平台，数据应该会保留！")
else:
    print("[错误] 未找到 close() 方法或格式已变化")
    print("请手动修改 engine.py 的 close() 方法")
