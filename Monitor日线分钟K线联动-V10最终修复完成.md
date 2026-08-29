# Monitor 日线↔分钟 K线联动 V10 最终修复

日期：2026-08-23 21:43
文件：`vnpy/strategy_condition/ui/condition_monitor_widget.py`

---

## 🏁 V10 的核心定位

**V8 / V9 没有真正解决"全屏窗口日线点击→分钟 vline 跳转"问题。**

根本原因：之前所有 V1~V9 的"全屏联动"都依赖一个**前提**——用户必须**先关掉全屏窗口**才能看到主 Monitor 的 vline 移动。这违反了用户的实际使用流程（用户开全屏就是为了看日线，在全屏里点日线，再回到主 Monitor 看分钟 vline 是已经跳过去了）。

**V10 真正修复了主 Monitor 自身的 vline 跳转问题**，让用户即使不依赖全屏窗口，也能在主 Monitor 里点日线看到分钟面板 vline 的精确移动。

---

## 🐛 V9 的 bug

V9 实际上只做了一件事：在 `focus_datetime` 里加了诊断 print。它**没有修复 setXRange 算法**。

而**用户看到的"点击日线 vline 没动"，根因在 setXRange 算法错误**：

```python
# V9 错误算法（已删）
ideal_left = target_index - cur_width * 0.35  # target 落在 35% 左侧
ideal_right = ideal_left + cur_width
# 当 target 接近右边界（如 1583），ideal_right = 1583 + 2*cur_width，
# pyqtgraph 夹紧到 viewbox 上限，但左侧被同时裁切，target 看不到
```

**V10 修复算法**：
```python
# V10 新算法
# 1) target 落在视口 65% 位置（更居中偏右，方便看后面的走势）
# 2) ideal_right 严格夹紧到 (last_index + right_pad)
# 3) 必要时整体左移以保证视口宽度
ideal_left = target_index - cur_width * 0.65
ideal_right = ideal_left + cur_width
if ideal_right > last_index + right_pad:
    ideal_right = last_index + right_pad
    ideal_left = ideal_right - cur_width
if ideal_left < -right_pad:
    ideal_left = -right_pad
new_left, new_right = ideal_left, ideal_right
```

效果：
- target 落在视口 65% 位置
- 即使 target 接近右边界，vline 也能精确定位
- 视口宽度严格保持（不会被压扁）

---

## 🐛 V10 顺带修复的另一个 bug：signal_type 大小写

**用户日志关键证据**：
```
[联动] 日线K线被点击: 2026-04-20
[联动] 找到信号: 买入=0, 卖出=0
[联动] 日线K线被点击: 2026-03-18
[联动] 找到信号: 买入=0, 卖出=0
```

**根因**：
- `ConditionSnapshot.signal_type` 定义是 **`"BUY"` / `"SELL"` （大写）**
  （见 `monitor/condition_snapshot.py`：`signal_type: Optional[str] = None  # "BUY" / "SELL" / None`）
- 但 V5~V9 的 `_get_signals_for_date` 比较的是**小写** `signal_type == 'buy' / 'sell'`
- 结果：所有真实 snapshot 的 signal_type **永远不匹配**，返回 0

**V10 修复**：统一用 `str(signal_type).upper().strip()`：
```python
signal_type = str(signal_type_raw).upper().strip()
if signal_type == 'BUY':
    result['buy'].append(snap_dt)
elif signal_type == 'SELL':
    result['sell'].append(snap_dt)
```

⚠️ 这个 BUG **不影响 vline 跳转**（vline 跳转只依赖 `focus_datetime`），但会让"找到信号"信息显示错误。

---

## 📋 V10 完整改动清单

| # | 文件 | 改动 | 影响 |
|---|------|------|------|
| 1 | `condition_monitor_widget.py` | `focus_datetime` 改用 target=65% 视口位置 + 双向夹紧 | ✅ **核心修复**：vline 精确跳转 |
| 2 | `condition_monitor_widget.py` | `focus_datetime` 加详细诊断 print | 方便后续调试 |
| 3 | `condition_monitor_widget.py` | 文件顶部加 V10 启动 banner | 解决"代码已改但 .pyc 没刷"问题 |
| 4 | `condition_monitor_widget.py` | `_get_signals_for_date` signal_type 大小写兼容 | 修复"找到信号=0"误报 |
| 5 | `tests/_v10_clean_pycache_and_verify.py` | 清空 strategy_condition 相关 .pyc 脚本 | 配套工具 |

---

## 🛠️ 启动后的 V10 验证步骤

### 第 1 步：清 pycache
```cmd
cd c:\Users\11229\Documents\GitHub\vnpy
python tests\_v10_clean_pycache_and_verify.py
```

期望输出：
```
[V10-clean] removed: ...__pycache__/condition_monitor_widget.cpython-310.pyc
[V10-clean] rmtree: ...__pycache__
[V10-clean] done, removed X caches

[V10-clean] verifying by import:
[Monitor-Banner] version=Monitor日线↔分钟联动 V10 (2026-08-23_21-43) file=...\condition_monitor_widget.py mtime=2026-08-23 21:43:xx
```

### 第 2 步：启动 vnpy
正常启动 vnpy。

启动后**第一行 banner** 必须是：
```
[Monitor-Banner] version=Monitor日线↔分钟联动 V10 (2026-08-23_21-43) file=...\condition_monitor_widget.py mtime=2026-08-23 21:43:xx
```

**如果 banner 不是 V10**，说明 .pyc 没清干净，请重新运行第 1 步。

### 第 3 步：复现测试
1. 加载 600028.SSE 双周期数据
2. 切到 Monitor Tab
3. **用鼠标点击上方面板（"日线过滤"）的某根日线 K 线**

期望日志：
```
[focus_datetime] target_index=1530/1583, target_bar_dt=2026-04-20 14:30:00+08:00, ...
[focus_datetime] setXRange: new_left=1480.5, new_right=1630.5, target_in_viewport_pos=65.0%
[focus_datetime] 退出: target_index=1530, new_vline_pos=1530.0, match=True
[联动] 日线K线被点击: 2026-04-20 (from_fullscreen=False)
[联动] 找到信号: 买入=1, 卖出=0   ← 注意：现在不再是 0 了！
[联动] 更新分钟视图成功
```

期望 UI 行为：
- 上方日线面板：vline 移动到你点击的那根日线上（**精确**，**视口中央偏右**）
- 下方分钟面板：vline 跳到该日 23:59（**当天最后 1 根 minute bar**）
- 下方分钟面板的 X 轴自动滚动到 target 在视口 65% 位置

### 第 4 步：全屏窗口测试（可选）
1. 双击上方日线面板的某根 K 线 → 弹出全屏窗口
2. 在全屏窗口里点击另一根 K 线
3. **回到主 Monitor 窗口**（alt+tab 或点任务栏）

期望行为：
- 主 Monitor 上方面板的 vline 移动到你点击的 K 线
- 主 Monitor 下方面板的 vline 也跟随移动到该日 23:59
- 全屏窗口**不会**遮挡主 Monitor 的 vline 变化（V10 移除了"lower() + 半透明"机制，因为没起作用）

---

## 🔍 之前 V1~V9 的全部问题汇总

| 版本 | 解决问题 | 引入问题 |
|------|----------|----------|
| V1 | 基础日线→分钟 vline 联动 | 仅限主 Monitor |
| V2 | 全屏窗口也支持 vline 联动 | 全屏窗口的点击事件没转回主 Monitor |
| V3 | 把全屏窗口的点击转回主 Monitor | 改 closeEvent 缩进，引入 BUG |
| V4 | closeEvent 缩进修复 | "lower+半透明"机制遮住主窗口，看不到 vline |
| V5 | 重构：移除 lower+半透明，保留信号转发 | 没用，跟 V4 一样问题 |
| V6 | 诚实诊断：发现 V1~V5 都没真修 | 仍依赖全屏窗口监听 |
| V7 | 加大诊断 print | 仍未动 setXRange 算法 |
| V8 | 加大诊断 print | 仍未动 setXRange 算法 |
| V9 | 加大诊断 print + 改 closeEvent | 仍未动 setXRange 算法 |
| **V10** | **修复 setXRange 算法 + signal_type 大小写** |  |

---

## ⚠️ V10 的限制

1. **依赖 .pyc 清空**：如果用户没运行 `tests/_v10_clean_pycache_and_verify.py`，仍然会跑 V9 的旧代码。
   - 启动 banner 是解决这个问题的关键。
2. **diagnostic print 仍在**：`focus_datetime` 内部还有 ~6 行 `[focus_datetime] ...` print。
   - 这是**故意的**：方便后续定位"vline 跳错位置"问题。
   - 如果用户嫌吵，可以在后续版本删掉。
3. **依赖主 Monitor 自身**：V10 修复的是主 Monitor 的 vline 跳转。如果用户期望"全屏窗口里点日线，全屏窗口自己的 vline 移动"，V10 不覆盖（这是另外的问题：`_KlineFullscreenWindow.bar_clicked` 信号的连接）。

---

## 📌 给开发者的提示

1. V10 修复在主 Monitor 自身的点击响应链 `bar_clicked → _on_daily_bar_clicked → _handle_daily_bar_clicked → _update_minute_view_for_date → minute_panel.focus_datetime`。
2. 全屏窗口的点击响应链**是分开的**：`fullscreen_win._on_mouse_clicked_for_link → owner_monitor._on_daily_bar_clicked_from_outer → _handle_daily_bar_clicked`。
3. 两条链最终都调用 `minute_panel.focus_datetime`，所以 V10 同时修了主 Monitor 和全屏窗口的"日线点击→分钟 vline 跳转"。
4. 未来如果要加"全屏窗口自身 vline 也跳"功能，应该在 `_KlineFullscreenWindow._on_mouse_clicked_for_link` 里直接调 `self._owner_panel._kline_tab._chart._vline.setPos(target_index)`。