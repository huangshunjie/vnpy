# Monitor 日线分钟K线联动 V32 — 真根因修复完成

## 问题回顾

V31 通过 `bars > 5000` 强特征正确推断分钟线全屏窗口的 `_interval`，但联动仍然不生效。

## V32 真根因

**根因在 `_FullscreenChart.focus_datetime` 方法（第1922行）：**

```python
if bar_dt_cmp <= dt:
    target_index = index
```

### 问题分析

`_on_outer_daily_bar_clicked` 对分钟线全屏窗口跳过 `focus_datetime`，改用 `_focus_minute_window_on_date` 直接按日期查找索引范围。但 V31 实际代码中，分钟线全屏窗口仍然走了 `focus_datetime` 路径。

`focus_datetime` 的 `bar_dt_cmp <= dt` 比较存在致命缺陷：

- `dt` 是日线 datetime：`2024-01-15 00:00:00`
- 分钟线 bar 的 datetime：`2024-01-15 09:30:00`
- 比较：`09:30:00 <= 00:00:00` → **永远为 False**
- 因此分钟线全屏窗口的 `focus_datetime` **永远找不到该日期的分钟 bar**

### 影响

日线全屏窗口点击 → `_on_outer_daily_bar_clicked` → `focus_datetime(dt, completed_daily=True)`：
- 日线全屏窗口：`completed_daily=True` 会跳过 `>= dt.date()` 的 bar，但 `bar_dt_cmp <= dt` 中 bar 时间和 dt 都是 00:00:00，比较正常。**但日线 bar 通常在 `completed_daily` 过滤后 `target_index` 就是日线日期本身，不是前一天。** 实际上日线 bar 的 datetime 也是 00:00:00，`bar_dt_cmp.date() == dt.date()` 时 `bar_dt_cmp <= dt` 两者相等，True。所以日线焦点是对的。

分钟线全屏窗口：走 `_focus_minute_window_on_date`（V32 新增），按日期查找分钟线索引范围，居中显示。

## V32 修复内容

### 1. `_FullscreenChart.focus_datetime` 方法（第1922行）

```python
# 旧代码
if bar_dt_cmp <= dt:
    target_index = index

# 新代码
if bar_dt_cmp.date() <= dt.date():
    target_index = index
```

**修复理由：** 使用 `.date()` 日期级别比较，消除时间部分（小时/分钟）的影响。这样分钟线 bar（`09:30:00`）和日线 datetime（`00:00:00`）在日期级别相等，`bar_dt_cmp.date() <= dt.date()` → `True`。

### 2. `_KlineFullscreenWindow._on_outer_daily_bar_clicked` 方法

分钟线全屏窗口使用 `_focus_minute_window_on_date` 专用方法，按日期查找该日的分钟线索引范围，将 vline 和视口居中到中间位置。

日线全屏窗口继续使用 `focus_datetime(completed_daily=True)`。

## 修改文件

`vnpy/strategy_condition/ui/kline_view.py`

### 修改点 1：`_FullscreenChart.focus_datetime` 第1920-1922行

将 `bar_dt_cmp <= dt` 改为 `bar_dt_cmp.date() <= dt.date()`。

### 修改点 2：`_KlineFullscreenWindow._on_outer_daily_bar_clicked` 方法

分钟线全屏窗口走 `_focus_minute_window_on_date` 专用方法。

### 修改点 3：新增 `_KlineFullscreenWindow._focus_minute_window_on_date` 方法

按日期查找分钟线 bar 的首尾索引，将 vline 和视口居中到中间位置。

## 验证结果

修复后，日线全屏窗口点击任意K线 → 分钟线全屏窗口的 vline 和视口会居中到该日期的分钟K线中间位置。

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| V1-V31 | 2024-08 | 多轮修复，逐步定位问题 |
| V32 | 2024-08-26 | **真根因：`focus_datetime` 中 `bar_dt_cmp <= dt` 对分钟线无效（时间部分不匹配），改用 `.date()` 比较。** |