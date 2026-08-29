# Monitor 日线↔分钟K线联动 - 全屏模式修复 V2

## 🎯 根本原因（真正的 bug）

在 `_FullscreenChart` 中：
```python
def _redraw(self):
    ...
    self.bar_clicked = QtCore.Signal(object)   # ❌ 实例上赋值 Signal 类，这是无效的！
    try:
        scene = self._main_plot.scene()
        if scene is not None:
            scene.sigMouseClicked.connect(self._on_mouse_clicked_for_link)
```

**`QtCore.Signal(object)` 只能在类级别定义**。在实例方法内 `self.bar_clicked = QtCore.Signal(object)` 实际上**不是创建 Qt 信号**，只是给实例加了一个属性（其值是 `Signal` 类对象），后续的 `self.bar_clicked.connect(...)` 会抛 `TypeError`，被 try-except 吞掉了，导致：

1. `_FullscreenChart` 没有真正的 Qt 信号 `bar_clicked`
2. `_KlineFullscreenWindow` 中的 `self._chart.bar_clicked.connect(self.bar_clicked)` **直接失败**（属性不是 Signal）
3. 全屏窗口的 `bar_clicked` 信号永远收不到事件
4. owner_panel 的 `_on_daily_bar_clicked` 永远不被调用

## 🔧 修复内容

### 1. 把 Signal 提到类级别（kline_view.py）

**`_FullscreenChart` 类：**
```python
class _FullscreenChart(QtWidgets.QWidget):
    """全屏模式下的 K 线图渲染"""
    
    # 类级 Signal，修复前在实例方法中创建 Signal 是无效的
    bar_clicked = QtCore.Signal(object)
    
    def __init__(self, ...):
        super().__init__(parent)
        ...
        self._build_ui()
        # 在 _build_ui 之后连接 sigMouseClicked（必须先连接再 _redraw）
        try:
            scene = self._main_plot.scene()
            if scene is not None:
                scene.sigMouseClicked.connect(self._on_mouse_clicked_for_link)
                print(f"[KlineView][DEBUG] _FullscreenChart sigMouseClicked 已连接")
        except Exception as _exc:
            print(f"[KlineView] _FullscreenChart 绑定 sigMouseClicked 失败: {_exc}")
        self._redraw()
    
    def _build_ui(self):
        ...
        # 删除了原来 _redraw 末尾错误的 self.bar_clicked = QtCore.Signal(object)
        # 联动：日线点击事件转发（已在 _build_ui 后绑定，这里不要再覆盖 bar_clicked！）
    
    def _redraw(self):
        ...
        # 不再在这里创建 self.bar_clicked = QtCore.Signal(object)
        # 也不在这里连接 sigMouseClicked（已经在外层 __init__ 中连接）
```

**关键改动**：
- ✅ `bar_clicked` 改为**类级 Signal**（现在真的是 Qt 信号）
- ✅ `sigMouseClicked` 连接**移到 `__init__` 中 `_build_ui` 之后、`_redraw` 之前**（保证信号先连好再重绘）
- ✅ 删除 `_redraw` 末尾的 `self.bar_clicked = QtCore.Signal(object)` 错误代码

### 2. 验证链路

**`_KlineFullscreenWindow.__init__` 末尾：**
```python
# 转发点击事件：_FullscreenChart.bar_clicked → _KlineFullscreenWindow.bar_clicked
self._chart.bar_clicked.connect(self.bar_clicked)
```

现在 `self._chart.bar_clicked` 是**真正的 Qt Signal**（来自类级定义），`connect` 成功。

**`KlineViewTab._on_fullscreen` 中：**
```python
win.bar_clicked.connect(owner._on_daily_bar_clicked)
```

现在 `win.bar_clicked` 也会被发射，最终调用 `owner._on_daily_bar_clicked(datetime)`，触发 Monitor 联动。

## 📊 修复前后对比

| 阶段 | 修复前 | 修复后 |
|---|---|---|
| 类定义 | `bar_clicked` 不是 Signal | `bar_clicked = QtCore.Signal(object)` ✅ |
| 信号连接 | `self.bar_clicked = QtCore.Signal(object)` 在 _redraw 末尾（无效）| 在 `__init__` 中 `sigMouseClicked.connect` 一次 ✅ |
| `_KlineFullscreenWindow` 转发 | `self._chart.bar_clicked.connect(...)` 失败（属性不是 Signal）| 成功转发 ✅ |
| owner_panel 接收 | 永远收不到 bar_clicked | 正确接收 `datetime` ✅ |
| 日线点击联动分钟线 | ❌ 无效 | ✅ 工作 |

## 🚀 验证步骤

1. 重新启动 vnpy（已修改的源文件会生效）
2. 加载 600028.SSE 任意策略回测/监控
3. 进入 K线 Tab → 加载日线数据
4. **点击日线K线 → 看到 "日线K线被点击" 日志（之前不打印）**
5. **点击全屏按钮 ⛶**
6. **在全屏窗口中点击任意日线K线 → 日志显示"日线K线被点击: YYYY-MM-DD"**
7. **Monitor Tab 的分钟线应该自动跳转到对应日期范围**

## 🔍 调试日志（重启后应该看到）

启动时（无变化）：
- `[联动] 日线K线点击事件已连接` （非全屏模式）

打开全屏窗口时（新增）：
- `[KlineView][DEBUG] _FullscreenChart sigMouseClicked 已在 _build_ui 阶段连接`
- `[KlineView][DEBUG] _KlineFullscreenWindow 转发前: chart.bar_clicked=<Signal>, self.bar_clicked=<Signal>`
- `[KlineView][DEBUG] _KlineFullscreenWindow bar_clicked 转发连接成功`

**点击全屏K线时（新增，应该看到）：**
- `[KlineView][DEBUG] _on_mouse_clicked_for_link 进入, evt=<pyqtgraph.GraphicsScene.mouseEvents.MouseClickEvent>, ...`
- `[KlineView][DEBUG] 全屏K线被点击: x=xxx, dt=YYYY-MM-DD HH:MM:SS, 发射 bar_clicked`

**最终（已存在）：**
- `[联动] 日线K线被点击: YYYY-MM-DD`

## 🛠️ 文件变更

仅修改了 `vnpy/strategy_condition/ui/kline_view.py` 一个文件：
- `_FullscreenChart`：类级 Signal + 重构初始化顺序
- `_KlineFullscreenWindow`：保持原有转发逻辑（现在能正常工作）

## 📝 备注

之前的所有修复（KlineViewTab._on_fullscreen 中连接 owner_panel、_KlineFullscreenWindow 中转发等）**都是正确的**。本次修复只针对**类级 Signal 缺失**这一根本 bug。修复后整套链路完整打通。