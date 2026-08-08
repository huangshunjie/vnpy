"""诊断 KLineBehaviorLab 在应用中心是否能正确加载"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine
from importlib import import_module

ee = EventEngine()
me = MainEngine(ee)

from vnpy.kline_behavior_lab import KLineBehaviorLabApp
me.add_app(KLineBehaviorLabApp)

# 模拟 sidebar 的逻辑
app_funcs = {}
for app in me.get_all_apps():
    try:
        ui_mod = import_module(app.app_module + '.ui')
        wcls = getattr(ui_mod, app.widget_name)
        app_funcs[app.app_name] = (app.display_name, 'OK')
    except Exception as e:
        print(f'FAILED: {app.app_name} -> {e}', flush=True)

print(f'Total in app_funcs: {len(app_funcs)}', flush=True)
print(f'KLineBehaviorLab in app_funcs: {"KLineBehaviorLab" in app_funcs}', flush=True)
if 'KLineBehaviorLab' in app_funcs:
    print(f'  display_name: {app_funcs["KLineBehaviorLab"][0]}', flush=True)
else:
    print('  NOT FOUND - checking all_apps...', flush=True)
    for app in me.get_all_apps():
        print(f'    app_name={app.app_name}', flush=True)