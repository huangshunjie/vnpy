# -*- coding: utf-8 -*-
import py_compile, sys
errs = []
for f in ['vnpy/strategy_condition/ui/widget.py',
          'vnpy/strategy_condition/ui/condition_monitor_widget.py',
          'vnpy/strategy_condition/ui/kline_view.py']:
    try:
        py_compile.compile(f, doraise=True)
        print(f, 'OK')
    except Exception as e:
        errs.append((f, str(e)))
        print(f, 'FAIL', e)
sys.exit(1 if errs else 0)
