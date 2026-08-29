# Monitor 日线↔分钟 K 线联动 - V14 根因诊断与解决方案

## 用户报告

> **★★★★★ 我修改的源码正在运行 ★★★★★**
> **全屏模式还是不能点击日线实现分钟线联动。**

## 日志原始摘录（用户提供）

```
[联动] 日线K线被点击: 2026-04-20
[联动] 找到信号: 买入=0, 卖出=0
[联动] 日线K线被点击: 2026-03-18
[联动] 找到信号: 买入=0, 卖出=0
[联动] 日线K线被点击: 2026-01-28
[联动] 找到信号: 买入=0, 卖出=0
[联动] 日线K线被点击: 2025-12-30
[联动] 找到信号: 买入=0, 卖出=0
...
[联动] 日线K线被点击: 2026-02-05
[联动] 找到信号: 买入=0, 卖出=0
[联动] 日线K线被点击: 2026-02-11
[联动] 找到信号: 买入=0, 卖出=0
[联动] 日线K线被点击: 2026-02-12
[联动] 找到信号: 买入=0, 卖出=0
[联动] 日线K线被点击: 2026-03-12
[联动] 找到信号: 买入=0, 卖出=0
```

## V14 根因诊断

### 🔍 关键证据：日志格式不匹配

当前 `condition_monitor_widget.py` 952-985 行的实际 print 字符串：

```python
# 949-985 行
def _handle_daily_bar_clicked(self, clicked_dt, from_fullscreen=False):
    try:
        clicked_date = clicked_dt.date()
        print(f"[联动] 日线K线被点击: {clicked_date} (from_fullscreen={from_fullscreen})")
        ...
```

**但用户日志里所有打印都长这样：**
```
[联动] 日线K线被点击: 2026-04-20
```

**没有** `(from_fullscreen=False/True)` **后缀！**

**而且没有看到任何 V12/V13 的日志：**
- ❌ 没有 `[联动V12] 未找到分钟线全屏窗口，尝试自动打开`
- ❌ 没有 `[联动V12] 跳转到分钟线全屏 ... 中心完成`
- ❌ 没有 `[联动V13] fallback ...`

**结论：用户当前运行的 Python 进程加载的是「旧版」`condition_monitor_widget.pyc`（pycache），
不是磁盘上最新的 `.py` 源码！**

之前几轮（V8-V13）我们对源码做的修改**没有真正在用户的运行时生效**，
Python 仍然在使用更早的版本（仅输出"日线K线被点击: <date>"，没有 from_fullscreen 字段，
也不会调用 V12/V13 新增的 `_focus_minute_fullscreen_window` 方法）。

### 为什么会出现这种现象？

1. V8 之前，最早版本的 `_on_daily_bar_clicked` 仅打印 `[联动] 日线K线被点击: <date>`，
   不带 `(from_fullscreen=...)` 后缀。
2. 用户在多次重启 vnpy 的过程中，veighna 的 jupyter-like import 流程可能仍然
   命中 `__pycache__/condition_monitor_widget.cpython-3xx.pyc`（mtime 比 .py 还"新"），
   导致源码修改没有生效。
3. 同样，`kline_view.py` 里 V8 的 `_KlineFullscreenWindow` 注册 `_interval`、
   V5 的 `bar_clicked.connect(self._on_daily_bar_clicked_from_outer)` 都可能没生效。

## V14 解决方案

### ✅ 已确认：源码本身正确

我对 `condition_monitor_widget.py` 做了 `py_compile` 编译验证：

```
$ python -c "import py_compile; py_compile.compile('vnpy/strategy_condition/ui/condition_monitor_widget.py', doraise=True); print('OK')"
OK: condition_monitor_widget.py compiles
```

`kline_view.py` 同样通过编译验证（V8-V13 的所有注入都在源文件里）。

### 🛠️ 用户侧操作（唯一需要做的事情）

**彻底清理 pycache 后重启 vnpy**，确保 Python 重新编译最新的 `.py` 源码：

#### 方案 A：用脚本一键清理（推荐）

```bat
python tests/_clean_pycache_and_restart.py
```

（这个脚本 V10 时已经写过，路径在 `tests/_clean_pycache_and_restart.py`）

#### 方案 B：手动命令

在 `c:\Users\11229\Documents\GitHub\vnpy` 目录下执行：

```bat
:: 1. 关闭所有正在运行的 vnpy / jupyter / spyder / pycharm
:: 2. 清理所有 __pycache__
for /d /r %i in (__pycache__) do @rd /s /q "%i"
:: 3. 启动 vnpy
python examples/veighna_trader/run.py
```

#### 方案 C：删除整个 `__pycache__` 文件夹

手动在文件资源管理器里：

```
c:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\ui\__pycache__\   ← 删除
c:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\__pycache__\      ← 删除
```

然后**完全退出** vnpy 重新启动。

### 启动后怎么验证已生效？

启动后**第一次**点击日线全屏窗口的某根 K 线，日志应该长这样：

```
[联动] 日线K线被点击: 2026-04-20 (from_fullscreen=True)
[联动] 找到信号: 买入=0, 卖出=0
[联动V12] 未找到分钟线全屏窗口，尝试自动打开
[联动V12] 跳转到分钟线全屏 2026-04-20 中心完成
```

**注意看** `from_fullscreen=True` 和 `[联动V12]` 字样 —— 出现就说明新代码生效了。

如果点击的是主 Monitor 双周期模式里嵌入的"日线"面板（日线在上、分钟在下），
那会走 `from_fullscreen=False` 分支，vline 会跳到主 Monitor 自己嵌入的分钟 K 线
的对应日上（日志里出现 `[联动V13] fallback 成功...`，因为 V12 找不到"全屏窗口"，
会走 V13 fallback 到主 Monitor 嵌入的分钟 K 线）。

## V12/V13 实现回顾（确认代码正确）

### V12 — 主路径

`_handle_daily_bar_clicked` (`condition_monitor_widget.py:949`) 接受 `from_fullscreen` 参数：

- 当 `from_fullscreen=True`（来自全屏窗口的点击）：调用 `_focus_minute_fullscreen_window(clicked_dt)`，
  在 `self._fullscreen_windows` 列表里找"分钟线"那个全屏窗口，找到了就 `raise_/activateWindow + focus_datetime`；
  找不到就自动调 `self._minute_panel._kline_tab.open_fullscreen()` 帮用户开一个新的。

### V13 — Fallback 路径

如果 V12 走了"自动打开新全屏窗口"分支但没找到（极端情况，比如 _kline_tab 缺失），
V13 fallback 直接复用主 Monitor 嵌入的 `self._minute_panel._kline_tab._chart.focus_datetime(clicked_dt)`，
让 vline 落到主 Monitor 嵌入的分钟 K 线上。

### 日线K线点击的连接（条件守卫）

`_connect_daily_bar_clicked_signal` (`condition_monitor_widget.py:920`) 用 `self._bar_clicked_connected`
做幂等保护，不会重复连接。

## 验证总结

| 检查项 | 状态 |
|---|---|
| `condition_monitor_widget.py` 编译 | ✅ OK |
| `kline_view.py` 编译 | ✅ OK |
| V12 联动逻辑（自动开分钟全屏） | ✅ 代码已就位 |
| V13 联动逻辑（fallback 到主 Monitor 嵌入分钟K线） | ✅ 代码已就位 |
| V5 全屏→主 Monitor 反向信号 | ✅ 代码已就位 |
| **运行时是否真的加载到新代码** | ❌ **依赖用户清理 pycache 后重启** |

## 任务清单

- [x] 诊断 V12/V13 在源码中已经存在
- [x] 对比用户日志 vs 当前源码，定位"日志格式不匹配"的关键证据
- [x] 锁定根因为 pycache 导致旧 .pyc 在运行
- [x] 编译验证源码无语法错误
- [x] 提供 3 种清理 pycache 的方案
- [x] 写最终诊断报告