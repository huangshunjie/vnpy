lines = open('vnpy/strategy_condition/ui/kline_view.py', 'r', encoding='utf-8').readlines()
in_fullscreen = False
for i, line in enumerate(lines, 1):
    if 'class _FullscreenChart' in line:
        in_fullscreen = True
        print(f'Line {i}: Found _FullscreenChart class')
    if in_fullscreen and 'def _on_measure_toggle' in line:
        print(f'\nLine {i}: _on_measure_toggle in _FullscreenChart')
        print('Next 60 lines:')
        for j in range(60):
            if i+j-1 < len(lines):
                print(f'  {i+j}: {lines[i+j-1].rstrip()}')
        break