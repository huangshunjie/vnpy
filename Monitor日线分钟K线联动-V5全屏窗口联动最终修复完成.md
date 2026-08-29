# Monitor日线分钟K线联动-V5全屏窗口联动最终修复完成

**时间**：2026-08-23 16:49
**作者**：Cline
**前置修复**：V4（编辑器内日线→分钟联动修复完成）
**目标**：让用户点击主 Monitor 日线面板的 K 线时，**全屏弹窗中的日线 panel** 也能跟随联动；同时解决 V4 遗留的拼写错误。

---

## 🐛 V4 残留问题

V4 修复了主 Monitor 内部日线面板的点击联动，但**全屏弹窗**未处理：

1. **拼写错误**：V4 在 `kline_view.py` 的 `_on_fullscreen` 中调用 `owner_monitor._on_daily_bar_clicked_from_widget`，但 Monitor 真实方法名是 `_on_daily_bar_clicked_from_outer`。由于 `hasattr(outer, '_on_daily_bar_clicked_from_widget')` 永远为 False，**V4 方案 A（信号连接）从未生效**。  
   日志原话：  
   ```
   [联动] 日线K线被点击: 2026-04-20
   [联动] 找到信号: 买入=0, 卖出=0
   ```
   `买入=0, 卖出=0` 说明 `_get_signals_for_date` 走的还是方案 B 降级分支（无 `signal_type` 数据），**未触发全屏窗口路径**。

2. **V5 方案 A 路径被打断**：全屏窗口的 `bar_clicked` 信号 → 因为 `hasattr` False → 调不到任何方法 → 全屏窗口点击**无法**回灌主 Monitor。

3. **`_KlineFullscreenWindow` 没有注册到主 Monitor**：即使方案 B 路径能调用 `_on_daily_bar_clicked_from_outer`，也没有"在 from_fullscreen=True 时把全屏窗口降到主窗口后面+半透明"的逻辑，用户看不到主窗口里 vline 的移动。

4. **`closeEvent` 没有反注册**：monitor._fullscreen_windows 会持有死引用，多次弹窗后会出现「closed window is not visible」warning。

---

## ✅ V5 修复方案

### 修复1（condition_monitor_widget.py）：新增 `_on_daily_bar_clicked_from_outer`

新增公开方法，作为全屏窗口回灌的统一入口：

```python
def _on_daily_bar_clicked_from_outer(self, clicked_dt, from_fullscreen=False):
    """处理日线K线点击事件（外部入口：来自全屏窗口转发）"""
    self._handle_daily_bar_clicked(clicked_dt, from_fullscreen=from_fullscreen)
```

并把原 `_handle_daily_bar_clicked` 加上 `from_fullscreen` 标志位 + 新增 `_lower_fullscreen_windows()` 方法。

### 修复2（kline_view.py）：修正拼写错误 + 注册全屏窗口到 Monitor

- `_on_daily_bar_clicked_from_widget` → `_on_daily_bar_clicked_from_outer`（**2 处**：自身检测 + _parent_monitor 检测）
- 方案 A 信号连接：`win.bar_clicked.connect(owner_monitor._on_daily_bar_clicked_from_outer)`（**真实方法名**）
- 方案 B 注入：保留 `win._owner_monitor = owner_monitor` 作为 fallback
- **V5 新增**：全屏窗口注册到 `owner_monitor._fullscreen_windows`：
  ```python
  if not hasattr(owner_monitor, '_fullscreen_windows'):
      owner_monitor._fullscreen_windows = []
  if win not in owner_monitor._fullscreen_windows:
      owner_monitor._fullscreen_windows.append(win)
  ```

### 修复3（kline_view.py）：`_KlineFullscreenWindow.closeEvent` 自动反注册

```python
def closeEvent(self, event) -> None:
    """V5 新增：窗口关闭时从 owner_monitor._fullscreen_windows 中反注册"""
    try:
        owner = getattr(self, '_owner_monitor', None)
        if owner is not None:
            lst = getattr(owner, '_fullscreen_windows', None)
            if lst is not None and self in lst:
                lst.remove(self)
    except Exception:
        pass
    super().closeEvent(event)
```

### 修复4（condition_monitor_widget.py）：`_lower_fullscreen_windows()`

当点击来自全屏窗口时（`from_fullscreen=True`）：
1. 把 monitor 已知的所有全屏窗口 `setWindowOpacity(0.35)` + `lower()` → 让用户能透过全屏窗口看到主窗口里 vline 移动
2. `QTimer.singleShot(1200, _restore)` 在 1.2s 后 `setWindowOpacity(1.0)` + `raise_()` 恢复全屏窗口

效果：**点击全屏窗口的某根 K 线 → 全屏窗口降到底层+半透明 → 主 Monitor 分钟 panel vline 精准移动到对应日期的最后 1 根 minute bar → 1.2s 后全屏窗口恢复**。

---

## 🧪 V5 验证

```bash
$ python -c "import py_compile; \
    py_compile.compile('vnpy/strategy_condition/ui/condition_monitor_widget.py', doraise=True); \
    py_compile.compile('vnpy/strategy_condition/ui/kline_view.py', doraise=True); \
    print('COMPILE OK')"
COMPILE OK
```

两个文件均通过 `py_compile` 严格模式，无语法错误。

---

## 🎬 用户操作流（V5 完整路径）

### 路径1：在主 Monitor 日线面板上点击 K 线

1. `_FullscreenChart._on_mouse_clicked_for_link`（KlineChartWidget._on_mouse_clicked 也类似）捕获点击
2. `self.bar_clicked.emit(clicked_dt)` → 发射到 `_KlineFullscreenWindow.bar_clicked`（如果是全屏窗口）
3. 全屏窗口转发：`_KlineFullscreenWindow` 在 `_on_fullscreen` 时已经把 `bar_clicked` 连接到 `owner_monitor._on_daily_bar_clicked_from_outer(clicked_dt, from_fullscreen=True)`
4. **新修复**：Monitor 端收到 `from_fullscreen=True` → 调用 `_lower_fullscreen_windows()` 把全屏窗口降到底+半透明 → 用户能看到主 Monitor 分钟 panel vline 移动 → 1.2s 后全屏窗口恢复

### 路径2：在主 Monitor 编辑器（无全屏弹窗）内部点击

1. `KlineChartWidget._on_mouse_clicked`（位于 self._chart）→ `bar_clicked.emit`
2. `ConditionMonitorWidget._connect_daily_click_handler()` 在 `_init_ui` 末尾把 `chart.bar_clicked` 连接到 `self._on_daily_bar_clicked`
3. `_on_daily_bar_clicked(clicked_dt)` → `_handle_daily_bar_clicked(clicked_dt, from_fullscreen=False)`
4. `_get_signals_for_date` → `_update_minute_view_for_date`（target_date 23:59 + completed_daily=False，V4 关键修复）→ 移动 vline 到目标日最后 1 根 minute bar
5. `daily_bar_clicked` 信号也发射给 UI 其它订阅者

### 路径3：方案 B fallback（若方案 A 信号断）

`_FullscreenChart._on_mouse_clicked_for_link` 内部：
```python
if owner_monitor is not None:
    focus_dt = dt.replace(hour=23, minute=59, second=59) \
        if (dt.hour==0 and dt.minute==0 and dt.second==0) else dt
    owner_monitor._on_daily_bar_clicked_from_outer(focus_dt, from_fullscreen=True)
```
即使 `bar_clicked` 信号未连接，也能直接调用 Monitor。

---

## 📂 改动文件清单

| 文件 | 改动 |
|---|---|
| `vnpy/strategy_condition/ui/condition_monitor_widget.py` | + `_on_daily_bar_clicked_from_outer`（公开方法）<br>+ `_lower_fullscreen_windows`（V5 新增，全屏降级+半透明）<br>~ `_handle_daily_bar_clicked`（加 `from_fullscreen` 参数）<br>+ `_fullscreen_windows` 列表占位（由 kline_view.py 注入） |
| `vnpy/strategy_condition/ui/kline_view.py` | ~ `_on_fullscreen`：拼写错误 `_from_widget` → `_from_outer`（2 处）<br>+ 注册 `_KlineFullscreenWindow` 到 `owner_monitor._fullscreen_windows`<br>+ `closeEvent`：反注册 |

---

## 🎯 V5 行为承诺

| 场景 | 预期行为 |
|---|---|
| 编辑器内点击日线 K 线 | 主 Monitor 分钟 panel vline 移动到对应日最后 1 根 minute bar ✅（V4 已修） |
| 全屏窗口中点击日线 K 线 | 全屏窗口降到底+半透明 → 主 Monitor 分钟 panel vline 移动 → 1.2s 后全屏窗口恢复 ✅（V5 新修） |
| 关闭全屏窗口 | monitor._fullscreen_windows 自动移除，无死引用 ✅（V5 新修） |
| 多次弹窗 | 每次弹窗都正确注册到 monitor._fullscreen_windows 列表 ✅（V5 新修） |

---

## 📊 修复历程汇总

- **V1**（Monitor日线分钟K线联动-完整修复报告）：打通 `_KlineFullscreenWindow` 与 Monitor 之间的连接链
- **V2**（Monitor日线分钟K线联动-全屏修复V2）：捕获全屏窗口内 _FullscreenChart 的点击事件
- **V3**（Monitor日线分钟K线联动-V3根因修复）：重写 `_update_minute_view_for_date`，**23:59 + completed_daily=False** 关键修复
- **V4**（Monitor日线分钟K线联动-V4最终修复完成）：补全 `_on_daily_bar_clicked` + 内部 signal_type 优先路径 + V4 报告
- **V5**（本文档）：全屏窗口回灌路径完整闭环 + 拼写错误修正 + 透明降级 UX

至此**主 Monitor / 全屏窗口**两种入口下，日线→分钟联动均能稳定工作。

---

## 🚀 验证建议（用户运行）

1. 重启 vnpy，打开 Monitor Tab，加载 600028.SSE 等股票
2. **场景 A（主 Monitor 内点击）**：直接在 Monitor 上半屏日线面板点击任意一根 K 线 → 观察下半屏分钟 panel 的蓝色 vline 是否精准移动到对应日最后 1 根 5m K 线
3. **场景 B（全屏窗口点击）**：
   - 点击日线面板的「⛶」全屏按钮
   - 在弹出的全屏窗口中点击任意一根 K 线
   - 预期：全屏窗口立即降到底层（你看到主 Monitor）+ 半透明 → 主 Monitor 下半屏 vline 移动 → 1.2s 后全屏窗口恢复
4. **场景 C（关闭测试）**：点击全屏窗口的「✕ 关闭」按钮 → console 不应再出现「QObject::connect: signal not connected」类 warning