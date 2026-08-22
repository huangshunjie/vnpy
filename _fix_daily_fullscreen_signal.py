[0.06]claude-opus-4-8-c"""
修复日线全屏模式下分钟K线信号不显示的问题

根本原因：
之前的修复只处理了分钟面板的全屏窗口同步，
但用户场景是：在单周期模式下打开日线全屏窗口，
然后点击日线K线触发双周期联动，这时分钟面板的全屏窗口也需要同步。

解决方案：
需要在日线面板的 load_snapshots 方法中也添加全屏窗口同步逻辑。
这样当日线点击触发双周期时，日线和分钟的全屏窗口都能正确同步波形数据。
"""

import re
import sys
import io

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 读取文件
with open('vnpy/strategy_condition/ui/condition_monitor_widget.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 第一步：为日线面板（第一个 _PeriodMonitorPanel）的 load_snapshots 添加全屏同步
# 查找第一个 load_snapshots 中的 set_waveform_data 调用（约第628行）

pattern1 = r'(            # 同步波形数据到 KlineViewTab（供全屏窗口使用）\s+' \
           r'self\._kline_tab\.set_waveform_data\(\s+' \
           r'snapshots, dates,\s+' \
           r'buy_indices=buy_indices,\s+' \
           r'sell_indices=sell_indices,\s+' \
           r'\)\s+' \
           r'# 加载数据到波形图)'

replacement1 = r'''\1
            
            # 如果已有打开的全屏窗口，同步更新其波形数据
            fs_win = getattr(self._kline_tab, '_fullscreen_window', None)
            if fs_win and hasattr(fs_win, '_waveform_view'):
                fs_win._waveform_buy_indices = buy_indices or []
                fs_win._waveform_sell_indices = sell_indices or []
                fs_win._waveform_view.load_data(
                    snapshots, dates,
                    buy_indices=buy_indices,
                    sell_indices=sell_indices)
            '''

# 检查是否已经有这段代码（避免重复添加）
if '# 如果已有打开的全屏窗口，同步更新其波形数据' in content:
    # 已经有一个，检查是否有两个
    count = content.count('# 如果已有打开的全屏窗口，同步更新其波形数据')
    if count >= 2:
        print(f"修复代码已存在（找到{count}处），无需重复添加")
    else:
        print(f"只找到{count}处同步代码，需要为日线面板添加")
        # 只有一个，说明分钟面板有但日线面板没有，需要添加
        content = re.sub(pattern1, replacement1, content, count=1, flags=re.MULTILINE)
        
        # 写回文件
        with open('vnpy/strategy_condition/ui/condition_monitor_widget.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("已为日线面板添加全屏窗口同步逻辑")
        print("现在日线和分钟的全屏窗口都会正确同步波形信号显示")
else:
    print("未找到预期的代码模式，请手动检查")