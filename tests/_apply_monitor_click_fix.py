"""应用Monitor日线点击事件连接修复"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')

# 读取文件
with open(r'vnpy\strategy_condition\ui\condition_monitor_widget.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找并修复
modified = False
new_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    
    # 1. 查找 ConditionMonitorPanel 的 __init__ 中的早期连接
    if 'class ConditionMonitorPanel' in line:
        # 找到类定义，寻找 __init__ 方法
        new_lines.append(line)
        i += 1
        in_init = False
        while i < len(lines):
            line = lines[i]
            if 'def __init__' in line and 'ConditionMonitorPanel' in ''.join(new_lines[-20:]):
                in_init = True
            
            # 移除 __init__ 中的 _connect_daily_click_handler 调用
            if in_init and '_connect_daily_click_handler()' in line:
                # 替换为初始化标志
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + '# 日线点击事件将在数据加载后延迟连接\n')
                new_lines.append(' ' * indent + 'self._click_handler_connected = False\n')
                print("已移除__init__中的过早连接调用")
                modified = True
                i += 1
                continue
            
            new_lines.append(line)
            
            # __init__ 方法结束
            if in_init and line.strip() and not line.strip().startswith('#') and not line[0].isspace():
                break
            i += 1
        continue
    
    # 2. 在load_snapshots结尾添加延迟连接
    if 'self._sync_plots()' in line and i + 1 < len(lines) and 'else:' in lines[i+1]:
        new_lines.append(line)
        new_lines.append('\n')
        indent = len(line) - len(line.lstrip())
        new_lines.append(' ' * indent + '# 延迟连接日线点击事件（确保K线图已完全加载)\n')
        new_lines.append(' ' * indent + 'if not self._click_handler_connected:\n')
        new_lines.append(' ' * (indent + 4) + 'QtCore.QTimer.singleShot(100, self._connect_daily_click_handler)\n')
        new_lines.append(' ' * (indent + 4) + 'self._click_handler_connected = True\n')
        print("已在load_snapshots结尾添加延迟连接")
        modified = True
        i += 1
        continue
    
    # 3. 增强 _connect_daily_click_handler 方法
    if 'def _connect_daily_click_handler(self):' in line:
        # 找到方法，替换整个实现
        indent = len(line) - len(line.lstrip())
        new_lines.append(line)
        i += 1
        
        # 跳过原来的实现
        while i < len(lines):
            if lines[i].strip() and not lines[i][0].isspace():
                break
            if 'def ' in lines[i] and lines[i].strip().startswith('def'):
                break
            i += 1
        
        # 写入新实现
        new_lines.append(' ' * (indent + 4) + '"""连接日线K线点击处理器（延迟连接）"""\n')
        new_lines.append(' ' * (indent + 4) + 'try:\n')
        new_lines.append(' ' * (indent + 8) + 'if not hasattr(self, \'_kline_tab\'):\n')
        new_lines.append(' ' * (indent + 12) + 'return\n')
        new_lines.append(' ' * (indent + 8) + '\n')
        new_lines.append(' ' * (indent + 8) + 'kline_tab = self._kline_tab\n')
        new_lines.append(' ' * (indent + 8) + 'if not hasattr(kline_tab, \'_chart\'):\n')
        new_lines.append(' ' * (indent + 12) + 'return\n')
        new_lines.append(' ' * (indent + 8) + '\n')
        new_lines.append(' ' * (indent + 8) + 'chart = kline_tab._chart\n')
        new_lines.append(' ' * (indent + 8) + 'if not hasattr(chart, \'bar_clicked\'):\n')
        new_lines.append(' ' * (indent + 12) + 'return\n')
        new_lines.append(' ' * (indent + 8) + '\n')
        new_lines.append(' ' * (indent + 8) + '# 避免重复连接\n')
        new_lines.append(' ' * (indent + 8) + 'if hasattr(self, \'_bar_clicked_connected\') and self._bar_clicked_connected:\n')
        new_lines.append(' ' * (indent + 12) + 'return\n')
        new_lines.append(' ' * (indent + 8) + '\n')
        new_lines.append(' ' * (indent + 8) + 'chart.bar_clicked.connect(self._on_bar_clicked)\n')
        new_lines.append(' ' * (indent + 8) + 'self._bar_clicked_connected = True\n')
        new_lines.append(' ' * (indent + 8) + 'print(f"[联动] 日线K线点击事件已连接")\n')
        new_lines.append(' ' * (indent + 4) + 'except Exception as e:\n')
        new_lines.append(' ' * (indent + 8) + 'print(f"[联动] 连接失败: {e}")\n')
        new_lines.append('\n')
        print("已增强_connect_daily_click_handler方法")
        modified = True
        continue
    
    new_lines.append(line)
    i += 1

if modified:
    # 写回文件
    with open(r'vnpy\strategy_condition\ui\condition_monitor_widget.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("\n修复完成！")
    print("主要改动:")
    print("1. 移除__init__中的过早连接")
    print("2. 在load_snapshots完成后延迟100ms连接")
    print("3. 增强_connect_daily_click_handler的健壮性")
    print("\n请重启应用测试")
else:
    print("未发现需要修改的代码，可能已经修复过")