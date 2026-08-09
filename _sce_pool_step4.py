# -*- coding: utf-8 -*-
"""微调 _on_pool_changed 逻辑：无股票池时显示数据源信息"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\ui\widget.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        n = len(self._get_pool_symbols())
        name = getattr(self, '_current_pool_name', '')
        if name:
            self._pool_count_lbl.setText(f"{name} - {n} \u53ea")
        else:
            self._pool_count_lbl.setText(f"{n} \u53ea")'''

new = '''        n = len(self._get_pool_symbols())
        name = getattr(self, '_current_pool_name', '')
        if name:
            self._pool_count_lbl.setText(f"{name} - {n} \u53ea")
        elif n > 0:
            self._pool_count_lbl.setText(f"\u6570\u636e\u6e90\uff1aVeighNa \u6570\u636e\u5e93 - {n} \u53ea")
        else:
            self._pool_count_lbl.setText("\u6570\u636e\u6e90\uff1aVeighNa \u6570\u636e\u5e93")'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - adjusted _on_pool_changed logic')
else:
    print('FAIL - pattern not found')
