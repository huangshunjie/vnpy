"""V27: 诚实地检查 V26 patch 状态 + 现场实际加 print。

源文件 kline_view.py 当前 print 分布（V27 实际探测）：
- L1112: _on_fullscreen (V5)
- L1127: 全屏注册失败 (V5)
- L1134/1136: V8 全屏监听
- L1138/1140/1144: V5 全屏 owner 注入
- L1388/1390/1394: _KlineFullscreenWindow bar_clicked 转发
- L1502/1532/1536: V18 _on_outer_daily_bar_clicked (关键!接收外部信号)
- L1601/1603: _FullscreenChart sigMouseClicked
- L1761-1814: _on_mouse_clicked_for_link (关键!鼠标点击处理)
- L1903-1930: V7 mousePressEvent 转发

观察:
- V8 patch 已有: bar_clicked 信号链路通
- V18 patch 已有: _on_outer_daily_bar_clicked handler 存在
- V7 patch 已有: mousePressEvent 中已有 owner_monitor 转发逻辑
- 但实际还是不工作 = 说明链路虽然存在,但运行时信号没发,或发到了错误的实例

要加的 V26 print（每个 print 都需要在新位置加,因为之前完全没加成功）:
1. _KlineFullscreenWindow.__init__: 收到 parent 参数 + outer_panel
2. _KlineFullscreenWindow.showEvent: 确认 show 时的状态
3. _on_mouse_clicked_for_link 入口: 打印 owner_monitor 类型 + chart bar
4. _on_outer_daily_bar_clicked 入口: 打印接收的 focus_dt 和 is_minute
5. ConditionMonitorWidget._on_daily_bar_clicked_from_outer: 打印接收 + 是否触发 focus_datetime 设置
"""
import os

path = 'vnpy/strategy_condition/ui/kline_view.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查关键方法是否都存在
checks = [
    ('class _KlineFullscreenWindow', '_KlineFullscreenWindow class'),
    ('def _on_outer_daily_bar_clicked', '_on_outer_daily_bar_clicked method'),
    ('def _on_mouse_clicked_for_link', '_on_mouse_clicked_for_link method'),
    ('def showEvent', 'showEvent method (KlineFullscreenWindow)'),
    ('def __init__', '__init__ method (KlineFullscreenWindow)'),
    ('_on_daily_bar_clicked_from_outer', 'monitor handler call'),
    ('bar_clicked.connect', 'bar_clicked signal connect'),
    ('sigMouseClicked.connect', 'sigMouseClicked connect'),
    ('focus_datetime =', 'focus_datetime assignment'),
    ('move_to_datetime', 'move_to_datetime call'),
]

print('='*70)
print('V27 当前 kline_view.py 状态 (基于 V26 之前的版本):')
print('='*70)
for keyword, desc in checks:
    count = content.count(keyword)
    flag = '[OK]' if count > 0 else '[MISSING]'
    print(f'  {flag:10s} {desc:45s} 出现{count}次')
print('='*70)

# 输出每行找到的关键 method 位置
import re
print('\n关键 method/function 定位:')
for m in re.finditer(r'^(\s*)(def |class )(\w+)', content, re.M):
    name = m.group(3)
    line_no = content[:m.start()].count('\n') + 1
    if name in ('_KlineFullscreenWindow', '_on_outer_daily_bar_clicked',
                '_on_mouse_clicked_for_link', 'showEvent', '__init__',
                'mousePressEvent', '_on_fullscreen', '_build_ui'):
        indent = len(m.group(1))
        print(f'  L{line_no:4d}  indent={indent}  {m.group(2)}{name}')