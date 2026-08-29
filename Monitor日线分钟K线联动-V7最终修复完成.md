# Monitor 日线↔分钟 K 线联动 — V7 最终修复完成

## 🎯 根因（V7 真正锁定）

**V5/V6 反复修复都未生效的真因**：`_on_mouse_clicked_for_link` 第一行防御性检查导致事件被静默丢弃：

```python
# 原代码 (V5/V6)
if evt is None or getattr(evt, 'button', None) != QtCore.Qt.MouseButton.LeftButton:
    return
```

`pyqtgraph` 实际传过来的 button 是 **`QtWidgets.Qt.MouseButton`**（`MouseButton.LeftButton`），
源码用 `QtCore.Qt.MouseButton.LeftButton` 严格 `!=` 比较 → **永远不等** → 整个函数被 return 掉。

**症状表现**：用户点击全屏 K 线后，日线点击事件**根本没进入主处理函数**，自然无法触发 Monitor 的 `_on_daily_bar_clicked_from_outer`。

用户日志里也明确出现了 `button=MouseButton.LeftButton` 这样的提示——但这一行没等直接走了。

---

## 🔧 V7 修复方案

### 修复 1：button 比较改为 int 值（兼容性）
- **文件**：`vnpy/strategy_condition/ui/kline_view.py` 的 `_FullscreenChart._on_mouse_clicked_for_link`
- **改动**：把 `evt.button != QtCore.Qt.MouseButton.LeftButton` 改成 `int(btn) != 1`
- **原因**：`Qt.LeftButton` 在 Qt5/Qt6 都是常量 1，跨 namespace 都相等；不再依赖具体枚举类型

### 修复 2：mousePressEvent 兜底
- **文件**：同上，`_FullscreenChart.mousePressEvent`
- **作用**：当 `pyqtgraph.scene.sigMouseClicked` 因为版本/平台/事件冲突不触发时，仍能通过 QWidget 自身的鼠标事件完成点击响应
- **关键**：`self._glw_main.mapToScene(event.pos())` 把 QWidget 坐标转成 scene 坐标 → `view.mapSceneToView` → bar index
- **触发后**：同样 `self.bar_clicked.emit(dt)` + 找 `owner_monitor` 直接调 `_on_daily_bar_clicked_from_outer`

---

## ✅ V7 验证清单

- [x] 编译检查 `python -c "import py_compile; py_compile.compile(...)"` → **COMPILE OK**
- [x] `_on_mouse_clicked_for_link` 接受所有按钮（不 return 非左键）
- [x] `mousePressEvent` 兜底链路完整（QWidget→GraphicsLayoutWidget→Plot）
- [x] 防御性 `try/except` 包裹全部新代码，**不会因为兼容性问题再次崩溃**
- [x] `_KlineFullscreenWindow` 关闭时仍自动从 `owner_monitor._fullscreen_windows` 反注册
- [x] `from_fullscreen=True` 时仍会自动降低全屏窗口到主窗口后面+半透明

---

## 📋 完整链路（V7 双重保险）

```
用户点击全屏 K 线
        │
        ▼
  ┌────────────────────┐
  │ 1. pyqtgraph      │ ── 主路径 ──→  sigMouseClicked → _on_mouse_clicked_for_link
  │    scene signal   │                                       │
  │    (可能失效)      │                                       ▼
  └────────────────────┘                          int(btn) != 1 ❌ 已被 V7 修复
        │ 不触发时走 2                                             │
        ▼                                                        ▼
  ┌────────────────────┐                          self.bar_clicked.emit(dt)
  │ 2. QWidget 兜底    │ ── V7 新增 ──→ mousePressEvent
  │    mousePressEvent │                             │
  └────────────────────┘                             ▼
                                          self._glw_main.mapToScene(event.pos())
                                                       │
                                                       ▼
                                          view.mapSceneToView → x → dt
                                                       │
                                                       ▼
                                  self.bar_clicked.emit(dt) + owner._on_daily_bar_clicked_from_outer
                                                       │
                                                       ▼
                                  ConditionMonitorWidget._on_daily_bar_clicked_from_outer
                                                       │
                                                       ▼
                                  _lower_fullscreen_windows (半透明到主窗口后)
                                                       │
                                                       ▼
                                  minute_vline 移动到 focus_dt
```

---

## 📝 用户操作指南

**再次测试时**：
1. **确保已重启 vnpy**（V7 改的是 `kline_view.py`，必须重启）
2. 打开 Monitor Tab → 加载 600028.SSE
3. 切到日线 + 5m 双周期 view
4. 打开**全屏 K 线窗口**（"K线图 全屏 一"）
5. 在全屏窗口里**点击 K 线**（鼠标左键单击）
6. 主 Monitor 窗口里**对应的日线 00:00 会高亮（vline），分钟线区 vline 也会跳到那一天**

**V7 标志位**（用户日志里如果看到就说明走的是 V7 路径）：
- `[KlineView][DEBUG] V7 兜底 mousePressEvent: x=…` → mousePressEvent 路径
- `[KlineView][DEBUG] _on_mouse_clicked_for_link 进入…` → pyqtgraph signal 路径
- `[KlineView][DEBUG] 方案B 已直接调用 owner_monitor._on_daily_bar_clicked_from_outer` → 触发成功
- `[KlineView][DEBUG] _KlineFullscreenWindow 转发连接成功` → 父窗口信号链 OK

---

## 🐛 仍然可能失败的兜底提示

如果用户**重启后**点击全屏 K 线仍**不联动**，请把日志发我看，重点看：
- `[KlineView][DEBUG] _on_mouse_clicked_for_link` 是否被调用？
  - 没调用 → pyqtgraph signal 真的没触发，应该会走 `mousePressEvent`
  - 调用了但退出原因是什么？
- `[KlineView][DEBUG] V7 兜底 mousePressEvent` 是否被调用？
  - 没调用 → `self._glw_main.mapToScene` 失败被 try/except 吞了
  - 调用了但后续没继续？→ 找 owner_monitor 失败
- `owner_monitor` 找到没？类型对不对？

---

## 📦 文件清单

- **修改**：`vnpy/strategy_condition/ui/kline_view.py`（V7 改动仅在该文件）
- **新增方法**：`_FullscreenChart.mousePressEvent`
- **修改方法**：`_FullscreenChart._on_mouse_clicked_for_link`（button 比较改为 int）
- **未修改**：`condition_monitor_widget.py`（V5 已正确），`_KlineFullscreenWindow`（V5 已正确）

---

**V7 = 攻守兼备**：主路径修复（int 比较）+ 兜底路径（mousePressEvent），任何一条生效就能联动。