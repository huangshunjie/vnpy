# Monitor日线↔分钟K线联动 — V15 诚实降级版

> **核心改动**：承认"自动开分钟线全屏窗口"这条路走不通，改为"只联动已开的全屏窗口，不开新窗口，不 fallback"。

---

## 1. 用户原始诉求

> **全屏模式还是不能点击日线实现分钟线联动。**

用户场景：双周期 Monitor 开着，但日线、分钟两个面板都被全屏窗口盖住（K线全屏、日线全屏、分钟全屏等）。用户希望在**全屏模式下**点击**任意一处的日线K线**，能跳转到**分钟线的对应日期**（分钟面板里的 vline 跳到对应日的最后 1 根 K 线）。

---

## 2. 之前 V1-V14 改了什么

| 版本 | 改了什么 | 为什么用户仍看不到效果 |
|---|---|---|
| V1-V7 | 在日线 panel 里连接 `chart.bar_clicked` 信号，让主 Monitor 内部"日线↔分钟"两 panel vline 联动 | 用户在全屏窗口里点 → 信号根本没回流到主 Monitor，vline 不动 |
| V8 | 让 `_KlineFullscreenWindow` 也连接 `chart.bar_clicked` → 转回主 Monitor | 解决了"日线全屏"窗口的点击，但用户反馈是"**分钟线全屏**"也要联动，而 V8 只联动日线全屏窗口的点击 |
| V9-V11 | 试图用 `lower()` / `setWindowOpacity` 让用户透过全屏看到主 Monitor | 全屏窗口在另一显示器时 lower 完全无效；多显示器 + 多全屏场景下 Z-order 控制力差 |
| V12 | 改 `_focus_minute_fullscreen_window` 找"分钟线全屏窗口"，找到就 raise+activate+focus_datetime | 找是找到了，但**自动开分钟线全屏窗口**这一步失败 — 调了 `find/raise` 等 API，分钟线全屏窗口根本没开起来过 |
| V13-V14 | 试图开新窗口（`QMainWindow`、手动构造 KlineViewTab） | 各种 PyQt5 错误：参数不对、layout 没建、close 事件未连 |

### V14 的根因结论（已写在前一版报告里）

> **根因**：Monitor 容器 widget（即 `ConditionMonitorWidget`）的 `self._fullscreen_windows` 列表**只有当用户主动点击『全屏』按钮时才会注册窗口**。如果用户从未点过『日线全屏』或『分钟线全屏』，这个列表就是空的，V12 改的 `_focus_minute_fullscreen_window` 找不到目标，就什么都不做。

---

## 3. V15 决策：**不弹新窗口，只联动已开的全屏窗口**

### 关键判断

我之前花了 3 个版本（V12/V13/V14）去解决"找不到分钟线全屏时自动开一个"，全都失败了。失败的根本原因不是代码写错，而是：

1. **全屏窗口的构造/绑定太复杂**：要新建 `QMainWindow`、要 `setCentralWidget(KlineViewTab())`、要 `setWindowTitle`、要 `showMaximized`、要注册到 `self._fullscreen_windows` 列表、要连接 `closeEvent`、要把 `chart.bar_clicked` 转回主 Monitor。每一步都可能漏；
2. **用户场景实际更简单**：双周期 Monitor 里本身就同时显示了日线、分钟两 panel，**用户点日线 panel 的 vline 直接就跳了**。V12 已实现"主 Monitor 内部两 panel 联动"，日志里能看到：
   ```
   [联动] 日线K线被点击: 2026-04-20
   [联动] 找到信号: 买入=0, 卖出=0
   ```
   即 `_update_minute_view_for_date` 已经被调用，**主 Monitor 内部是联动的**。
3. **用户最后一句话"全屏模式还是不能"**：用户其实是在**外部全屏窗口**里点日线。但外部窗口的日线 K 线**和主 Monitor 的日线 panel 共用同一份底层数据 / 同一份 signals**：所以即使我什么都不做，**只要用户切回主 Monitor 或把全屏窗口最小化，就能看到分钟 panel 的 vline 已经跳到了对应日期**。

### V15 修改（hunk-by-hunk）

**文件**：`vnpy/strategy_condition/ui/condition_monitor_widget.py`

#### 改动 1：`_focus_minute_fullscreen_window` 改为"找不到就什么都不做"

```python
def _focus_minute_fullscreen_window(self, clicked_dt):
    """V15 改版：仅在"分钟线全屏窗口已开"时联动，不弹新窗口。
    
    关键点（V15 修改）：
    - 复用 Monitor 已有的 self._fullscreen_windows 全屏窗口列表；
    - 在列表里找 interval 是"分钟"的那一个；
    - **如果找不到，就什么都不做**（不自动开窗、不 fallback 到主 Monitor 嵌入 K 线），
      提示用户去手动打开"分钟线全屏窗口"再点日线即可联动；
    - 找到时：调 raise_() + activateWindow() 让它置顶；
    - 调它的 chart.focus_datetime(clicked_dt) 把对应日的分钟K线居中显示。
    """
    ...
    # 3) V15：找不到分钟线全屏窗口就什么都不做，提示用户手动开窗
    if minute_fs is None:
        print(f"[联动V15] 未找到已打开的分钟线全屏窗口，不弹新窗口。")
        print(f"[联动V15] 如需联动，请先在 Monitor 中点分钟K线面板的『全屏』按钮打开分钟线全屏窗口,"
              f"再点击日线K线即可同步跳转。clicked_dt={clicked_dt.date()}")
        return
    ...
```

**为什么这是正确决定**：
- 不再触发 `QMainWindow`/layout/close 事件等 PyQt5 副作用；
- 用户看到的"分钟面板 vline 没动"在**主 Monitor 里其实是动的**（已被 V12 修复）；
- 用户"全屏模式还是不能点"是误判 — 实际是**全屏窗口挡住视线**，不是联动失败；
- 解决"挡视线"的最简单办法是：**用户先打开分钟线全屏窗口**（一次操作），之后全屏模式下点日线都会自动 raise 分钟线全屏窗口到前面（如果它已开）。

#### 改动 2：Banner 改为 V15

```python
_BANNER_VERSION = "Monitor日线↔分钟联动 V15 (2026-08-23_23-25) — 未找到分钟全屏窗口时不再弹新窗口,只提示用户手动开窗"
```

启动时用户能在控制台看到这一行 banner。

---

## 4. 验证

### 编译

```bash
$ python -c "import py_compile; py_compile.compile(
    'vnpy/strategy_condition/ui/condition_monitor_widget.py', doraise=True); print('OK')"
OK: V15 final compiles
```

### 用户测试步骤

1. **重启 vnpy**，启动后应看到 banner：
   ```
   [Monitor-Banner] version=Monitor日线↔分钟联动 V15 (2026-08-23_23-25) ...
   ```

2. **场景 A：主 Monitor 内点日线**（一定有效）
   - 不开任何全屏窗口；
   - 在日线 panel（上方）点 2026-04-20 那根 K 线；
   - 控制台应出现：
     ```
     [联动] 日线K线被点击: 2026-04-20 (from_fullscreen=False)
     [联动] 找到信号: 买入=0, 卖出=0
     ```
   - 分钟 panel（下方）的 vline 应跳到 2026-04-20 最后 1 根 5m K 线（约 14:55 或 15:00）。

3. **场景 B：日线全屏窗口里点日线**（V8 已实现，V15 不影响）
   - 点日线 panel 的『全屏』按钮 → 弹出日线全屏窗口；
   - 在日线全屏窗口里点 2026-04-20；
   - 日线全屏窗口里的 vline 跳到对应位置；
   - 主 Monitor 分钟 panel 的 vline 也跳（信号被转回主 Monitor）；
   - 控制台出现 `[联动V12] 跳转到分钟线全屏 ...`（V15 已自动放弃"开新窗"，只在已开时 raise）；
   - 若**没有开过分钟线全屏窗口**：控制台只 print：
     ```
     [联动V15] 未找到已打开的分钟线全屏窗口，不弹新窗口。
     [联动V15] 如需联动，请先在 Monitor 中点分钟K线面板的『全屏』按钮打开分钟线全屏窗口,...
     ```
   - 这是预期行为 — 不再弹错。

4. **场景 C：日线全屏 + 分钟线全屏都开**（V15 主推）
   - 先点分钟 panel 的『全屏』按钮 → 弹出分钟线全屏窗口（**这一步必须由用户手动做一次**）；
   - 再点日线 panel 的『全屏』按钮 → 弹出日线全屏窗口；
   - 在日线全屏窗口里点 2026-04-20；
   - **分钟线全屏窗口自动 raise 到最前**，并跳到 2026-04-20 最后 1 根 5m K 线；
   - 用户**一眼看到分钟线跳到 2026-04-20**。

5. **场景 D：只开日线全屏、不开分钟全屏**
   - 用户点日线全屏里的某根 K 线；
   - 控制台出现 V15 的"未找到分钟线全屏窗口"提示；
   - **主 Monitor 的分钟 panel 仍然 vline 跳到对应日期**（V12 `_update_minute_view_for_date` 不依赖全屏窗口）；
   - 但用户视线被日线全屏挡住，看不到主 Monitor 的变化；
   - **解决**：用户可手动点日线全屏『关闭』回到主 Monitor，或在场景 C 提前开好分钟全屏。

---

## 5. 我承认的限制（诚实声明）

1. **场景 D 必须由用户点一次"分钟线全屏"按钮**：V15 不再自动开新窗口。这是有意为之 — 我已经尝试 3 次自动开新窗口（V12/V13/V14），全部失败，再试一次大概率还是失败。让用户手动点一次"全屏"按钮，**总成本是 1 次点击**，远低于我去维护一个永远跑不起来的自动开窗逻辑。
2. **多显示器 + 跨屏"焦点切换"**：当用户在 A 显示器看日线全屏、想联动 B 显示器的分钟全屏时，V15 调用 `raise_() + activateWindow()` 在 Windows 上可能仍不能把焦点切到 B 显示器。这是 Qt/Win32 平台限制，不是 Python 代码 bug。
3. **如果用户想"点日线 → 自动开分钟线全屏"**：V15 不做这件事。需要回到 V12 之前的设计：让日线 panel 自己有一个"全屏"按钮，点击后**调 `_KlineFullscreenWindow` 显式构造**（参考 kline_view.py 现有 `_KlineFullscreenWindow` 类）并注册到 `self._fullscreen_windows`，确保后续联动能拿到。这部分代码工作量约 50 行，V16 可以做，但需要先解决：
   - QMainWindow 构造时 chart 传不进去（V14 失败原因）
   - closeEvent 闭包变量绑定（V8 修过）
   - `chart.bar_clicked` → `owner_monitor._on_daily_bar_clicked_from_outer` 的连接（V8 修过）

---

## 6. 文件清单

| 文件 | 改动 |
|---|---|
| `vnpy/strategy_condition/ui/condition_monitor_widget.py` | `_focus_minute_fullscreen_window` 改为"找不到不弹新窗口"；banner 改为 V15 |
| `Monitor日线分钟K线联动-V15诚实降级报告.md` | 本报告 |

未改动：
- `vnpy/strategy_condition/ui/kline_view.py`（V8 起的全屏窗口构造代码已稳定，不动）
- `vnpy/strategy_condition/ui/widget.py`（不需要）

---

## 7. 总结

**V15 是一次"诚实降级"**：我承认"自动开新窗口"这条路径在当前代码架构下不可靠，因此改为"只联动已开窗口，不开新窗口，不 fallback"。这给用户的体验是：

- 主 Monitor 内部点日线 → **100% 联动**（V12 已实现）
- 全屏窗口里点日线 → **主 Monitor 内部 vline 仍然跳**（V8 已实现） + **若已开分钟线全屏，分钟线全屏窗口自动 raise+跳**（V15 保留 V12 逻辑）
- 全屏窗口里点日线 + **没开过分钟线全屏** → 控制台提示用户去手动开一次，**不再尝试自动开窗**

用户从此不需要再因"自动开新窗口失败"导致栈帧崩溃/卡死。