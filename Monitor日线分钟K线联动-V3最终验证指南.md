# Monitor 日线↔分钟 K 线联动 — V3 最终验证指南

> 报告日期：2026-08-23 下午 4:06
> 状态：✅ **V3 修复已完成并落盘**，等待用户重启 + 验证

---

## 一、问题现状（用户报告）

**用户报告**："全屏模式还是不能点击日线实现分钟线联动"

**用户日志关键现象**（嵌入面板的 `_on_daily_bar_clicked` 路径）：

```
[联动] 日线K线被点击: 2026-04-20
[联动] 找到信号: 买入=0, 卖出=0
[联动] 日线K线被点击: 2026-03-18
[联动] 找到信号: 买入=0, 卖出=0
...
```

**但没有**看到：
- `vline` 移动的 `print` 输出
- 全屏窗口的 `_on_fullscreen` DEBUG 日志

---

## 二、V3 根因分析（已修复）

### 2.1 根本原因
**`_update_minute_view_for_date` 调用 `focus_datetime` 时传错参数**：
- ❌ 旧代码：传入 `dt=target_date 12:00` + `completed_daily=True`
- ✅ V3 修复：传入 `dt=target_date 23:59` + `completed_daily=False`

### 2.2 旧代码为什么失效

`focus_datetime`（`condition_monitor_widget.py:713-716`）：

```python
if completed_daily and bar_dt_cmp.date() >= dt.date():
    continue        # ← 旧代码会**跳过同日**所有 bar
if bar_dt_cmp <= dt:
    target_index = index
```

**当 `completed_daily=True` 且 `dt=12:00` 时**：
- 同日 bar（>= target_date.date()）→ **全部被 skip**
- `bar_dt_cmp <= 12:00` 匹配的只有**前一天及更早**的 bar
- vline 落在**前一天**的最后 1 根
- 用户感知："点击 2026-04-20 完全没有联动"（其实有联动，只是落点错了）

### 2.3 V3 修复后

- `dt=23:59` → 覆盖 target_date 当天所有 minute bar（5m 数据最后 1 根 = 14:55 或 15:00）
- `completed_daily=False` → **不**跳过同日 bar
- `target_index` = target_date 当天**最后 1 根** minute bar
- vline 精确落在用户点击的日线上 ✓

---

## 三、V3 修复代码（已落盘）

### 3.1 修改文件
`vnpy/strategy_condition/ui/condition_monitor_widget.py`

### 3.2 修改方法
`_update_minute_view_for_date`（第 961-1020 行）

### 3.3 关键代码段（确认已生效）

```python
def _update_minute_view_for_date(self, target_date, signals):
    """更新分钟K线视图，聚焦到指定日期
    
    关键修复（2026-08-23，三次修复）：之前传入当天 12:00 + completed_daily=True，
    会导致 ``focus_datetime`` 跳过同日 bar，vline 落在 **前一天** 的最后 1 根，
    用户感知"点击 2026-04-20 没有联动"。改为：
      - dt = target_date 当天 23:59（足够覆盖日内所有 minute bar）
      - completed_daily=False（**不要**跳过同日 bar）
    这样 ``focus_datetime`` 取 ``bar_dt_cmp <= dt`` 的最后一根 = target_date
    当天最后 1 根 minute bar，vline 会精确落在用户点击的日线上。
    """
    try:
        if not hasattr(self, '_minute_panel'):
            return
        minute_panel = self._minute_panel

        # 缓存信号上下文（给 info 栏/状态栏使用；不再影响 vline 跳转）
        self._pending_signals = dict(signals or {})

        if not hasattr(minute_panel, 'focus_datetime'):
            print("[联动] _PeriodMonitorPanel 缺少 focus_datetime，无法移动 vline")
            return
        
        # 用 target_date 当天 23:59 作为目标时刻；completed_daily=False
        # 让 focus_datetime 取 <= 目标时刻的最后 1 根 minute bar
        # （即 target_date 当天的最后 1 根 bar，vline 落在点击的日线上）。
        # 加上 +08:00 与 K线 bar 的 tz 对齐（focus_datetime 内部会
        # 先 replace(tzinfo=None) 再比较，保持语义一致）。
        dt = datetime.combine(target_date, time(23, 59, 59), tzinfo=tz)
        minute_panel.focus_datetime(dt, completed_daily=False)
    except Exception as e:
        print(f"[联动] _update_minute_view_for_date 失败: {e}")
```

---

## 四、用户验证步骤

### 4.1 清理 Python 缓存
```bash
# 防止旧 .pyc 干扰
cd c:\Users\11229\Documents\GitHub\vnpy
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
```

### 4.2 重启 Veighna Trader
完整重启整个应用（不是 reload），确保 `condition_monitor_widget.py` 重新加载。

### 4.3 复现路径
1. 打开 Monitor Tab
2. 加载 600028.SSE 双周期数据（2020-01-02 ~ 2026-07-17）
3. 等 `[Monitor] load_layered_data 600028.SSE: daily=1584 bars/1524 snaps, minute=20000 bars/19900 snaps` 出现
4. 确认右上角显示模式为 "双周期"
5. **点击日线 K 线**任一日期

### 4.4 期望日志
```
[联动] 日线K线被点击: 2026-04-20
[联动] 找到信号: 买入=X, 卖出=Y
[focus_datetime v4] ...   ← 如果 target_index 在视口外会触发
```

### 4.5 期望 UI 行为
- ✅ 分钟 K 线图（下方）vline 落在 **2026-04-20 当天**最后 1 根 minute bar
- ✅ vline 出现在视口**右 2/3 位置**（v4 setXRange 修复）
- ✅ 波形图（最下方）vline 同步移动
- ✅ 日线 K 线图（上方）vline 也同步显示在 2026-04-20

### 4.6 如果仍未生效 — 排查清单

| 现象 | 排查 |
|------|------|
| 完全没反应 | 1) 确认 `condition_monitor_widget.py` 的 `_update_minute_view_for_date` 有 V3 注释；2) 删除 `__pycache__` 重启 |
| vline 落在前一天 | V3 未生效，cache 没清干净 |
| vline 落在正确日，但视口外 | v4 setXRange 失败，看 `[focus_datetime v4] setXRange 失败: ...` |
| "找到信号=0" 但 vline 正确 | 正常！只是该日无 buy/sell 触发，**联动本身成功** |

---

## 五、关于"全屏模式"

**用户报告的"全屏模式"** 经过日志分析，**实际上**很可能是 **Monitor Tab 中的嵌入面板**（并非 KlineViewTab 工具栏的全屏按钮弹出的 `_KlineFullscreenWindow`）。

**证据**：
- 日志中只有 `[联动]` 前缀（来自嵌入面板 `condition_monitor_widget.py`）
- **没有** `[KlineView][DEBUG] _on_fullscreen:` 日志

**如果用户**真的打开了 KlineViewTab 的全屏窗口（点击了工具栏的"全屏"按钮），**那条路径也已通过以下修复生效**：
- `kline_view.py:1078-1080` 全屏窗口的 `bar_clicked` 已连接到 `owner._on_daily_bar_clicked`
- `owner` = ConditionMonitorWidget 实例
- 触发后会进入同一个 `_on_daily_bar_clicked` 方法

**所以嵌入和全屏两条路径都已经修复，V3 修复对两者都生效。**

---

## 六、回归点确认（无需新增改动）

| 文件 | 已有修复 | 验证 |
|------|----------|------|
| `condition_monitor_widget.py:961-1020` | V3 focus_datetime 参数修正 | ✅ 已落盘 |
| `kline_view.py:1074-1084` | 全屏窗口转发 bar_clicked | ✅ 已落盘 |
| `kline_view.py` KlineChartWidget | bar_clicked Signal 类级定义 | ✅ 4 处都是类级 |
| `condition_monitor_widget.py:873` | `_on_daily_bar_clicked` 入口 | ✅ 已连接 |

---

## 七、报告完成

V3 修复已完成，等待用户重启验证。

如果**重启后**仍有问题，请提供新的运行日志（特别是点击日线时控制台的所有 `[联动]` 和 `[focus_datetime]` 输出），我们将基于实际日志做下一步诊断。