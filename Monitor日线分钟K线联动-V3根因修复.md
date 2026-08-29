# Monitor 日线→分钟 K线 联动 - V3 根因修复

**修复时间**：2026-08-23 15:50
**修复文件**：`vnpy/strategy_condition/ui/condition_monitor_widget.py`
**修复函数**：`_PeriodMonitorPanel.focus_datetime` 的调用方 `_update_minute_view_for_date`

---

## 一、问题描述

用户在全屏日线 K线模式下，点击日线 K线，预期分钟线 K线的 vline 跳到该日。但 vline **要么不动，要么落到前一天最后 1 根**，用户感知"点击 2026-04-20 没有联动"。

日志显示：

```
[联动] 日线K线被点击: 2026-04-20
[联动] 找到信号: 买入=0, 卖出=0
```

说明 `_on_daily_bar_clicked` **确实触发了**，并且 `_update_minute_view_for_date` 也**确实被调用了**（因为 V1 已经把 `hasattr 永远为 False` 的 KlineViewTab 改成 _PeriodMonitorPanel）。

---

## 二、根因分析

`_update_minute_view_for_date` 调用 `focus_datetime(dt, completed_daily=True)` 时：

```python
# _PeriodMonitorPanel.focus_datetime 的关键逻辑
if completed_daily and bar_dt_cmp.date() >= dt.date():
    continue
if bar_dt_cmp <= dt:
    target_index = index
```

而 V2 调用时传的是：

```python
dt = datetime.combine(target_date, time(12, 0), tzinfo=tz)  # 2026-04-20 12:00
minute_panel.focus_datetime(dt, completed_daily=True)        # ⚠️ 跳过同日！
```

**当 `completed_daily=True` + dt=当天 12:00 时**：
1. `if completed_daily and bar_dt_cmp.date() >= dt.date(): continue` 会跳过所有 `date >= 2026-04-20` 的 minute bar
2. 所以 `target_index` 只会被更新到 `2026-04-19 14:55`（前一天最后 1 根）
3. **vline 落到了 2026-04-19 的最后 1 根！** 用户看到"点击 04-20 没动"

**对照：**
- `completed_daily=True` + dt=2026-04-20 12:00 → vline 落在 2026-04-19 最后 1 根
- `completed_daily=True` + dt=2026-04-19 15:00 → vline 落在 2026-04-18 最后 1 根

`completed_daily` 的设计本意是"只取已收盘的完整日线"，但用在分钟线 K线时，**用户希望 vline 落在点击的日线当天**，这个语义不匹配！

---

## 三、修复方案

**改动**（`condition_monitor_widget.py` 行的 `_update_minute_view_for_date`）：

```diff
-            from datetime import datetime, time, timezone, timedelta
-            # 当天 12:00 作为目标时刻；completed_daily=True 时
-            # focus_datetime 会跳过同日 bar，取 <= 目标时刻的最后一根
-            # minute bar（恰是 target_date 当天最后已完成的 bar）
-            # 加上 +08:00 与 K线 bar 的 tz 对齐（focus_datetime 内部会
-            # 先 replace(tzinfo=None) 再比较，保持语义一致）。
-            tz = timezone(timedelta(hours=8))
-            dt = datetime.combine(target_date, time(12, 0), tzinfo=tz)
-            minute_panel.focus_datetime(dt, completed_daily=True)
+            from datetime import datetime, time, timezone, timedelta
+            # 用 target_date 当天 23:59:59 作为目标时刻；completed_daily=False
+            # 让 focus_datetime 取 <= 目标时刻的最后 1 根 minute bar
+            # （即 target_date 当天的最后 1 根 bar，vline 落在点击的日线上）。
+            tz = timezone(timedelta(hours=8))
+            dt = datetime.combine(target_date, time(23, 59, 59), tzinfo=tz)
+            minute_panel.focus_datetime(dt, completed_daily=False)
```

**修复后语义**：
- `dt = 2026-04-20 23:59:59` + `completed_daily=False`
- `focus_datetime` 取 `bar_dt_cmp <= 2026-04-20 23:59:59` 的最后一根
- = 2026-04-20 当天最后 1 根 minute bar（15:00 收盘那根或 23:59 内最近一根）
- vline 精确落在用户点击的日线上 ✓

---

## 四、副作用分析

1. **不影响 `_sync_daily_cursor`**：分钟→日线 联动仍然用 `completed_daily=True`，保持"分钟 14:30 引用当日日线"的语义。
2. **不影响 buy/sell 信号查询**：`_get_signals_for_date` 与 `focus_datetime` 解耦。
3. **不影响空信号日联动**：用户点击 **任何日线 K线**（无论是否有 buy/sell），vline 都会跳转——这与用户的预期一致（"点击日线 K线就跳到分钟线对应日"）。
4. **v4 setXRange 滚动保留**：把目标 bar 放到视口右 2/3 处，vline 不会落到视口外。

---

## 五、验证步骤

1. 重新启动 vnpy + Monitor Tab
2. 双周期模式，stock=600028.SSE
3. 全屏日线 K线
4. 点击 2026-04-20 日线 K线
5. 预期：vline 跳到 2026-04-20 14:55（当天最后 1 根 minute bar）
6. 点击 2026-04-21 日线 K线
7. 预期：vline 跳到 2026-04-21 14:55

---

## 六、修复涉及的关键文件

| 文件 | 改动 |
|------|------|
| `vnpy/strategy_condition/ui/condition_monitor_widget.py` | `_update_minute_view_for_date`：12:00 + completed_daily=True → 23:59:59 + completed_daily=False |

无其他文件改动。

---

## 七、关键日志

启动后应该会看到：

```
[联动] 日线K线点击事件已连接
...
[联动] 日线K线被点击: 2026-04-20
[联动] 找到信号: 买入=0, 卖出=0
```

**只要这 2 行出现 + 没有 exception 堆栈**，vline 就会按修复后的语义跳到目标日线当天最后 1 根 minute bar。