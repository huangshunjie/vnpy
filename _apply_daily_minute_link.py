#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用日线分钟K线联动功能补丁
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
kline_view_path = project_root / "vnpy" / "strategy_condition" / "ui" / "kline_view.py"

print("=" * 60)
print("应用日线分钟K线联动功能补丁")
print("=" * 60)

# 读取原文件
with open(kline_view_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已应用补丁
if 'focus_on_date' in content:
    print("\n✓ 补丁已应用，无需重复操作")
    sys.exit(0)

print("\n正在应用补丁...")

# 在 KlineViewTab 类中添加 focus_on_date 方法
# 查找插入位置：set_waveform_data 方法之后
insert_marker = "    def set_waveform_data("
if insert_marker not in content:
    print("✗ 未找到插入点")
    sys.exit(1)

# 找到 set_waveform_data 方法的结束位置
parts = content.split(insert_marker)
before = parts[0]
after_start = insert_marker + parts[1]

# 找到该方法结束的位置（下一个同级方法定义或类结束）
lines = after_start.split('\n')
method_end_idx = 0
indent_count = 0
for i, line in enumerate(lines[1:], 1):  # 跳过方法定义行
    if line.strip() and not line.startswith('        '):  # 找到同级或更外层代码
        if line.startswith('    def ') or line.startswith('class '):
            method_end_idx = i
            break

if method_end_idx == 0:
    print("✗ 未找到方法结束位置")
    sys.exit(1)

before_method_end = '\n'.join(lines[:method_end_idx])
after_method_end = '\n'.join(lines[method_end_idx:])

# 新增的方法代码
new_methods = '''
    def focus_on_date(self, target_date, signals=None):
        """聚焦到指定日期，并更新信号标记
        
        Args:
            target_date: date 对象
            signals: dict, {'buy': [dt1, dt2,...], 'sell': [dt1, dt2,...]}
        """
        try:
            if not hasattr(self, '_chart') or not self._chart:
                return
            
            if not hasattr(self._chart, '_datetimes') or not self._chart._datetimes:
                return
            
            datetimes = self._chart._datetimes
            
            # 找到该日期的所有K线索引
            target_indices = [
                i for i, dt in enumerate(datetimes)
                if dt.date() == target_date
            ]
            
            if not target_indices:
                print(f"[联动] 未找到日期 {target_date} 的分钟数据")
                return
            
            start_idx = min(target_indices)
            end_idx = max(target_indices)
            
            print(f"[联动] 聚焦到日期 {target_date}, 索引范围: {start_idx}-{end_idx}")
            
            # 设置显示范围（前后各留5根）
            padding = 5
            x_min = max(0, start_idx - padding)
            x_max = min(len(datetimes) - 1, end_idx + padding)
            
            if hasattr(self._chart, '_main_plot'):
                self._chart._main_plot.setXRange(x_min, x_max, padding=0.02)
            
            # 更新信号标记
            if signals:
                self._update_signals_display(signals)
            
        except Exception as e:
            print(f"[联动] focus_on_date 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_signals_display(self, signals):
        """更新信号标记显示"""
        try:
            chart = self._chart
            if not hasattr(chart, '_datetimes'):
                return
            
            datetimes = chart._datetimes
            dt_to_idx = {dt: i for i, dt in enumerate(datetimes)}
            
            # 找到买入/卖出信号索引
            buy_indices = set()
            for sig_dt in signals.get('buy', []):
                if sig_dt in dt_to_idx:
                    buy_indices.add(dt_to_idx[sig_dt])
            
            sell_indices = set()
            for sig_dt in signals.get('sell', []):
                if sig_dt in dt_to_idx:
                    sell_indices.add(dt_to_idx[sig_dt])
            
            print(f"[联动] 更新信号标记: 买入={len(buy_indices)}, 卖出={len(sell_indices)}")
            
            # 更新图表的信号集合
            if hasattr(chart, '_buy_triggers'):
                chart._buy_triggers = buy_indices
            if hasattr(chart, '_sell_triggers'):
                chart._sell_triggers = sell_indices
            
            # 触发重绘
            if hasattr(chart, '_redraw'):
                chart._redraw()
            
        except Exception as e:
            print(f"[联动] 更新信号显示失败: {e}")
            import traceback
            traceback.print_exc()
'''

# 组合新内容
new_content = before + insert_marker + before_method_end + new_methods + '\n' + after_method_end

# 修改 _on_fullscreen 方法以传递联动上下文
# 查找 _on_fullscreen 方法
if 'def _on_fullscreen(self) -> None:' in new_content:
    # 替换全屏窗口创建部分，添加联动参数
    old_fullscreen = '''win = _KlineFullscreenWindow(
            bars=self._chart._bars,
            dates=self._chart._dates,
            volumes=self._chart._volumes,
            buy_triggers=self._chart._buy_triggers,
            sell_triggers=self._chart._sell_triggers,
            ma_flags=self._get_ma_config(),
            show_triggers=self._trig_chk.isChecked(),
            show_candles=self._candle_chk.isChecked(),
            title=self._current_symbol,
            datetimes=getattr(self._chart, '_datetimes', None),
            waveform_snapshots=self._waveform_snapshots,
            waveform_dates=self._waveform_dates,
            waveform_buy_indices=getattr(self, '_waveform_buy_indices', []),
            waveform_sell_indices=getattr(self, '_waveform_sell_indices', []),
            parent=self,
        )'''
    
    new_fullscreen = '''# 获取联动上下文
        parent_monitor = None
        window_type = 'unknown'
        if hasattr(self, '_owner_panel'):
            panel = self._owner_panel
            if hasattr(panel, '_parent_monitor'):
                parent_monitor = panel._parent_monitor
            if hasattr(panel, '_panel_type'):
                window_type = panel._panel_type
        
        win = _KlineFullscreenWindow(
            bars=self._chart._bars,
            dates=self._chart._dates,
            volumes=self._chart._volumes,
            buy_triggers=self._chart._buy_triggers,
            sell_triggers=self._chart._sell_triggers,
            ma_flags=self._get_ma_config(),
            show_triggers=self._trig_chk.isChecked(),
            show_candles=self._candle_chk.isChecked(),
            title=self._current_symbol,
            datetimes=getattr(self._chart, '_datetimes', None),
            waveform_snapshots=self._waveform_snapshots,
            waveform_dates=self._waveform_dates,
            waveform_buy_indices=getattr(self, '_waveform_buy_indices', []),
            waveform_sell_indices=getattr(self, '_waveform_sell_indices', []),
            parent=self,
            parent_monitor=parent_monitor,
            window_type=window_type,
        )'''
    
    new_content = new_content.replace(old_fullscreen, new_fullscreen)

# 修改 _KlineFullscreenWindow __init__ 方法，添加联动参数
old_init_sig = '''def __init__(self, bars: list, dates: list, volumes: list,
                 buy_triggers: set, sell_triggers: set,
                 ma_flags: list, show_triggers: bool,
                 show_candles: bool = True,
                 title: str = "", datetimes: list = None,
                 waveform_snapshots: list = None,
                 waveform_dates: list = None,
                 waveform_buy_indices: list = None,
                 waveform_sell_indices: list = None,
                 parent=None):'''

new_init_sig = '''def __init__(self, bars: list, dates: list, volumes: list,
                 buy_triggers: set, sell_triggers: set,
                 ma_flags: list, show_triggers: bool,
                 show_candles: bool = True,
                 title: str = "", datetimes: list = None,
                 waveform_snapshots: list = None,
                 waveform_dates: list = None,
                 waveform_buy_indices: list = None,
                 waveform_sell_indices: list = None,
                 parent=None,
                 parent_monitor=None,
                 window_type='unknown'):'''

if old_init_sig in new_content:
    new_content = new_content.replace(old_init_sig, new_init_sig)
    
    # 在 __init__ 方法中保存联动上下文
    init_super = 'super().__init__(parent, QtCore.Qt.WindowType.Window)'
    if init_super in new_content:
        new_content = new_content.replace(
            init_super,
            init_super + '\n        self._parent_monitor = parent_monitor\n        self._window_type = window_type'
        )

# 在 _KlineFullscreenWindow 的 _setup_widgets 或类似方法末尾添加联动连接
# 查找连接信号的位置（在 _setup_widgets 方法内）
setup_marker = '        self._trig_chk.stateChanged.connect(self._on_ma_toggle)'
if setup_marker in new_content:
    link_code = '''
        
        # 连接日线点击信号（如果是分钟全屏窗口）
        if parent_monitor and window_type == 'minute':
            if hasattr(parent_monitor, 'daily_bar_clicked'):
                parent_monitor.daily_bar_clicked.connect(
                    self._on_daily_clicked_from_main)
                print(f"[联动] 分钟全屏窗口已连接日线点击信号")'''
    
    new_content = new_content.replace(setup_marker, setup_marker + link_code)

# 在 _KlineFullscreenWindow 类末尾添加联动处理方法
# 查找类结束位置（在最后一个方法之后）
class_end_marker = 'class _KlineFullscreenWindow'
if class_end_marker in new_content:
    # 找到该类的最后
    parts = new_content.split(class_end_marker)
    if len(parts) >= 2:
        before_class = parts[0] + class_end_marker + parts[1].split('\n\nclass ')[0]
        after_class = '\n\nclass ' + '\n\nclass '.join(parts[1].split('\n\nclass ')[1:]) if '\n\nclass ' in parts[1] else ''
        
        link_methods = '''

    def _on_daily_clicked_from_main(self, clicked_dt, signals):
        """响应主界面的日线点击（分钟全屏窗口）"""
        try:
            clicked_date = clicked_dt.date()
            print(f"[联动] 分钟全屏窗口收到日线点击: {clicked_date}")
            
            if hasattr(self, '_chart'):
                self._focus_chart_on_date(clicked_date, signals)
        except Exception as e:
            print(f"[联动] 分钟全屏窗口处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _focus_chart_on_date(self, target_date, signals):
        """全屏图表聚焦到指定日期"""
        try:
            chart = self._chart
            if not hasattr(chart, '_datetimes'):
                return
            
            datetimes = chart._datetimes
            if not datetimes:
                return
            
            # 找到目标日期的索引范围
            target_indices = [
                i for i, dt in enumerate(datetimes)
                if dt.date() == target_date
            ]
            
            if not target_indices:
                print(f"[联动] 全屏窗口未找到日期 {target_date}")
                return
            
            start_idx = min(target_indices)
            end_idx = max(target_indices)
            
            # 设置显示范围
            padding = 5
            x_min = max(0, start_idx - padding)
            x_max = min(len(datetimes) - 1, end_idx + padding)
            
            if hasattr(chart, '_main_plot'):
                chart._main_plot.setXRange(x_min, x_max, padding=0.02)
                print(f"[联动] 全屏窗口已聚焦到 {target_date}")
            
            # 更新信号标记
            if signals:
                self._update_fullscreen_signals(signals, datetimes)
        except Exception as e:
            print(f"[联动] 全屏图表聚焦失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_fullscreen_signals(self, signals, datetimes):
        """更新全屏窗口的信号标记"""
        try:
            chart = self._chart
            dt_to_idx = {dt: i for i, dt in enumerate(datetimes)}
            
            buy_indices = set()
            for sig_dt in signals.get('buy', []):
                if sig_dt in dt_to_idx:
                    buy_indices.add(dt_to_idx[sig_dt])
            
            sell_indices = set()
            for sig_dt in signals.get('sell', []):
                if sig_dt in dt_to_idx:
                    sell_indices.add(dt_to_idx[sig_dt])
            
            if hasattr(chart, '_buy_triggers'):
                chart._buy_triggers = buy_indices
            if hasattr(chart, '_sell_triggers'):
                chart._sell_triggers = sell_indices
            
            print(f"[联动] 全屏窗口更新信号: 买入={len(buy_indices)}, 卖出={len(sell_indices)}")
            
            # 重绘
            if hasattr(chart, '_redraw'):
                chart._redraw()
        except Exception as e:
            print(f"[联动] 更新全屏信号失败: {e}")
            import traceback
            traceback.print_exc()
'''
        
        new_content = before_class + link_methods + after_class

# 写回文件
with open(kline_view_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✓ 补丁应用成功")
print("\n修改内容：")
print("1. KlineViewTab 添加 focus_on_date() 方法")
print("2. KlineViewTab 添加 _update_signals_display() 方法")
print("3. _on_fullscreen() 传递联动上下文")
print("4. _KlineFullscreenWindow 支持联动参数")
print("5. _KlineFullscreenWindow 添加联动处理方法")
print("\n=" * 60)
print("日线分钟K线联动功能已完成")
print("=" * 60)