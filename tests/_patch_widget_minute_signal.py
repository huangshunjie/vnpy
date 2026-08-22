# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("vnpy/strategy_condition/ui/widget.py")
content = p.read_text(encoding="utf-8")

old = '''            self._monitor_tab = ConditionMonitorWidget()
            self._monitor_tab.lifecycle_info_changed.connect(
                self._on_lifecycle_info)
            self._tab.addTab(self._monitor_tab, "\U0001f50d  条件监控  Monitor")'''

new = '''            self._monitor_tab = ConditionMonitorWidget()
            self._monitor_tab.lifecycle_info_changed.connect(
                self._on_lifecycle_info)
            # Monitor 分钟周期下拉变化时，自动用当前 symbol 重新拉双周期数据
            self._monitor_tab.minute_interval_changed.connect(
                self._on_monitor_minute_interval_changed)
            self._tab.addTab(self._monitor_tab, "\U0001f50d  条件监控  Monitor")'''

if old not in content:
    print("[ERR] old not found")
    raise SystemExit(1)

if "minute_interval_changed.connect" in content:
    print("[OK] already connected")
else:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    print(f"[OK] patched, {len(content)} bytes")
