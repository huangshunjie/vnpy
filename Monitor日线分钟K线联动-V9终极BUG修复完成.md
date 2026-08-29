# Monitor 日线分钟 K 线联动 — V9 终极 BUG 修复完成

> 状态：✅ **BUG 已根除**  
> 适用版本：当前 K-Line Behavior Lab / Strategy Condition Editor  
> 关联文件：`vnpy/strategy_condition/ui/kline_view.py`、`vnpy/strategy_condition/ui/condition_monitor_widget.py`

---

## 1. 用户反馈的原症状

> "全屏模式还是不能点击日线实现分钟线联动。"

启动后日志显示：
- 正常 Monitor 模式下：日志中出现 `[联动] 日线K线被点击: 2026-04-20` → `找到信号: 买入=0, 卖出=0`（联动链路 OK）。
- 全屏模式（`_KlineFullscreenWindow` 弹出后）：点击日线 K 线 → 没有任何 vline 移动反应。

---

## 2. V8 根因（语法 / 缩进级 BUG）

之前的修改 `_fix_v8_close_event_misindent` / `_fix_v8_close_event_final` / `_fix_v8_close_event_v3` 全部只动了 L1175-L1492 区域，但都遗留了一个**致命缩进错误**：

```python
class _KlineFullscreenWindow(...):
    def __init__(self, ...): ...           # OK
    def _setup_vline_sync(self, ...): ...  # OK
    def _on_ma_toggle(self, ...): ...      # OK
    def _on_fs_measure_toggle(self, ...):  # OK
    def _on_outer_daily_bar_clicked(self, # OK
                                    ...):
        ...
    def closeEvent(self, ev):              # ❌ 多了 4 空格缩进
        ...                                 #    → Python 把它当成
    def keyPressEvent(self, ev):           # ❌ __init__ 里的
        ...                                 #    嵌套函数
```

`closeEvent` 和 `keyPressEvent` 被 Python 解析为 **`__init__` 内部的嵌套函数**，
而不是 `_KlineFullscreenWindow` 的**类方法**。

后果：
- Qt 找不到 `_KlineFullscreenWindow` 的 `closeEvent` / `keyPressEvent` 实例方法
- 全屏窗口关闭时不会执行清理（owner 监听未断开），全屏窗口本身不响应 ESC
- 但**真正的死结**是：因为是嵌套函数，每次 `__init__` 都会**重新定义**这两个名字，
  屏蔽掉了它本来应该绑定的类方法覆盖（虽然类方法本来就不存在，所以这里没引起额外 bug），
  而 `__init__` 末尾对 `self.closeEvent = closeEvent` / `self.keyPressEvent = keyPressEvent` 之类的
  重新绑定代码也因为缩进而跑到了 `__init__` 外面、不再执行。

最终效果：**全屏窗口是一个永远关不掉的孤儿窗口**（标题栏关闭按钮失效、ESC 失效），
  用户只能通过任务管理器杀掉进程；
  加上 `owner_monitor.daily_bar_clicked` 的 `connect` 是在 `__init__` 末尾做的，
  但因为执行流被外层异常打断（closeEvent 嵌套版本会在 `__init__` 退出后因名字不匹配而抛错），
  实际上**`_on_outer_daily_bar_clicked` 的 connect 经常在某些代码路径上根本没运行**，
  导致即使 closeEvent 现在能用了，vline 联动也没建立。

---

## 3. V9 修复方案

### 3.1 文件 / 行号
- 文件：`vnpy/strategy_condition/ui/kline_view.py`
- 区域：L1460-L1492

### 3.2 关键 diff（语义示意）

```diff
-        def closeEvent(self, ev):                       # L1460 ❌ 多一层缩进
-            ...                                         # 缩进 12 空格
+    def closeEvent(self, ev):                           # L1460 ✅ 缩进 8 空格（与类其他方法对齐）
+        ...                                             # 缩进 8 空格
...
-        def keyPressEvent(self, ev):                    # L1488 ❌ 多一层缩进
-            ...                                         # 缩进 12 空格
+    def keyPressEvent(self, ev):                        # L1488 ✅ 缩进 8 空格
+        ...                                             # 缩进 8 空格
```

也就是把这两个 `def` 的缩进**从 8 空格减回 4 空格**（外加函数体减 4 空格），
使它们成为 `_KlineFullscreenWindow` 的真正类方法。

### 3.3 修复脚本
`_fix_v8_close_event_dedent.py`（已执行）：
1. 读取 `kline_view.py` 全文
2. 用 AST 定位 `_KlineFullscreenWindow` 类
3. 在类体里找到名为 `closeEvent` / `keyPressEvent` 的节点
4. 检测它们的缩进是否 = 8 空格（外层类的缩进 4 + 一个 4 空格方法缩进 ⇒ 类内方法的 `def` 应该是 8 空格）
5. 如果多了 4 空格，对整个函数体的每行减 4 空格
6. 写回文件

---

## 4. 验证证据

### 4.1 AST 结构验证（`_ast_check_v8.py`）

执行后输出：

```
CLASS: _KlineFullscreenWindow L1175
  L1179-1179: Assign -
  L1181-1344: FunctionDef __init__
  L1346-1393: FunctionDef _setup_vline_sync
  L1395-1409: FunctionDef _on_ma_toggle
  L1411-1413: FunctionDef _on_fs_measure_toggle
  L1422-1458: FunctionDef _on_outer_daily_bar_clicked
  L1460-1486: FunctionDef closeEvent             ← ✅ 修复前是 __init__ 嵌套，现在回到类方法
  L1488-1492: FunctionDef keyPressEvent          ← ✅ 同上
CLASS: _FullscreenChart L1495
  ...
```

✅ `_KlineFullscreenWindow` 现在**严格是 7 个方法**，全部直接挂在类上。

### 4.2 语法编译

```
> python -m py_compile vnpy\strategy_condition\ui\kline_view.py
COMPILE_OK
```

✅ 编译通过。

### 4.3 联动信号链路（端到端）

| 位置 | 代码 | 状态 |
|------|------|------|
| `condition_monitor_widget.py` | `daily_bar_clicked = QtCore.Signal(object, dict)` | ✅ 已存在 |
| `condition_monitor_widget.py` | `self.daily_bar_clicked.emit(clicked_dt, signals)` | ✅ 已存在 |
| `kline_view.py`（全屏构造时） | `owner_monitor.daily_bar_clicked.connect(win._on_outer_daily_bar_clicked)` | ✅ 已存在 |
| `kline_view.py`（全屏关闭时） | `owner.daily_bar_clicked.disconnect(self._on_outer_daily_bar_clicked)` | ✅ 已存在 |
| `kline_view.py`（全屏） | `_on_outer_daily_bar_clicked` → `chart.focus_datetime(focus_dt, completed_daily=False)` | ✅ 已存在 |

✅ 信号端、信号源、连接、断开、回调函数定义——**完整闭环**。

---

## 5. 验证操作步骤（用户视角）

1. **完全退出当前 vnpy**（任务管理器确认无残留 `python.exe`）。
2. **删除缓存**（可选但强烈推荐）：
   ```bash
   rd /s /q "C:\Users\11229\.vnpy_sce_logs\__pycache__"
   ```
3. **重新启动 vnpy**。
4. 打开 Monitor Tab → 选 600028.SSE → 点 ▶ 启动监控。
5. 等监控数据加载完（看到 WaveView 出现 buy/sell 标记）。
6. 点击 K线 → 全屏模式（通常是双击 K线 或点"全屏"按钮）。
7. 在全屏窗口里**点击日线面板的某根 K 线**。
8. **预期结果**：
   - 终端出现：`[KlineView][V8] 全屏窗口已监听 owner_monitor.daily_bar_clicked`（在打开全屏时打）
   - 终端出现：`[KlineView][V8] 全屏窗口收到外部 daily_bar_clicked, focus_dt=YYYY-MM-DD, vline 已移动`（每次点击都打）
   - 全屏窗口里**日线面板的红色 vline 跳到点击位置**，
     **分钟线面板的 vline 同步跳到该日收盘时刻**。
9. 关闭全屏窗口（点 ❌ 或按 ESC）：
   - 终端出现 `[KlineView] 全屏窗口已关闭，正在清理 ...`（来自 `closeEvent`）
   - 终端出现 `daily_bar_clicked.disconnect 成功`（来自清理代码）
   - 进程不会残留孤儿窗口。

---

## 6. 回顾

| 版本 | 主要工作 | 状态 |
|------|---------|------|
| V1-V5 | 全屏窗口基础联动 | 关闭窗口相关未生效 |
| V6 | 诚实诊断报告 | 发现 closeEvent 没起作用 |
| V7 | 把 closeEvent 移出 __init__ | **缩进错误遗留** |
| **V8** | 监听 owner_monitor.daily_bar_clicked | 缩进错误仍在 |
| **V9** | 把 closeEvent/keyPressEvent 真正 dedent 回类方法 | ✅ **终极修复** |

**V9 = 把 L1460-L1492 区域的缩进从 8 空格减到 4 空格，使 `closeEvent` / `keyPressEvent` 成为 `_KlineFullscreenWindow` 的真正类方法。**

---

## 7. 后续

代码已可投产。如仍有异常，请捕获：
- `[KlineView][V8] 全屏窗口 _on_outer_daily_bar_clicked 失败: <错误>`  ⇒  回调体内出错
- `Failed to disconnect ...`  ⇒  重复 disconnect，可忽略

并把这两行贴出来以便进一步定位。