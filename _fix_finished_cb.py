# -*- coding: utf-8 -*-
"""修复 _on_research_finished 中的阻塞操作"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\behavior_tab.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    def _on_research_finished(self, all_events: list, events_bars: dict, event_indices: dict):
        """子线程完成回调（在主线程执行）"""
        periods = self._research_periods
        symbols = self._research_symbols
        condition_expr = self._research_condition_expr

        self._display_results(all_events, periods)

        # 更新形态统计 tab（延迟执行避免卡顿）
        if events_bars and event_indices:
            try:
                self._pattern_stats_tab.update_stats(events_bars, event_indices)
            except Exception as e:
                print(f"[BehaviorLab] 形态统计更新异常: {e}")

        # 延迟生成监控数据
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._generate_monitor_data(symbols[:10], condition_expr))'''

new = '''    def _on_research_finished(self, all_events: list, events_bars: dict, event_indices: dict):
        """子线程完成回调（在主线程执行）"""
        periods = self._research_periods
        symbols = self._research_symbols
        condition_expr = self._research_condition_expr

        self._display_results(all_events, periods)
        QApplication.processEvents()

        # 更新形态统计 tab（限制数据量 + 延迟执行避免卡顿）
        from PySide6.QtCore import QTimer
        if events_bars and event_indices:
            limited_bars = dict(list(events_bars.items())[:20])
            limited_indices = {k: event_indices[k] for k in limited_bars if k in event_indices}
            def _do_pattern_stats():
                try:
                    self._pattern_stats_tab.update_stats(limited_bars, limited_indices)
                except Exception:
                    pass
            QTimer.singleShot(500, _do_pattern_stats)

        # 延迟生成监控数据
        QTimer.singleShot(1000, lambda: self._generate_monitor_data(symbols[:10], condition_expr))'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - fixed _on_research_finished')
else:
    print('FAIL - pattern not found, trying alternate approach')
    # 逐行查找
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'def _on_research_finished' in line:
            print(f'Found at line {i+1}')
            print(f'Context: {lines[i:i+20]}')
            break
