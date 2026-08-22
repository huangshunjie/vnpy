# -*- coding: utf-8 -*-
content = open("vnpy/strategy_condition/ui/widget.py", encoding="utf-8").read()
checks = {
    "_feed_monitor 重写（含 minute_interval_key）":
        "minute_interval_key()" in content,
    "缓存键含 minute_key": "minute_key," in content,
    "缓存值 4-tuple 解构": "minute_snapshots, minute_bars) = cached" in content,
    "调用 load_layered_data": "load_layered_data(" in content,
    "_load_minute_bars_for_monitor 方法存在":
        "def _load_minute_bars_for_monitor" in content,
    "_minute_key_to_interval 方法存在":
        "def _minute_key_to_interval" in content,
    "_on_monitor_minute_interval_changed 方法存在":
        "def _on_monitor_minute_interval_changed" in content,
    "minute_interval_changed 信号已 connect":
        "minute_interval_changed.connect" in content,
    "fallback 降级（load_snapshots 兜底）":
        "if daily_bars and daily_snapshots" in content,
}
ok = 0
for k, v in checks.items():
    print("  [OK]" if v else "  [MISS]", k)
    ok += 1 if v else 0
print(f"  ==> {ok}/{len(checks)} 通过")
print()
# 同样检查 condition_monitor_widget.py
content2 = open("vnpy/strategy_condition/ui/condition_monitor_widget.py",
                encoding="utf-8").read()
checks2 = {
    "load_layered_data 接受 minute_snapshots=None":
        "minute_snapshots: List[ConditionSnapshot] = None" in content2,
    "_build_minute_snapshots_fallback 方法存在":
        "def _build_minute_snapshots_fallback" in content2,
    "load_snapshots 容忍 snapshots 为空":
        "(snapshots or [])" in content2,
    "_on_minute_interval_changed 方法存在":
        "def _on_minute_interval_changed" in content2,
    "minute_interval_changed 信号监听 self":
        "self.minute_interval_changed.connect(\n            self._on_minute_interval_changed)" in content2,
}
ok2 = 0
for k, v in checks2.items():
    print("  [OK]" if v else "  [MISS]", k)
    ok2 += 1 if v else 0
print(f"  ==> {ok2}/{len(checks2)} 通过")
