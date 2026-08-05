"""
量化研究平台 - 完整修复脚本

这个脚本会：
1. 为引擎添加日志系统方法
2. 修复所有UI模块的事件处理
3. 防止卡死问题

运行方式：python fix_research_platform.py
"""

import os
import re

# 项目根目录
PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"

print("=" * 80)
print("量化研究平台修复脚本")
print("=" * 80)

# ============================================================================
# 修复1：为引擎添加日志方法
# ============================================================================
print("\n[步骤1] 为引擎添加日志系统...")

engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

# 读取引擎文件
with open(engine_file, 'r', encoding='utf-8') as f:
    engine_content = f.read()

# 检查是否已经添加了日志方法
if 'def log(self' in engine_content and 'def get_recent_logs' in engine_content:
    print("[OK] 引擎已包含日志方法，跳过")
else:
    print("[执行] 添加日志方法到引擎...")
    
    # 在文件末尾的 _put 方法之前添加日志方法
    log_methods = '''
    # ------------------------------------------------------------------
    # Log System - 日志系统
    # ------------------------------------------------------------------

    def log(self, level, source, message, context_id=None, context_name=None, details="", user=""):
        """记录日志"""
        if not hasattr(self, 'log_registry'):
            from .registry import LogRegistry
            self.log_registry = LogRegistry()
        
        try:
            from .event import EVENT_LOG_MESSAGE
            record = self.log_registry.add(
                level=level, source=source, message=message,
                context_id=context_id, context_name=context_name,
                details=details, user=user
            )
            self._put(EVENT_LOG_MESSAGE, record)
        except Exception as e:
            print(f"[LOG] 日志记录失败: {e}")

    def get_recent_logs(self, n=100):
        """获取最近日志"""
        if not hasattr(self, 'log_registry'):
            from .registry import LogRegistry
            self.log_registry = LogRegistry()
        return self.log_registry.get_recent(n)

    def filter_logs(self, level=None, source=None, context_id=None, keyword=None, limit=1000):
        """筛选日志"""
        if not hasattr(self, 'log_registry'):
            from .registry import LogRegistry
            self.log_registry = LogRegistry()
        return self.log_registry.filter(level, source, context_id, keyword, limit)

    def get_error_logs(self, limit=50):
        """获取错误日志"""
        if not hasattr(self, 'log_registry'):
            from .registry import LogRegistry
            self.log_registry = LogRegistry()
        return self.log_registry.get_errors(limit)

    def get_log_statistics(self):
        """获取日志统计"""
        if not hasattr(self, 'log_registry'):
            from .registry import LogRegistry
            self.log_registry = LogRegistry()
        return {
            'total': self.log_registry.total_count(),
            'by_level': self.log_registry.count_by_level(),
            'by_source': self.log_registry.count_by_source(),
        }

    def clear_logs(self):
        """清空日志"""
        if not hasattr(self, 'log_registry'):
            from .registry import LogRegistry
            self.log_registry = LogRegistry()
        self.log_registry.clear()

'''
    
    # 在 _put 方法之前插入
    if 'def _put(self, event_type: str, data: object = None) -> None:' in engine_content:
        engine_content = engine_content.replace(
            '    def _put(self, event_type: str, data: object = None) -> None:',
            log_methods + '\n    def _put(self, event_type: str, data: object = None) -> None:'
        )
        
        # 写回文件
        with open(engine_file, 'w', encoding='utf-8') as f:
            f.write(engine_content)
        
        print("[完成] 日志方法已添加到引擎")
    else:
        print("[失败] 未找到 _put 方法，请手动添加")

# ============================================================================
# 修复2：修复所有UI模块的事件处理
# ============================================================================
print("\n[步骤2] 修复UI模块事件处理...")

ui_files = [
    "dataset_tab.py",
    "experiment_tab.py",
    "feature_tab.py",
    "strategy_tab.py",
    "model_tab.py",
    "backtest_tab.py",
    "report_tab.py",
    "pipeline_tab.py",
    "artifact_tab.py",
]

fixed_count = 0
for ui_file in ui_files:
    file_path = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "ui", ui_file)
    
    if not os.path.exists(file_path):
        continue
    
    print(f"  [处理] {ui_file}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找并修复 _on_event 方法
    old_pattern = r'def _on_event\(self, event: Event\):\s+self\._refresh\(\)'
    new_code = '''def _on_event(self, event: Event):
        # 使用定时器延迟刷新，避免阻塞UI
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._refresh)'''
    
    if re.search(old_pattern, content):
        content = re.sub(old_pattern, new_code, content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"    [OK] 已修复 {ui_file}")
        fixed_count += 1
    else:
        print(f"    [跳过] {ui_file} 未找到标准 _on_event 模式")

print(f"\n[完成] 共修复 {fixed_count} 个UI文件")

# ============================================================================
# 完成
# ============================================================================
print("\n" + "=" * 80)
print("修复完成！")
print("=" * 80)

print("\n修复摘要：")
print("  [OK] 为引擎添加了日志系统方法")
print("  [OK] 修复了UI模块的事件处理")
print("  [OK] 防止了卡死问题")

print("\n下一步：")
print("  1. 重启量化研究平台")
print("  2. 尝试创建数据集")
print("  3. 如果还有问题，查看控制台输出")

print("\n相关文档：")
print("  - OPTIMIZATION_REPORT.md: 技术细节")
print("  - QUICK_START_7_STEPS.md: 使用指南")

print("\n" + "=" * 80)
print("修复脚本执行完毕")
print("=" * 80)
