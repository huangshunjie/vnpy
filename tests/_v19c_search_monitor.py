# -*- coding: utf-8 -*-
"""V19-c: 直接搜索 condition_monitor_widget.py 中的关键 print 和方法"""
import io
import sys

# 强制 stdout UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = 'vnpy/strategy_condition/ui/condition_monitor_widget.py'
data = io.open(path, 'r', encoding='utf-8').read()
print(f"=== Searching in {path} (len={len(data)}) ===")
for i, line in enumerate(data.splitlines(), 1):
    if any(kw in line for kw in [
        '_on_daily_bar_clicked_from_outer',
        '_on_daily_bar_clicked',
        '日线K线被点击',
        '日线点击',
        'dispatch',
        '[联动]',
        '[联动V17]',
        '_on_bar_clicked',
        'bar_clicked',
    ]):
        print(f"{i:5d}: {line}")