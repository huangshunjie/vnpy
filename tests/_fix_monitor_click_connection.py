"""修复Monitor日线点击事件连接问题"""
import sys
sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')

# 读取文件
with open(r'vnpy\strategy_condition\ui\condition_monitor_widget.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 问题诊断：
# 1. _connect_daily_click_handler 在 __init__ 中被过早调用
# 2. 此时 _kline_tab._chart 可能还没有初始化完成
# 3. 需要延迟连接，在 load_snapshots 完成加载后再连接

# 修复方案：
# 1. 在 load_snapshots 结束时调用 _connect_daily_click_handler
# 2. 确保K线图已经完全加载后再连接信号

# 查找并移除 __init__ 中的过早连接
old_init_call = """        # 连接日线点击事件
        self._connect_daily_click_handler()"""

# 在 ConditionMonitorPanel 的 __init__ 中移除过早的连接
if old_init_call in content:
    content = content.replace(old_init_call, """        # 日线点击事件将在 load_snapshots 完成后连接
        self._click_handler_connected = False""")
    print("✓ 已移除__init__中的过早连接")
else:
    # 如果找不到，尝试其他变体
    patterns = [
        "self._connect_daily_click_handler()",
        "self. _connect_daily_click_handler()",
    ]
    found = False
    for pattern in patterns:
        if pattern in content and "__init__" in content[max(0, content.index(pattern)-500):content.index(pattern)]:
            # 找到了在__init__附近的调用
            print(f"⚠ 发现模式: {pattern}")
            found = True
            break
    if not found:
        print("⚠ 未找到__init__中的连接调用，可能已经被修改过")

# 在 load_snapshots 末尾添加连接逻辑
# 查找 load_snapshots 方法的结尾
marker = """            self._sync_plots()
        else:
            self._waveform_view.load_data([])"""

if marker in content:
    # 在此处添加连接逻辑
    addition = """            self._sync_plots()
            
            # 确保日线点击事件已连接（延迟连接，确保K线图已完全加载）
            if not self._click_handler_connected:
                QtCore.QTimer.singleShot(100, self._connect_daily_click_handler)
                self._click_handler_connected = True
        else:
            self._waveform_view.load_data([])"""
    
    content = content.replace(marker, addition)
    print("✓ 已在load_snapshots结尾添加延迟连接逻辑")
else:
    print("⚠ 未找到load_snapshots的预期标记点")

# 修改 _connect_daily_click_handler 使其更健壮
old_connect_method = """    def _connect_daily_click_handler(self):
        \"\"\"连接日线K线点击处理器\"\"\"
        try:
            if hasattr(self._kline_tab, '_chart'):
                self._kline_tab._chart.bar_clicked.connect(
                    self._on_bar_clicked)
        except Exception as e:
            print(f"[联动] 连接日线点击失败: {e}")"""

new_connect_method = """    def _connect_daily_click_handler(self):
        \"\"\"连接日线K线点击处理器（延迟连接，确保K线图已加载）\"\"\"
        try:
            if not hasattr(self, '_kline_tab'):
                print("[联动] _kline_tab 不存在，跳过连接")
                return
            
            kline_tab = self._kline_tab
            if not hasattr(kline_tab, '_chart'):
                print("[联动] _kline_tab._chart 不存在，跳过连接")
                return
            
            chart = kline_tab._chart
            if not hasattr(chart, 'bar_clicked'):
                print("[联动] _chart.bar_clicked 信号不存在，跳过连接")
                return
            
            # 检查是否已经连接过
            if hasattr(self, '_bar_clicked_connected') and self._bar_clicked_connected:
                print("[联动] 日线点击事件已经连接过，跳过重复连接")
                return
            
            # 连接信号
            chart.bar_clicked.connect(self._on_bar_clicked)
            self._bar_clicked_connected = True
            print(f"[联动] ✓ 日线K线点击事件连接成功")
            
        except Exception as e:
            print(f"[联动] ✗ 连接日线点击失败: {e}")
            import traceback
            traceback.print_exc()"""

if old_connect_method in content:
    content = content.replace(old_connect_method, new_connect_method)
    print("✓ 已增强_connect_daily_click_handler方法的健壮性")
else:
    print("⚠ 未找到_connect_daily_click_handler方法，可能已被修改")

# 写回文件
with open(r'vnpy\strategy_condition\ui\condition_monitor_widget.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n修复完成！主要改动:")
print("1. 移除了__init__中的过早连接")
print("2. 在load_snapshots完成后延迟100ms连接")
print("3. 增强了_connect_daily_click_handler的健壮性和调试输出")
print("\n请重启应用测试日线点击联动功能")