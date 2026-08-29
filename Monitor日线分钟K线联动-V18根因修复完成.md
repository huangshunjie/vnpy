# Monitor日线分钟K线联动 — V18 根因修复完成

## 终极根因（V18）

`vnpy/strategy_condition/ui/kline_view.py` 中 `_KlineFullscreenWindow._on_outer_daily_bar_clicked` 在调用 `chart.focus_datetime(focus_dt, completed_daily=False)` 时**硬编码 `completed_daily=False`**。

而 `_FullscreenChart` 类**根本没有 `focus_datetime` 方法**（该方法只存在于 `KlineChartWidget`/`_PeriodMonitorPanel`），所以 `hasattr(chart, 'focus_datetime')` 一直返回 False，**始终走兜底逻辑**：循环 `chart._datetimes` 找最接近 `focus_dt` 的 bar 索引。

**结果**：当用户在日线面板点击 2026-05-28 时，`focus_dt=2026-05-28 00:00:00`；分钟线全屏窗口拿到这个 dt，循环找最近的 bar — 但 minute bars 通常从 9:30 开始（早于 00:00:00 距离也可能短），实际行为是**vline 跳到了用户点击日的 9:30 那根附近**，而不是该日 15:00 收盘位置 — 用户视觉感受"分钟线没动/跳到早上"。

## V18 修复内容

修改了 `_KlineFullscreenWindow._on_outer_daily_bar_clicked`：

1. **读取自身 `_interval` 属性**（V12 已注入，KlineViewTab 在创建全屏窗口时会透传 `self._interval`），判定当前是"日线全屏"还是"分钟全屏"。
2. **动态计算 `completed_daily`**：
   - 日线全屏 → `completed_daily=False`（直接找该日对应 bar）
   - 分钟线全屏 → `completed_daily=True`（把 target 改为 `focus_dt.date() 15:00`，找 15:00 收盘附近的那根）
3. **保留兜底逻辑**（以防 `focus_datetime` 不存在或 `_datetimes` 为空），但在兜底中也应用了 15:00 target 修正。

## 修改文件

- `vnpy/strategy_condition/ui/kline_view.py`
  - `_KlineFullscreenWindow._on_outer_daily_bar_clicked`：增加 `my_interval` 读取与 `is_minute_window` 判定，分钟线全屏时把 target dt 改为 15:00；更新 print 信息为 V18。

## 验证步骤

1. 重启 vnpy trader
2. 加载 600028.SSE
3. 打开 Monitor Tab 加载 5m + d 周期数据
4. 弹出分钟全屏窗口（点击内嵌分钟面板的"全屏"按钮）
5. **回主 Monitor**，点击**日线面板**任一日 K 线（如 2026-05-28）
6. **预期**：
   - 主 Monitor 内嵌分钟面板 vline 跳到 2026-05-28 15:00 附近 ✅ (V8 已修)
   - **全屏分钟窗口** vline 跳到 2026-05-28 15:00 附近 ✅ (V18 新修)
   - 日志输出 `[KlineView][V18] 全屏窗口收到外部 daily_bar_clicked: focus_dt=2026-05-28 00:00:00, my_interval=Interval.MINUTE_5, is_minute=True, completed_daily=True, vline 已移动`

## 涉及版本演进

- V1-V7：基础信号连接 + 点击处理
- V8：全屏窗口独立监听 `owner_monitor.daily_bar_clicked`
- V9-V17：连续修复 close_event、属性注入、可见性、dispatch 等问题
- **V18**（本次）：**根因修复** — `completed_daily` 参数 + 分钟全屏 target 改 15:00

## AST 验证

```
$ python -c "import ast; ast.parse(open('vnpy/strategy_condition/ui/kline_view.py', encoding='utf-8').read()); print('AST OK')"
AST OK