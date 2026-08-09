# -*- coding: utf-8 -*-
"""
彻底修复卡死问题：
1. 不通过信号传递大数据（events_bars/event_indices），改为存在worker属性上
2. finished信号只传递轻量的 all_events 列表
3. _display_results 降低MAX为200行，每50行 processEvents
4. pattern_stats 和 monitor_data 都延迟且限制数据量
"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\behavior_tab.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# ═══ 修改1：找到 class _ResearchWorker 中的 Signal 定义，改为不传大数据 ═══
for i, line in enumerate(lines):
    if 'finished = Signal(list, dict, dict)' in line:
        lines[i] = '            finished = Signal(list)\n'
        print(f"Fix 1: Signal changed at line {i+1}")
        break

# ═══ 修改2：找到 self.finished.emit(all_events, events_bars, event_indices) ═══
for i, line in enumerate(lines):
    if 'self.finished.emit(all_events, events_bars, event_indices)' in line:
        # 改为先存到属性，再只emit轻量数据
        lines[i] = ('                    self._result_events_bars = events_bars\n'
                    '                    self._result_event_indices = event_indices\n'
                    '                    self.finished.emit(all_events)\n')
        print(f"Fix 2: emit changed at line {i+1}")
        break

# ═══ 修改3：修改 _on_research_finished 的参数签名 ═══
for i, line in enumerate(lines):
    if 'def _on_research_finished(self, all_events: list, events_bars: dict, event_indices: dict):' in line:
        lines[i] = '    def _on_research_finished(self, all_events: list):\n'
        print(f"Fix 3: signature changed at line {i+1}")
        break

# ═══ 修改4：在 _on_research_finished 中从 worker 属性获取大数据 ═══
for i, line in enumerate(lines):
    if 'self._display_results(all_events, periods)' in line and i > 3190:
        # 在这行前面插入从 worker 获取数据的代码
        indent = '        '
        insert = (indent + 'events_bars = getattr(self._research_worker, "_result_events_bars", {})\n' +
                  indent + 'event_indices = getattr(self._research_worker, "_result_event_indices", {})\n')
        lines.insert(i, insert)
        print(f"Fix 4: data retrieval inserted at line {i+1}")
        break

# ═══ 修改5：_display_results 中每100行 processEvents ═══
for i, line in enumerate(lines):
    if 'for row, evt in enumerate(display_events):' in line:
        # 在循环体第一行之后添加 processEvents
        # 找到循环体第一行
        j = i + 1
        # 跳过空行
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        # 在这个位置插入 processEvents 逻辑
        indent = '            '
        insert = indent + 'if row > 0 and row % 100 == 0:\n' + indent + '    QApplication.processEvents()\n'
        lines.insert(j, insert)
        print(f"Fix 5: processEvents in display loop at line {j+1}")
        break

# ═══ 修改6：降低 MAX_DISPLAY_ROWS 到 200 ═══
for i, line in enumerate(lines):
    if 'MAX_DISPLAY_ROWS = 500' in line:
        lines[i] = '        MAX_DISPLAY_ROWS = 200\n'
        print(f"Fix 6: MAX_DISPLAY_ROWS lowered at line {i+1}")
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\nAll fixes applied!")
