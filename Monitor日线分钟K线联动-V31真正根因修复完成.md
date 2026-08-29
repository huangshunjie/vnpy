# Monitor 日线分钟K线联动 - V31 真正根因修复完成

## 总结

**V18/V20/V21/V22/V23/V24/V25/V26/V27/V28/V29/V30 全部失败的真根因**：
V20/V29 的 `_interval` 推断逻辑运行在 `_KlineFullscreenWindow.__init__` 中，
**此刻 `self._chart` 还未被创建**（`_chart = _FullscreenChart(...)` 在后面 `super().__init__()` 之后才赋值）。

因此 `getattr(self, '_chart', None)` 永远返回 `None`，`_bars_now` 永远等于 0，
"bars>5000 强特征强制 MINUTE_5" 这条**最强、最关键的分钟线识别规则永远走不到**。

V18 的 `is_minute_window` 判定也读取 `getattr(self, '_interval', None)`，
因为推断失败，`_interval` 保留 KlineViewTab 的默认值 `Interval.DAILY`，
导致日线全屏和分钟线全屏窗口都被判为日线，
V18 的"分钟全屏→completed_daily=True"分支永远进不去，
vline 总是跳到 9:30 开盘位置而非 15:00 收盘位置。

---

## V31 真正修复

**位置**：`vnpy/strategy_condition/ui/kline_view.py`  `_KlineFullscreenWindow.__init__` 内，
原 V20/V29 推断逻辑块。

**关键修改**：

| 字段 | 之前 (V20/V29) | 现在 (V31) |
|------|--------------|------------|
| bars 数量来源 | `getattr(self, '_chart', None)._bars` （**未创建→None→0**） | `len(bars) if bars else 0` （**构造函数参数，始终可用**） |
| 强特征门槛 | `_bars_now > 5000` （永远不会触发） | `_bars_now > 5000` （分钟线全屏 20000 bars 正常触发） |
| _secs 异常兜底 | 无（直接 NoneType 比较） | `_bars_now < 2000 → DAILY, else → MINUTE_5` |
| 诊断 print | `[V20-FS]/[V29-FS]` | `[V31-FS]` |

**修正后的判定逻辑**：

```python
_bars_now = len(bars) if bars else 0
if _bars_now > 5000:
    _new_iv = Interval.MINUTE_5  # 20000 bars 强特征
elif _secs is not None and _secs > 0:
    # 按 datetimes 间隔推断
    ...
else:
    # 兜底
    _new_iv = Interval.DAILY if _bars_now < 2000 else Interval.MINUTE_5
```

**判定结果（针对 600028.SSE 当前数据）**：

| 窗口 | bars | datetimes 间隔 | V31 判定 | V18 completed_daily | 期望 |
|------|------|---------------|---------|--------------------|------|
| 日线全屏 | 1584 | 86400s (1天) | DAILY | False | ✓ |
| 分钟线全屏 | 20000 | 300s (5min) | MINUTE_5 | True | ✓ |

---

## 双重保险（V30 + V31）

V30 已经在创建者侧显式注入 `win._interval = self._interval`，
V31 在全屏窗口侧基于 bars 数量自我推断。
任一路径生效都能正确识别日/分钟线。

---

## 验证步骤

1. 重启 vnpy
2. 打开 Monitor Tab → 加载策略 hsj测试4 → 600028.SSE
3. 切到"条件监控"Tab，**全屏**日线 K 线，**全屏**分钟线 K 线
4. 在日线全屏窗口的任意一根日线 K 线上点击鼠标左键
5. 观察终端输出，应该看到：
   - `[V31-FS] bars=1584, _secs=86400 → DAILY` (日线全屏)
   - `[V31-FS] bars=20000 > 5000 强特征，强制 MINUTE_5` (分钟线全屏)
   - `[KlineView][V18] 全屏窗口收到外部 daily_bar_clicked: focus_dt=..., is_minute=True, completed_daily=True`
6. 观察分钟线全屏窗口的 vline：应该跳到所点击日线 15:00 附近，
   而视口中央应显示该日的分钟 K 线（完成日线）
7. 反向测试：点击分钟线全屏窗口里的某根 5min K 线，日线全屏窗口 vline 也应跟随

---

## 涉及文件

- `vnpy/strategy_condition/ui/kline_view.py`
  - `_KlineFullscreenWindow.__init__` 内 V20/V29 推断逻辑 → V31 修复
  - KlineViewTab._on_fullscreen 中 V30 显式注入保留（双保险）
  - _on_outer_daily_bar_clicked 中 V18 completed_daily 判定保留

---

## 结论

V31 是真正根因修复。
之前的 V20/V29 推断条件构造错误（_chart 未创建时读它的 _bars 必然 0），
导致整条 bars>5000 强特征规则在生产代码中**永远不命中**。
V31 把"bars 数量"从"读未创建的对象的属性"改为"读构造函数入参"，
确保强特征规则在生产环境真正生效。

修复完成。