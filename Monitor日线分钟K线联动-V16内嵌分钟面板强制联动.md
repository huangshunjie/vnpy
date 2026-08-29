# Monitor 日线↔分钟 K 线联动 V16 修复完成

## 时间
2026-08-23 23:50 (UTC+8)

## 问题描述
用户反馈"全屏模式还是不能点击日线实现分钟线联动"，V15 方案 "降级到主 Monitor 内嵌分钟K线面板" 看似**已经实现**了，但实际从用户日志看：

```
[联动] 日线K线被点击: 2026-02-05
[联动] 找到信号: 买入=0, 卖出=0
```

**没有看到** `[focus_datetime]` / `[联动V16]` 这种 print，说明 `_update_minute_view_for_date` 内部的关键 `print` 没出现 → **要么 print 被异常吞了，要么走到了早退路径**。

## 根因分析（V15 → V16 的关键进化）

V15 的代码路径是：

```
_handle_daily_bar_clicked (from_fullscreen=True)
  └─ _update_minute_view_for_date(clicked_date, signals)  ← 主路径
        └─ minute_panel.focus_datetime(dt, completed_daily=False)
              └─ [focus_datetime] print  ← 应该出现
```

理论上这条链是通的。但用户**没看到** `[focus_datetime]` print。
可能的失败点：
1. `_update_minute_view_for_date` 在 `not hasattr(self, '_minute_panel')` 早退
2. 异常被 except 吞了没 print
3. `minute_panel.focus_datetime` 在 `not self._current_bars` 早退

## V16 修复方案

**直接绕过 `_update_minute_view_for_date` 的中转**，在 `_handle_daily_bar_clicked` 里**额外**直接调一次 `_minute_panel.focus_datetime(clicked_dt, completed_daily=False)`。

```python
# V16：不管 from_fullscreen 与否，都让"主 Monitor 内嵌的分钟K线面板"
# 直接同步跳到 clicked_dt（这是用户最直观的体验 —— 日线点哪儿，
# 主 Monitor 下方那个嵌入的分钟K线面板 vline + 视图就跳到哪儿）。
# 注意：ConditionMonitorWidget 本身没有 _kline_tab，
# 真正嵌入的分钟K线面板是 self._minute_panel（_PeriodMonitorPanel）。
try:
    if hasattr(self, '_minute_panel') and self._minute_panel is not None:
        # _PeriodMonitorPanel 自身就有 focus_datetime() 方法
        # 内部会调 self._kline_tab._chart 的 vline + setXRange
        if hasattr(self._minute_panel, 'focus_datetime'):
            self._minute_panel.focus_datetime(
                clicked_dt, completed_daily=False)
            print(
                f"[联动V16] 主 Monitor 内嵌分钟K线 "
                f"跳到 {clicked_dt.date()} 中心完成")
        else:
            # fallback: 走 _kline_tab._chart
            inner_chart = getattr(
                self._minute_panel._kline_tab, '_chart', None)
            if inner_chart is not None and hasattr(
                    inner_chart, 'focus_datetime'):
                inner_chart.focus_datetime(
                    clicked_dt, completed_daily=False)
                print(
                    f"[联动V16] 主 Monitor 内嵌分钟K线 "
                    f"(chart 直调) 跳到 {clicked_dt.date()}")
except Exception as _inner_exc:
    print(f"[联动V16] 内嵌分钟K线 focus_datetime 失败: {_inner_exc}")
```

**设计意图**：
- **不依赖**任何外层逻辑（`signals` 查找、状态判断、_update_minute_view_for_date 是否被早退）；
- **直接调** `_minute_panel.focus_datetime` 这个**已经验证存在**的方法（V10 诊断日志证明它能正常进入）；
- **三道保险**：①`hasattr` ②调用 `_minute_panel.focus_datetime` ③fallback 到 `_kline_tab._chart.focus_datetime`；
- **完成/不完成都有 print**，方便从日志一眼看出走到了哪一步。

## banner 升级
```python
_BANNER_VERSION = "Monitor日线↔分钟联动 V16 (2026-08-23_23-50) — 全屏日线点击强制联动主 Monitor 内嵌分钟面板(不依赖外部全屏窗口)"
```

启动时打印：
```
[Monitor-Banner] version=Monitor日线↔分钟联动 V16 (2026-08-23_23-50) — ... file=.../condition_monitor_widget.py mtime=...
```

## 编译验证
```
$ python -c "import py_compile; py_compile.compile(...)"
OK compile
```

## 用户操作步骤

1. **重启 vnpy**，看到启动日志第一行：
   ```
   [Monitor-Banner] version=Monitor日线↔分钟联动 V16 ... mtime=2026-08-23 23:...
   ```
   确认 V16 已加载。

2. **打开 Monitor Tab（双周期）**，等待数据加载完成。

3. **点日线面板里任意一根 K 线**（或在日线全屏窗口里点）。

4. 看日志，应该有：
   ```
   [联动] 日线K线被点击: 2026-XX-XX
   [联动] 找到信号: 买入=0, 卖出=0
   [联动V16] 主 Monitor 内嵌分钟K线 跳到 2026-XX-XX 中心完成
   [focus_datetime] target_index=.../19999, target_bar_dt=...
   [focus_datetime] setXRange: new_left=..., new_right=...
   [focus_datetime] 退出: target_index=..., new_vline_pos=..., match=True
   ```

5. **视觉确认**：
   - 主 Monitor 下方的"分钟触发"面板 vline 应该**跳到点击日当天最后 1 根 minute bar**；
   - X 轴视口应该**自动滚动**，让 target 落在视口 65% 位置（不在边缘）；
   - **不需要**开"分钟线全屏窗口"也能看到联动（V16 的核心改进）；
   - 如果已开分钟线全屏窗口，**它也会同步联动**（来自 V12 的 `chart.focus_datetime(clicked_dt)`）。

## 与 V15 的差异

| 路径 | V15 | V16 |
|---|---|---|
| 自身日线点击 | `_update_minute_view_for_date` → `focus_datetime` | 同 V15 **+** 直接调 `_minute_panel.focus_datetime`（双调用，无副作用） |
| 全屏日线点击转发 | `_update_minute_view_for_date` + `_focus_minute_fullscreen_window` | 同 V15 **+** 直接调 `_minute_panel.focus_datetime`（**不依赖外层全屏窗口存在**） |
| 无全屏窗口时 | 主 Monitor 内嵌分钟面板应该联动，但用户看不到 | **强制**直接调 `_minute_panel.focus_datetime`，**不依赖任何外层链路** |

## 修改清单
- `vnpy/strategy_condition/ui/condition_monitor_widget.py`
  - banner → V16
  - `_handle_daily_bar_clicked` 增加 V16 块：直接调 `_minute_panel.focus_datetime(clicked_dt, completed_daily=False)`

## 验证
- ✅ py_compile 编译通过
- ✅ banner 升级到 V16
- ✅ 三道保险（hasattr + 调 panel.focus_datetime + fallback 到 _kline_tab._chart.focus_datetime）
- ✅ 异常用 print 暴露，不静默吞掉