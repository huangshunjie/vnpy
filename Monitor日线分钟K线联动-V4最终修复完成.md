# Monitor 日线↔分钟 K 线联动 - V4 最终修复完成

## 📋 任务背景

用户反馈：**全屏模式下点击日线 K 线后，分钟 K 线区域没有切换到对应日期**。  
之前 V3 修复未生效，因为：
- `_on_daily_bar_clicked_from_outer` 的 `focus_datetime` 时间是 `00:00:00`（日线数据天然如此）
- `_update_minute_view_for_date` 用 `date(target_date)` 过滤，但 5m 分钟线数据是 `09:30/10:00/...`
- 即使传入 00:00 也能正常过滤，所以 V3 那块理论上是 OK 的

**真正根因**（V4 才发现）：**`KlineViewTab._on_fullscreen` 创建全屏窗口时，  
没有把 owner_monitor 注入到 _KlineFullscreenWindow，**  
导致全屏的 `_FullscreenChart.bar_clicked` 找不到要调用的 monitor。

## 🎯 V4 修复方案

### 修复 1：`_KlineFullscreenWindow.__init__` 加 `self._owner_monitor = None` 属性
```python
self._owner_monitor = None  # V4: 转发日线点击用
```

### 修复 2：`KlineViewTab._on_fullscreen` 找 owner_monitor 并注入
```python
# V4 关键修复：owner_panel 可能是 _PeriodMonitorPanel 而非 ConditionMonitorWidget
# 需沿 _parent_monitor 链找到真正的 Monitor
outer = getattr(self, '_owner_panel', None)
owner_monitor = None
if outer is not None:
    if hasattr(outer, '_on_daily_bar_clicked_from_outer'):
        owner_monitor = outer  # outer 本身就是 Monitor
    elif getattr(outer, '_parent_monitor', None) is not None and \
            hasattr(outer._parent_monitor, '_on_daily_bar_clicked_from_outer'):
        owner_monitor = outer._parent_monitor  # 走 _PeriodMonitorPanel._parent_monitor
# 方案A：信号连接
win.bar_clicked.connect(owner_monitor._on_daily_bar_clicked_from_outer)
# 方案B：直接把 monitor 注入 _FullscreenChart._owner_monitor，绕过信号链
win._owner_monitor = owner_monitor
```

### 修复 3：`_FullscreenChart._on_mouse_clicked_for_link` 加"方案B" fallback
```python
# 方案B fallback: 通过 parent window 找 owner_monitor 直接调
par = self.parent()
while par is not None and not isinstance(par, _KlineFullscreenWindow):
    par = par.parent() if hasattr(par, 'parent') else None
if par is not None and getattr(par, '_owner_monitor', None) is not None:
    owner_monitor = par._owner_monitor
if owner_monitor is not None:
    # 日线 00:00 datetime 补成 23:59:59，避免 _update_minute_view_for_date 过滤掉
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        focus_dt = dt.replace(hour=23, minute=59, second=59)
    else:
        focus_dt = dt
    owner_monitor._on_daily_bar_clicked_from_outer(focus_dt, from_fullscreen=True)
```

## 📊 修改文件
- `vnpy/strategy_condition/ui/kline_view.py`
  - L? `_KlineFullscreenWindow.__init__`: 加 `self._owner_monitor = None`
  - L? `KlineViewTab._on_fullscreen`: 找 owner_monitor + 注入 + 双路径连接
  - L? `_FullscreenChart._on_mouse_clicked_for_link`: 加方案B fallback（双保险）

## ✅ 验证

| 检查项 | 结果 |
|--------|------|
| `python -X utf8 -c "import ast; ast.parse(...)"` | OK ✅ |
| owner_monitor 沿 `_parent_monitor` 链查找 | 实现 ✅ |
| 方案A 信号连接 + 方案B 直接调用双保险 | 实现 ✅ |
| 日线 00:00 → 23:59:59 补齐 | 实现 ✅ |

## 🧪 验证步骤（请运行）

1. 重启 vnpy（重要：清 pycache）
2. 打开 Monitor Tab
3. 点击日线 K 线上某根 bar
4. 验证：分钟 K 线区是否自动跳转到该日期？信号是否标记？
5. 点击"⛶"全屏按钮
6. 在全屏窗口里点击日线 K 线上的另一根 bar
7. 验证：全屏窗口下方（或主窗口）的分钟 K 线是否跳转到该日期？

预期日志：
```
[KlineView][DEBUG] _on_fullscreen: owner_panel=ConditionMonitorWidget, owner_monitor=ConditionMonitorWidget
[KlineView][DEBUG] 全屏窗口 owner_monitor 注入成功: <ConditionMonitorWidget ...>
[KlineView][DEBUG] 全屏K线被点击: x=NNN, dt=2026-03-18, 发射 bar_clicked
[KlineView][DEBUG] 方案B owner_monitor=ConditionMonitorWidget
[KlineView][DEBUG] 方案B 已直接调用 owner_monitor._on_daily_bar_clicked_from_outer, focus_dt=2026-03-18 23:59:59
[Monitor] 跳转到日线点击: 2026-03-18
```

## 🎉 完成度

- [x] V3 修复（focus_datetime 时间补齐）
- [x] V4 修复 1（_owner_monitor 属性）
- [x] V4 修复 2（_on_fullscreen 注入 owner_monitor）
- [x] V4 修复 3（_on_mouse_clicked_for_link 方案B fallback）
- [x] 语法检查通过
- [ ] **运行时验证**（待你测试）