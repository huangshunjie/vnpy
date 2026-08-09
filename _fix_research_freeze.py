# -*- coding: utf-8 -*-
"""
修复研究100%后卡死的问题：
1. _display_results 限制显示行数 + 禁用表格排序/更新
2. _generate_monitor_data 改为延迟异步执行
"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\behavior_tab.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ─── 修复1：优化 _display_results，限制显示行数并使用 blockSignals ───
old_display = '''    def _display_results(self, events, periods):

        """Display research results"""

        import numpy as np



        self._results_table.setRowCount(0)

        self._events_count_lbl.setText(f"事件数: {len(events)}")

        symbols_set = set(e.get("symbol", "") for e in events)

        self._symbols_count_lbl.setText(f"标的数: {len(symbols_set)}")

        self._results_table.setRowCount(len(events))'''

new_display = '''    def _display_results(self, events, periods):

        """Display research results（优化：限制显示行数避免卡死）"""

        import numpy as np

        MAX_DISPLAY_ROWS = 500

        self._results_table.setRowCount(0)

        self._events_count_lbl.setText(f"事件数: {len(events)}")

        symbols_set = set(e.get("symbol", "") for e in events)

        self._symbols_count_lbl.setText(f"标的数: {len(symbols_set)}")

        display_events = events[:MAX_DISPLAY_ROWS]
        self._results_table.setSortingEnabled(False)
        self._results_table.blockSignals(True)
        self._results_table.setRowCount(len(display_events))'''

if old_display in content:
    content = content.replace(old_display, new_display)
    print("[OK] Fix 1: _display_results header optimized")
else:
    print("[FAIL] Fix 1: pattern not found")

# 修复 _display_results 中的循环变量（events -> display_events）
old_loop = '''        for row, evt in enumerate(events):'''
new_loop = '''        for row, evt in enumerate(display_events):'''

if old_loop in content:
    content = content.replace(old_loop, new_loop, 1)
    print("[OK] Fix 1b: loop variable fixed")

# 在 _display_results 的 self._tab.setCurrentIndex(1) 之前添加恢复表格信号
old_tab_switch = '''        self._tab.setCurrentIndex(1)'''
new_tab_switch = '''        self._results_table.blockSignals(False)
        self._results_table.setSortingEnabled(True)
        if len(events) > MAX_DISPLAY_ROWS:
            self._events_count_lbl.setText(f"事件数: {len(events)} (显示前{MAX_DISPLAY_ROWS}条)")
        self._tab.setCurrentIndex(1)'''

if old_tab_switch in content:
    content = content.replace(old_tab_switch, new_tab_switch, 1)
    print("[OK] Fix 1c: table signals restored")

# ─── 修复2：_generate_monitor_data 改为延迟异步执行 ───
old_monitor_call = '''            self._generate_monitor_data(symbols, condition_expr)'''
new_monitor_call = '''            # 延迟100ms后异步生成监控数据，避免100%后卡死
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._generate_monitor_data(symbols[:10], condition_expr))'''

if old_monitor_call in content:
    content = content.replace(old_monitor_call, new_monitor_call)
    print("[OK] Fix 2: _generate_monitor_data deferred")
else:
    print("[FAIL] Fix 2: pattern not found")

# ─── 修复3：_generate_monitor_data 中添加 processEvents 防卡 ───
old_monitor_loop = '''            for sym_full in symbols[:10]:'''
new_monitor_loop = '''            for _mi, sym_full in enumerate(symbols[:10]):
                if _mi % 2 == 0:
                    QApplication.processEvents()'''

if old_monitor_loop in content:
    content = content.replace(old_monitor_loop, new_monitor_loop)
    print("[OK] Fix 3: monitor loop processEvents added")
else:
    print("[FAIL] Fix 3: pattern not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nAll done!")
