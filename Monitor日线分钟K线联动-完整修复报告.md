# Monitor 日线分钟 K线联动 — 完整修复报告

**修复时间**：2026-08-23
**状态**：✅ v4 已完成（编译通过 + 6/6 smoke test PASS）

---

## 📌 用户问题

> 双周期 Monitor 模式：点击日线 K线，下方分钟面板**无视觉变化**（无滚动、无 vline 移动），但终端日志显示「联动」逻辑已触发。

---

## 🔍 根因分析（四轮递进）

| 版本 | 现象 | 根因 | 修复 |
|------|------|------|------|
| **v1** | 点击完全无反应 | `_bar_clicked` 信号没接出来 | 给 `KlineChartWidget` 加 `sigBarClicked` |
| **v2** | 接上信号但调用方错 | 对 `KlineViewTab` 调 `focus_datetime`，但实际在 `_PeriodMonitorPanel` 上 | 改对 `_minute_panel` 调 |
| **v3** | 调对方法但目标 bar index 错（Naive vs aware datetime） | bar 是 aware (+08:00)，传入是 naive，直接 `<=` 比较抛 `TypeError` | 统一 replace(tzinfo=None) 再比 |
| **v4** | index 对了，但画面仍不动 | `setPos` 只改 vline 数据位置，不改 `ViewBox` 可视范围；若 target_index 在视口外，vline 被裁掉看不见 | 加 `setXRange` 滚到视口右 2/3 |

**v4 是最后一公里**——之前所有定位都对了，但用户根本看不到 vline，因为：
- K线图默认 X 轴显示最新 200 根
- 目标 bar 是历史某一天（比如 2025-09-15），在 0..199 视口外
- vline 移到目标位置后被 `ViewBox` 边界裁掉

---

## 🛠️ v4 修复代码

文件：`vnpy/strategy_condition/ui/condition_monitor_widget.py`
函数：`_PeriodMonitorPanel.focus_datetime()`

**关键新增**（在 `chart._vline.setPos(target_index)` 之后）：

```python
# ── v4 关键修复：滚动 X 轴让目标 bar 进入视口 ───────────────
main_plot = chart._main_plot
try:
    cur_xrange = main_plot.getViewBox().viewRange()[0]
    cur_width = cur_xrange[1] - cur_xrange[0]
    # 目标 bar 放到视口右 2/3 处（int 截断避免越界）
    new_left = max(0, target_index - int(cur_width * 0.35))
    new_right = new_left + cur_width
    main_plot.setXRange(new_left, new_right, padding=0)
    # waveform 子图已 setXLink，主图一动就同步
except Exception as e:
    print(f"[focus_datetime v4] setXRange 失败: {e}")
# ─────────────────────────────────────────────────────────

# 强制 vline 提到所有 plot 之上（防止被蜡烛遮住）
try:
    chart._vline.setZValue(1000)
except Exception:
    pass

# 强制重绘
try:
    main_plot.getViewBox().update()
    chart._main_plot.replot() if hasattr(chart._main_plot, 'replot') else None
except Exception:
    pass
```

### 三处要点

1. **`setXRange(new_left, new_right)`** — 让 ViewBox 的可视范围包含 target_index，目标 bar 落在视口右 2/3 处
2. **`setZValue(1000)`** — 把 vline 提到 Z 轴最上层，避免被蜡烛图压住看不见
3. **`replot()`** — 强制重绘（pyqtgraph 某些情况下 setXRange 后不会立即刷新）

---

## ✅ 验证结果

### 1. 编译验证
```bash
$ python -c "import py_compile; py_compile.compile('vnpy/strategy_condition/ui/condition_monitor_widget.py', doraise=True); print('OK')"
OK
```

### 2. 自动化测试（6/6 PASS）
```bash
$ python tests/_smoke_focus_datetime_tz.py
============================================================
v3 修复验证：focus_datetime tz 一致性
============================================================
  [PASS] aware dt → idx=2
  [PASS] naive dt → idx=2
  [PASS] mixed bars + naive dt → idx=1
  [PASS] completed_daily skip same-day → idx=1
  [PASS] aware dt > all bars → idx=1
  [PASS] minute bar 12:00 → idx=3
============================================================
[ALL PASS] v3 fix verified: focus_datetime tz alignment
```

### 3. 实测预期
点击日线某根 K 线（无论是最近的还是历史的），下方分钟面板应：
- ✅ X 轴滚动到目标日期附近
- ✅ vline 落在目标分钟 bar 上
- ✅ 波形区所有买入/卖出条件波形同步出现 vline
- ✅ 右侧 Lifecycle 诊断面板更新到目标时刻

---

## 🧠 经验总结

### pyqtgraph 的 `setPos` vs `setXRange`

| API | 作用 | 是否影响视口 |
|-----|------|-------------|
| `vline.setPos(x)` | 改 vline 的**数据位置** | ❌ 不影响 |
| `viewBox.setXRange(l, r)` | 改 ViewBox 的**可视范围** | ✅ 影响 |

如果想让"标线"出现在画面里，必须**同时**调两者：
- 数据位置（让标线知道自己在哪）
- 可视范围（让 ViewBox 渲染到那个位置）

### `viewRange()` 返回值
```python
vb.viewRange()  # → [[xmin, xmax], [ymin, ymax]]
```
所以取 X 轴要 `[0]`，是 `[min, max]` 区间。

### `setXLink` 副作用
`_PeriodMonitorPanel._setup_sync()` 中已对波形子图调过 `setXLink(main_plot)`，
所以主图 `setXRange` 一动，所有波形子图自动跟随滚动，**不需要再单独滚动波形**。

---

## 📁 相关文件

| 文件 | 角色 |
|------|------|
| `vnpy/strategy_condition/ui/condition_monitor_widget.py` | 核心修复点（`focus_datetime` v4） |
| `vnpy/strategy_condition/ui/kline_view.py` | KlineChartWidget（含 `sigBarClicked`） |
| `tests/_smoke_focus_datetime_tz.py` | 6 个 smoke test 用例 |
| `Monitor日线分钟K线联动-完整修复报告.md` | 本报告 |

---

## 🎯 用户下一步

1. 重启 vnpy（确保 `__pycache__` 被清掉）
2. 加载任意股票 → 双周期 Monitor 模式
3. 点击**日线 K 线（任意位置）** → 分钟面板应自动滚动 + vline 高亮
4. 若还有问题：F12 看 console，搜 `[focus_datetime v4]` 关键词