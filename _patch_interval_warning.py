# -*- coding: utf-8 -*-
from pathlib import Path

path = Path(r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\ui\widget.py')
text = path.read_text(encoding='utf-8')
old = '        self._strategy.params = self._collect_params()\n'
new = '        self._strategy.params = self._collect_params()\n        for warning in self._strategy.validate_interval_scopes():\n            self._show_msg(warning)\n'
text = text.replace(old, new, 2)
path.write_text(text, encoding='utf-8')
print('patched scan/backtest warnings')