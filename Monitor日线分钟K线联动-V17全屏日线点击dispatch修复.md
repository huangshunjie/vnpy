# Monitor 日线↔分钟K线联动 V17 修复完成

**日期**：2026-08-23  
**版本**：V17  
**文件**：`vnpy/strategy_condition/ui/condition_monitor_widget.py`  
**症状**：V8~V16 改了一堆，全屏窗口依然"日线点击→分钟全屏不动"。  
**根因**：`kline_view._on_fullscreen` 里的 `owner_monitor.daily_bar_clicked.connect(win._on_outer_daily_bar_clicked)` 只在"创建某全屏窗口时"被调用一次，且连接的 `win` 是"它自己"——所以**自己监听自己**，没有跨窗口效果。

---

## V17 关键设计：主动 dispatch

放弃"被动等信号"，改为 ConditionMonitorWidget **主动**遍历所有已注册全屏窗口，统一调它们的 `_on_outer_daily_bar_clicked(clicked_dt, signals)`。

### 三件套

1. **Banner 升级**（V17）
   ```python
   _BANNER_VERSION = "Monitor日线↔分钟联动 V17 (2026-08-23_23-52) — 全屏日线点击 dispatch 到所有已开全屏窗口(包括分钟K线全屏)"
   ```

2. **在 `_handle_daily_bar_clicked` 里插入调用**（放在 `daily_bar_clicked.emit` 之后）：
   ```python
   self.daily_bar_clicked.emit(clicked_dt, signals)
   self._dispatch_to_fullscreen_windows(clicked_dt, signals)  # V17 新增
   ```

3. **实现 `_dispatch_to_fullscreen_windows` 方法**：
   ```python
   def _dispatch_to_fullscreen_windows(self, clicked_dt, signals):
       try:
           wins = list(getattr(self, '_fullscreen_windows', []) or [])
           print(f"[联动V17] dispatch: 已注册全屏窗口 {len(wins)} 个, clicked_dt={clicked_dt.date()}")
           for w in wins:
               if w is None:
                   continue
               handler = getattr(w, '_on_outer_daily_bar_clicked', None)
               if handler is None:
                   print(f"[联动V17]   - 窗口 {type(w).__name__} 无 _on_outer_daily_bar_clicked 接口")
                   continue
               try:
                   handler(clicked_dt, signals)
                   print(f"[联动V17]   - 已 dispatch 到 {type(w).__name__}(_interval={getattr(w, '_interval', None)})")
               except Exception as _per_exc:
                   print(f"[联动V17]   - dispatch {type(w).__name__} 异常: {_per_exc}")
                   import traceback
                   traceback.print_exc()
       except Exception as _exc:
           print(f"[联动V17] _dispatch_to_fullscreen_windows 异常: {_exc}")
           import traceback
           traceback.print_exc()
   ```

---

## 工作流程（V17 全景）

1. 用户在 Monitor 主窗口的**日线 K 线**上点击；
2. `_connect_daily_click_handler` 连接的 `bar_clicked` 信号触发 `_on_daily_bar_clicked`；
3. 进入 `_handle_daily_bar_clicked(clicked_dt, from_fullscreen=False)`：
   - 计算 `clicked_date`；
   - `_get_signals_for_date(clicked_date)` 找该日的 buy/sell；
   - `_update_minute_view_for_date` → 主 Monitor 内嵌分钟面板 vline 跳到该日（V16）；
   - `daily_bar_clicked.emit(clicked_dt, signals)`（被 V8 自己的 connect 接住——但它只是 self 监听 self，没跨窗口效果）；
   - **`self._dispatch_to_fullscreen_windows(clicked_dt, signals)`**（V17 新增）→ **主动**遍历 `_fullscreen_windows`，每个窗口调一次 `_on_outer_daily_bar_clicked(clicked_dt, signals)`。

---

## 验证步骤

启动 vnpy，加载 600028.SSE Monitor，确认 banner 是 `V17`：

```
[Monitor-Banner] version=Monitor日线↔分钟联动 V17 (2026-08-23_23-52) ...
```

**测试场景 A：先开日线全屏，再开分钟全屏**（V17 主要修复）
1. 点日线面板『全屏』→ 弹出日线全屏窗口（已注册到 `_fullscreen_windows`）；
2. 点分钟面板『全屏』→ 弹出分钟全屏窗口（也注册到 `_fullscreen_windows`）；
3. 在**日线全屏**上点某根日线 K 线；
4. 期望：
   - 日线全屏自身 vline 跳到点击处；
   - **分钟全屏** vline + 视图跳到该日（关键！V17 修复点）；
   - 主 Monitor 内嵌分钟面板 vline 跳到该日（V16 已实现）。

控制台期望打印：
```
[联动] 日线K线被点击: 2026-04-20 (from_fullscreen=False)
[联动] 找到信号: 买入=0, 卖出=0
[联动V16] 主 Monitor 内嵌分钟K线 跳到 2026-04-20 中心完成
[联动V17] dispatch: 已注册全屏窗口 2 个, clicked_dt=2026-04-20
[联动V17]   - 已 dispatch 到 _KlineFullscreenWindow(_interval=d)
[联动V17]   - 已 dispatch 到 _KlineFullscreenWindow(_interval=5m)
```

**测试场景 B：在分钟全屏上点日线区（如果有）**
   - 不会触发（分钟全屏不显示日线轴）
   - 用户在分钟全屏里点 K 线只影响自己

---

## 已修改文件

- `vnpy/strategy_condition/ui/condition_monitor_widget.py`
  - 升级 banner 到 V17
  - `_handle_daily_bar_clicked` 增加 `self._dispatch_to_fullscreen_windows(clicked_dt, signals)` 调用
  - 新增 `_dispatch_to_fullscreen_windows(self, clicked_dt, signals)` 方法

## 编译验证

```
[OK] condition_monitor_widget.py syntax OK
```

---

## 已知限制

1. **依赖 `_KlineFullscreenWindow` 暴露 `_on_outer_daily_bar_clicked` 接口**
   - 该方法在 V8 已添加到 `_KlineFullscreenWindow` 类（参见之前的 kline_view.py 改动）
   - 它的内部用 `self._interval` 决定是直接 `focus_datetime`（日线）还是传 `completed_daily=True`（分钟）
2. **依赖 `_fullscreen_windows` 列表正确注册**
   - 由 `kline_view._KlineFullscreenWindow.__init__` 在创建时注册，closeEvent 时移除（V8 代码）
3. **如果某个全屏窗口没正确注册**（例如用户手动 new 出来的实例），仍然不会被 dispatch
   - 这是兜底设计——所有"通过 UI 按钮全屏打开的窗口"都会走 kline_view._on_fullscreen，注册路径一致