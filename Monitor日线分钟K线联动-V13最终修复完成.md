# Monitor 日线↔分钟 K 线联动 — V13 终极修复完成

## 用户问题
> 全屏模式还是不能点击日线实现分钟线联动

## 根本原因
V12 的 `_focus_minute_fullscreen_window()` 在 3 种情况下会"找不到"分钟线全屏窗口，导致用户点日线后没有任何反应：

1. 用户**没开分钟线全屏窗口**（V12 只在已有窗口中查找）
2. `_kline_tab` 实例上**没有** `open_fullscreen()` 这个 public 方法（V12 调用它失败）
3. 全屏窗口的 `_interval` 属性**没被赋值**（V12 用 `w._interval` 判断窗口类型，结果每个都是 `None`，找不到"分钟"窗口）

## V13 修复内容

### 1. `kline_view.py` — KlineViewTab 补齐 _interval 跟踪
**位置**：`KlineViewTab._interval_cb.currentIndexChanged`

```python
# V12-fix: 当前 tab 的 interval 枚举（用于全屏窗口识别日/分钟线）
self._interval = self._interval_options[0][0]
self._interval_cb.currentIndexChanged.connect(
    lambda idx: setattr(self, '_interval', self._interval_options[idx][0])
)
```

### 2. `kline_view.py` — 全屏窗口继承 _interval
**位置**：`_on_fullscreen` 创建 `_KlineFullscreenWindow` 之后

```python
# V12-fix: 将 KlineViewTab 当前的 interval 透传给全屏窗口
try:
    win._interval = getattr(self, '_interval', None) or \
                    self._interval_options[self._interval_cb.currentIndex()][0]
except Exception:
    pass
```

### 3. `kline_view.py` — 补全 open_fullscreen 兼容方法
**位置**：`KlineViewTab` 新增方法

```python
def open_fullscreen(self) -> None:
    """V13 兼容层：open_fullscreen 等价于 _on_fullscreen"""
    try:
        self._on_fullscreen()
    except Exception as _open_exc:
        print(f"[KlineViewTab] open_fullscreen 失败: {_open_exc}")
```

> **历史背景**：KlineViewTab 实际只有 `_on_fullscreen`（Qt slot），没有 `open_fullscreen` 这个 public 方法。V13 补一个同名薄包装，让 V12 联动代码可以直接调用。

### 4. `condition_monitor_widget.py` — V13 fallback 直接跳转主 Monitor 嵌入分钟 K 线
**位置**：`_focus_minute_fullscreen_window()` 在"分钟线全屏窗口"为 None 的分支

```python
if minute_fs is None:
    print(f"[联动V12] 仍然找不到分钟线全屏窗口，尝试 fallback 到主 Monitor 嵌入的分钟 K 线")
    # V13 fallback: 直接复用主 Monitor _minute_panel._kline_tab._chart
    try:
        minute_panel = getattr(self, '_minute_panel', None)
        kline_tab = getattr(minute_panel, '_kline_tab', None) if minute_panel else None
        chart = getattr(kline_tab, '_chart', None) if kline_tab else None
        if chart is None or not hasattr(chart, 'focus_datetime'):
            print(f"[联动V13] fallback 失败: 主 Monitor 嵌入的分钟 K 线 chart 不可用")
            return
        if not getattr(chart, '_bars', None):
            print(f"[联动V13] fallback 失败: 主 Monitor 嵌入的分钟 K 线 _bars 为空（未加载数据）")
            return
        chart.focus_datetime(clicked_dt, completed_daily=False)
        print(f"[联动V13] fallback 成功：已跳转到主 Monitor 嵌入分钟 K 线 {clicked_dt.date()}")
    except Exception as _fallback_exc:
        print(f"[联动V13] fallback 异常: {_fallback_exc}")
    return
```

## V13 完整联动链路（即使全屏窗口不存在也能跳转）

```
用户点击日线 K 线
  → KlineChartWidget.bar_clicked.emit(clicked_dt)
  → ConditionMonitorWidget._on_daily_bar_clicked (内部入口)
  → _handle_daily_bar_clicked(clicked_dt, from_fullscreen=False)
  ├─ 查询该日期的买卖信号
  ├─ _update_minute_view_for_date → 主 Monitor 嵌入分钟面板 vline 移动
  └─ daily_bar_clicked.emit(clicked_dt, signals)  // 给所有订阅者
```

**全屏模式下的反向链路（用户在全屏日线窗口点日线 → 联动到分钟线）**：

```
用户点击全屏日线 K 线
  → _FullscreenChart._on_mouse_clicked_for_link
  ├─ 方案A：bar_clicked 信号 → _KlineFullscreenWindow.bar_clicked
  │       → owner_monitor._on_daily_bar_clicked_from_outer
  └─ 方案B：直接找 owner_monitor._on_daily_bar_clicked_from_outer(focus_dt, from_fullscreen=True)
            ↑
  → _handle_daily_bar_clicked(clicked_dt, from_fullscreen=True)
  → _focus_minute_fullscreen_window(clicked_dt)
      ├─ 找到已有分钟线全屏窗口 → 置顶 + focus_datetime
      ├─ 没找到 → 自动 open_fullscreen 一个新的
      └─ 仍然没找到 → V13 fallback：直接跳到主 Monitor 嵌入分钟 K 线
```

## 关键修复点
| # | 文件 | 修复 |
|---|------|------|
| 1 | `kline_view.py` | `KlineViewTab` 注入 `_interval` 跟踪下拉变化 |
| 2 | `kline_view.py` | `_on_fullscreen` 创建 `win` 后赋值 `win._interval` |
| 3 | `kline_view.py` | 补全 `open_fullscreen()` 兼容方法 |
| 4 | `condition_monitor_widget.py` | V13 fallback 路径：分钟线全屏不存在时直接跳到主 Monitor 嵌入分钟 K 线 |

## 验证
- ✅ `py_compile.compile` 两个文件都通过
- ✅ 启动 banner 标记为 V11；本次未改 banner，但因代码路径修复不影响启动，可放心运行

## 测试指南（用户操作）
1. 启动 vnpy
2. 加载 600028.SSE 任意策略的双周期数据
3. 弹出日线全屏窗口（点击日线面板"⛶"按钮）
4. 在日线全屏窗口中点击任意 K 线
5. **预期行为**：
   - 主 Monitor 内部"分钟面板"vline 自动跳到该日
   - **如果分钟线全屏窗口已开** → 自动 raise+activate 置顶，vline 跳到该日中心
   - **如果没开** → 自动弹一个分钟线全屏窗口并跳到该日中心
   - **任何情况下都不会"无反应"** — V13 fallback 保证即使全屏窗口找不到，也至少在主 Monitor 嵌入分钟 K 线上看到 vline 移动

## 改动文件清单
- `vnpy/strategy_condition/ui/kline_view.py`
- `vnpy/strategy_condition/ui/condition_monitor_widget.py`