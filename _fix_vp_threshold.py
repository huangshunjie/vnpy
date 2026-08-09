# -*- coding: utf-8 -*-
"""修复量价特征默认阈值：vp_开头的布尔型特征应为 > 0.0，而非 > 1.5"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\behavior_tab.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换量价类默认阈值逻辑
old = '''        elif ft == KLineFeatureType.VOLUME:\n\n            return (">", 1.5)  # \u91cf\u4ef7\u7c7b\u9ed8\u8ba4\u653e\u91cf'''

new = '''        elif ft == KLineFeatureType.VOLUME:\n            if name.startswith("vp_"):\n                return (">", 0.0)  # vp_\u524d\u7f00\u5e03\u5c14\u578b\u91cf\u4ef7\u5f62\u6001\uff0c\u8fd4\u56de0/1\n            return (">", 1.5)  # \u91cf\u6bd4\u7c7b\u8fde\u7eed\u503c\u7279\u5f81'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - fixed via exact pattern')
else:
    print('Exact pattern not found, trying line-by-line fix')
    lines = content.split('\n')
    fixed = False
    for i, line in enumerate(lines):
        if 'KLineFeatureType.VOLUME' in line and 'elif' in line:
            # 找到这行，下面几行应该是 return (">", 1.5)
            for j in range(i+1, min(i+5, len(lines))):
                if 'return (">", 1.5)' in lines[j]:
                    indent = '            '
                    # 在 return 前插入 vp_ 前缀检查
                    lines[j] = (indent + 'if name.startswith("vp_"):\n' +
                                indent + '    return (">", 0.0)  # vp_\u524d\u7f00\u5e03\u5c14\u578b\u91cf\u4ef7\u5f62\u6001\n' +
                                lines[j].rstrip() + '  # \u91cf\u6bd4\u7c7b\u8fde\u7eed\u503c\u7279\u5f81')
                    fixed = True
                    print(f'OK - fixed at line {j+1}')
                    break
            break
    
    if fixed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    else:
        print('FAIL - could not find pattern to fix')
