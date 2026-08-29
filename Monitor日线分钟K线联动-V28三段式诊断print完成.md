# Monitor 日线↔分钟 K 线全屏联动 V28 — 三段式诊断 print 完成

## V28 的核心目的
**用户视角可观测**：在终端里**真实看到**每次点击是否被 3 段保险捕获,不再需要猜测。

---

## 文件
`vnpy/strategy_condition/ui/kline_view.py`

---

## 已植入 9 个 print（findstr 已验证全部落盘）

| # | 行号 | print 标记 | 所在位置 | 何时触发 |
|---|---|---|---|---|
| 1 | **2003** | `[V28-MODULE] kline_view.py 已被加载` | 模块底部 | 启动 vnpy 加载此模块时 |
| 2 | **2004** | `[V28-MODULE] V7 兜底 mousePressEvent + _on_mouse_clicked_for_link 已就绪` | 模块底部 | 同上 |
| 3 | **2005** | `[V28-MODULE] V18 _on_outer_daily_bar_clicked 已就绪` | 模块底部 | 同上 |
| 4 | **1760** | `[V28-CLICK-FN] _on_mouse_clicked_for_link 触发` | `_on_mouse_clicked_for_link` 入口 | 方案A（pyqtgraph scene）捕获点击 |
| 5 | **1787** | `[V28-CLICK-FN] 解析完成 x=..., dt=...` | `_on_mouse_clicked_for_link` 解析后 | 方案A 拿到 bar 索引和 datetime |
| 6 | **1939** | `[V28-CLICK] fullscreen daily bar clicked` | `mousePressEvent`（V7 兜底）出口 | 方案B（QWidget 鼠标）触发完整链路 |
| 7 | **1496** | `[KlineView][V18] 全屏窗口收到外部 daily_bar_clicked` | `_on_outer_daily_bar_clicked` 主路径 | 外部主 Monitor 推信号到全屏 |
| 8 | **1526** | `[KlineView][V18] 全屏窗口 vline 兜底移动 idx=` | `_on_outer_daily_bar_clicked` 退化路径 | focus_datetime 不存在时 |
| 9 | **1530** | `[KlineView][V18] 全屏窗口 _on_outer_daily_bar_clicked 失败` | 异常分支 | 出错时打印 traceback |

---

## V28 完整修复合并清单（与 V18 之前叠加）

### 方案A — pyqtgraph scene 信号路径
- 在 `_FullscreenChart.__init__`（**第 1081 行**）已绑定：
  ```python
  scene.sigMouseClicked.connect(self._on_mouse_clicked_for_link)
  ```
- `_on_mouse_clicked_for_link`（第 1754 行起）内做：
  1. 解析 x、dt → 发 `bar_clicked.emit(dt)` → 转给 `owner_monitor._on_daily_bar_clicked_from_outer`
  2. **方案B fallback**：走父链找 `_KlineFullscreenWindow._owner_monitor`，直接调 `owner_monitor._on_daily_bar_clicked_from_outer(focus_dt, from_fullscreen=True)`
  3. 日线 00:00 datetime 自动补成 23:59（避免被过滤）

### 方案B — QWidget 兜底（V7 mousePressEvent）
- `_FullscreenChart.mousePressEvent`（第 1880 行起）：
  1. 仅处理左键
  2. `self._glw_main.mapToScene(event.pos())` 拿 scene_pt
  3. `self._main_plot.vb.mapSceneToView(scene_pt)` 拿 x
  4. 走父链找 `_KlineFullscreenWindow._owner_monitor`
  5. 日线补 23:59，调 `_on_daily_bar_clicked_from_outer(focus_dt, from_fullscreen=True)`

### 方案C — V18 外部推信号
- `_KlineFullscreenWindow._on_outer_daily_bar_clicked(focus_dt, signals)`（第 1442 行）：
  1. 根据本窗口 `_interval` 判定 `completed_daily`
  2. 日线全屏 → `completed_daily=False`（直接跳该日）
  3. 分钟线全屏 → `completed_daily=True`（跳该日 15:00 收盘后位置）
  4. 调 `chart.focus_datetime(focus_dt, completed_daily=...)`
  5. 退化路径：若 `focus_datetime` 不存在，按 `_datetimes` 找最近 bar 移动 vline

### 配套修复（V18 之前已落地）
- `_KlineFullscreenWindow.__init__` V20 段：按 `datetimes` 实际间隔反推 `_interval`（原默认 DAILY 错判）
- `_KlineFullscreenWindow.__init__` V12/V4 段：`win._owner_monitor = owner_monitor` 注入
- `_on_fullscreen`（KlineViewTab）V8 段：监听 `owner_monitor.daily_bar_clicked` → `win._on_outer_daily_bar_clicked`
- `_KlineFullscreenWindow.closeEvent`：反注册 `owner_monitor._fullscreen_windows` + 断 `daily_bar_clicked` 监听

---

## V27 之前 **V7 兜底为什么静默失败**（本 V28 同步修正）

**根因**：上一次写文件时 V7 `mousePressEvent` 内部 if/else 缩进错位：
```python
if owner is not None:
    ...
owner._on_daily_bar_clicked_from_outer(focus_dt, from_fullscreen=True)  # ← 平级缩进,在 if 外
print(...)                                                                # ← 同上
```

**V28 修正**：
- 整段重写为正确缩进（每个 `if owner is None: return` 后只做 if 内的事）
- 在 `mousePressEvent` 入口与出口加 `[V28-CLICK]` 标记 print
- 在 `try/except` 中加 `print("异常: ...")`，**任何异常都不再静默**

---

## 终端操作步骤

1. **完全退出当前 vnpy 进程**（Ctrl+C 或关掉窗口），**确保不再运行**。
2. **清缓存**（如能执行）：
   ```cmd
   rd /S /Q vnpy\strategy_condition\ui\__pycache__
   ```
3. **重新启动 vnpy**（您通常用的命令，例如 `python run.py` 或 `examples/veighna_trader/run.py`）。
4. **启动时观察终端**：
   - 应当立即出现：
     ```
     ==========================================================
     [V28-MODULE] vnpy/strategy_condition/ui/kline_view.py 已被加载
     [V28-MODULE] V7 兜底 mousePressEvent + _on_mouse_clicked_for_link 已就绪
     [V28-MODULE] V18 _on_outer_daily_bar_clicked 已就绪
     ==========================================================
     ```
5. **进入 Monitor → 单击日线全屏 → 单击分钟线全屏**（应有 2 个全屏窗口）。
6. **在日线全屏窗口的任意 K 线上点击**：
   - **理想路径** → 终端应出现：
     ```
     [V28-CLICK-FN] _on_mouse_clicked_for_link 触发, evt_type=...
     [V28-CLICK-FN] 解析完成 x=..., dt=2025-..., len_bars=..., len_dt=...
     [KlineView][DEBUG] 方案B owner_monitor=ConditionMonitorWidget
     [KlineView][DEBUG] 方案B 已直接调用 owner_monitor._on_daily_bar_clicked_from_outer, focus_dt=...
     ```
   - **或兜底路径** → 终端应出现：
     ```
     [V28-CLICK] fullscreen daily bar clicked, dt=..., owner=ConditionMonitorWidget
     ```
7. **观察分钟线全屏窗口**：
   - vline 应跳到点击日 15:00 附近
   - 视口应自动滚动，使点击日位于视口偏右 65% 位置

---

## 故障排查映射（V28 后**绝不**再"什么都没发生"）

| 终端表现 | 诊断结论 | 下一步动作 |
|---|---|---|
| 启动后**完全没有** `[V28-MODULE]` 4 行 print | kline_view.py **未重新加载**（可能是旧 .pyc 缓存，或 vnpy 用打包模式） | 清 __pycache__，或重启 Python 进程；若仍无，确认 kline_view.py 路径正确 |
| `[V28-CLICK-FN] 触发` 出现但 `[V28-CLICK-FN] 解析完成` **不出现** | 坐标解析失败，点击**没落在**主图区域 | 检查全屏窗口是否被另一窗口遮挡；用 `窗口置顶` 验证 |
| `[V28-CLICK-FN] 解析完成` 出现但**完全没看到** `[V28-CLICK] fullscreen ... clicked` | 方案A 已发射 `bar_clicked.emit(dt)` 但方案B 未触发（说明 owner 解析失败） | 关注 `[KlineView] 方案B fallback 失败` 的异常打印 |
| `[V28-CLICK] fullscreen ... clicked` 出现但**分钟线全屏没反应** | 方案B 调了 owner，但 owner 内 `_on_daily_bar_clicked_from_outer` 出错 | 在 condition_monitor_widget.py 内查看是否有新 print；可能是 from_fullscreen 路径上 NPE |
| 启动后**所有 3 个 print 都出现**但**点击后什么 print 都没有** | 鼠标点击**根本没到 `_FullscreenChart`**，可能被 QGraphicsView 子类拦截 | 改方案：把 `_on_fullscreen` 里 `self._chart.bar_clicked.connect(...)` 后面加一行 `self._chart._main_plot.scene().sigMouseClicked.connect(lambda e: print("[V28-SANITY] scene.sigMouseClicked received", e.button()))` 验证 |
| `[V28-CLICK-FN] 收到非左键 (btn_int=2, btn=Qt.RightButton)` 一直出现 | 您点的是**右键**，代码已按 V7 兼容规则放行 | 用**左键**点击 |
| `[KlineView][V18] 全屏窗口收到外部 daily_bar_clicked` 出现但 vline **没动** | `focus_datetime` 走完但 `_vline.setPos` 失败或视口卡死 | 关注是否有异常；可手动 `print(chart._vline.pos())` 验证 |

---

## V28 核心承诺
**任何一次"点击没生效"都会在终端留下至少 1 行 print**。
若您按上述步骤操作后**完全没有**以下 print 中的任何一个：
- `[V28-MODULE]`（启动时）
- `[V28-CLICK-FN]` 或 `[V28-CLICK]`（点击时）

**就 100% 说明是 Qt 事件分发层根本没把点击送到全屏窗口的 K 线图元**（不是代码逻辑问题）。
此时请把那 4 行终端输出（启动 + 点击瞬间前后 5 秒的 print）发我，**我将精确定位是哪个层级吞了事件**。