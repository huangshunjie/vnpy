"""
修复close()方法清空JSON持久化数据的问题
"""

import os
import re

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

print("=" * 80)
print("修复close()方法")
print("=" * 80)

# 读取文件
with open(engine_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换close方法
old_close = """    def close(self) -> None:
        self.experiment_registry.clear()
        self.dataset_registry.clear()
        self.feature_registry.clear()
        self.strategy_registry.clear()
        self.model_registry.clear()
        self.backtest_registry.clear()
        self.report_registry.clear()
        self.pipeline_registry.clear()
        self.artifact_registry.clear()
        self.workspace_registry.clear()"""

new_close = """    def close(self) -> None:
        # JSON持久化的Registry不应该清空数据
        # 只清空内存版本的Registry
        # self.experiment_registry.clear()  # JSON持久化，不清空
        # self.dataset_registry.clear()     # JSON持久化，不清空
        self.feature_registry.clear()
        self.strategy_registry.clear()
        self.model_registry.clear()
        self.backtest_registry.clear()
        self.report_registry.clear()
        self.pipeline_registry.clear()
        self.artifact_registry.clear()
        self.workspace_registry.clear()"""

if old_close in content:
    content = content.replace(old_close, new_close)
    
    # 写回文件
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[完成] close()方法已修复")
    print("\n修改内容:")
    print("  - 注释掉了 experiment_registry.clear()")
    print("  - 注释掉了 dataset_registry.clear()")
    print("  - 保留了其他内存Registry的clear()")
    print("\n现在关闭软件时，JSON持久化的数据不会被清空！")
else:
    print("[错误] 未找到close()方法或格式已变化")
    print("需要手动修改")

print("\n" + "=" * 80)
print("重新测试：创建实验 → 关闭软件 → 重启 → 数据应该保留！")
print("=" * 80)
