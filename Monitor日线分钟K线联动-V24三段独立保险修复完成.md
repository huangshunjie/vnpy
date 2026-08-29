# Monitor 日线分钟 K 线联动 V24 三段独立保险修复完成

## 1. 问题描述

用户在 Monitor 中：
1. 打开"日线全屏"窗口
2. 打开"分钟线全屏"窗口
3. 单击日线全屏窗口上的任意 K 线
4. **期望**：分钟线全屏窗口的 vline 自动跳到该日线对应日期的中间
5. **实际**：V1-V23 反复修复后仍不生效

## 2. 根因分析

V1-V23 反复失败的核心：`_KlineFullscreenWindow._interval` 在某些代码路径下被错误设置成 `DAILY`，导致：

- V15 严格匹配（`iv in (MINUTE, MINUTE_5, ...)`）失败
- V23 负向判断（`iv not in (DAILY, WEEKLY, MONTHLY)`）也失败

`_interval` 被错误推断的具体路径：
1. `KlineViewTab._interval` 默认值是 `DAILY`（kline_view.py 早期定义）
2. `KlineViewTab._on_fullscreen` 创建全屏窗口时把 `self._interval` 透传给 `win._interval`
3. 即使后面 V20 加了"用 datetimes 间隔反推 _interval"，但 datetimes 可能为 None 或不可用
4. 结果：分钟线全屏窗口的 `_interval` 仍可能是 `DAILY` → 负向判断也认不出来

## 3. V24 方案：三段独立保险

V24 不再"看 _interval"，而是**从三个独立维度**判断"哪个全屏窗口是分钟线"：

```
路径 A：_interval 负向判断（V23 保留）
  → 如果 _interval 正确（不是 DAILY），直接命中
  → 输出：[联动V24] 路径A命中

路径 B：bars 实际间隔反推（V24 新增）
  → 取 _chart._bars[0].datetime 和 _chart._bars[1].datetime 的 gap
  → gap < 半天（43200s）→ 一定是分钟线
  → 输出：[联动V24] 路径B命中 bars=X gap=Ys

路径 C：bars 数量兜底（V24 新增）
  → 日线 1584 根 vs 分钟线 20000 根，bar 数差异巨大
  → bars 数量最多的全屏窗口（>1000）→ 视为分钟线
  → 输出：[联动V24] 路径C兜底命中 bars=X（最多）
```

**三段独立可验证**：每条路径都有独立 print 输出，调试时贴 banner 就能立刻定位走的是哪条、哪条失败。

## 4. 改动清单

| # | 文件 | 改动 | 目的 |
|---|---|---|---|
| 1 | `condition_monitor_widget.py` | banner 升级 V23 → V24 | 标识当前版本 |
| 2 | `condition_monitor_widget.py` | 重写 `_focus_minute_fullscreen_window`（~95 行） | 三段独立保险 A/B/C |
| 3 | `kline_view.py` | `_KlineFullscreenWindow.__init__` 追加 V24 bars 间隔 fallback（~40 行） | 在 V20 推断失败时再次兜底 |
| 4 | `kline_view.py` | `_on_outer_daily_bar_clicked` 加 debug print | 便于定位信号是否被全屏窗口收到 |

**未改动**（保持稳定）：
- `daily_bar_clicked` 信号定义与连接（V8 路径）
- `_handle_daily_bar_clicked` 主流程（V16）
- `_dispatch_to_fullscreen_windows`（V17）
- `focus_datetime` 实现（V22）
- 全屏窗口注册到 `_fullscreen_windows` 列表（V5）

## 5. 代码关键片段

### 5.1 `_focus_minute_fullscreen_window`（V24 三段保险）

```python
def _focus_minute_fullscreen_window(self, clicked_dt):
    """V24 三段独立保险：日线全屏 → 分钟线全屏跳转。"""
    try:
        from vnpy.trader.constant import Interval
        fullscreen_windows = list(getattr(self, '_fullscreen_windows', []) or [])
        if not fullscreen_windows:
            print(f"[联动V24] 没有任何已注册全屏窗口")
            return
        
        # 路径A：V23 负向判断
        minute_fs_A = None
        for w in fullscreen_windows:
            iv = getattr(w, '_interval', None)
            if iv is None: continue
            if iv in (Interval.DAILY, Interval.WEEKLY, Interval.MONTHLY): continue
            minute_fs_A = w
            print(f"[联动V24] 路径A命中: {type(w).__name__}._interval={iv}")
            break
        
        # 路径B：V24 新增 - bars 间隔反推
        minute_fs_B = None
        if minute_fs_A is None:
            for w in fullscreen_windows:
                w_chart = getattr(w, '_chart', None)
                bars = getattr(w_chart, '_bars', None) if w_chart else None
                if not bars or len(bars) < 2: continue
                b0_dt = getattr(bars[0], 'datetime', None)
                b1_dt = getattr(bars[1], 'datetime', None)
                if b0_dt is None or b1_dt is None: continue
                try: gap = (b1_dt - b0_dt).total_seconds()
                except Exception: continue
                if gap < 86400 * 0.5:
                    minute_fs_B = w
                    print(f"[联动V24] 路径B命中: bars={len(bars)} gap={gap:.0f}s")
                    break
        
        # 路径C：V24 新增 - bars 数量兜底
        minute_fs_C = None
        if minute_fs_A is None and minute_fs_B is None:
            max_bars = -1
            for w in fullscreen_windows:
                w_chart = getattr(w, '_chart', None)
                bars = getattr(w_chart, '_bars', None) if w_chart else None
                if not bars: continue
                n = len(bars)
                if n > max_bars:
                    max_bars = n
                    minute_fs_C = w
            if minute_fs_C is not None and max_bars > 1000:
                print(f"[联动V24] 路径C兜底命中: bars={max_bars}（最多）")
        
        # A > B > C 选择最终目标
        minute_fs = minute_fs_A or minute_fs_B or minute_fs_C
        if minute_fs is None:
            print(f"[联动V24] A/B/C 三条路径都没找到分钟线全屏窗口，放弃跳转")
            return
        
        # 置顶 + focus_datetime
        ...
```

### 5.2 `_KlineFullscreenWindow.__init__` V24 bars 间隔 fallback

```python
# V24 新增：datetimes 不可用时，fallback 到 bars 间隔反推
try:
    from vnpy.trader.constant import Interval as _Iv
    cur_iv = getattr(self, '_interval', None)
    cur_iv_ok = cur_iv is not None and cur_iv not in (_Iv.DAILY, _Iv.WEEKLY, _Iv.MONTHLY)
    if not cur_iv_ok:
        _chart_bars = None
        if hasattr(self, '_chart') and self._chart is not None:
            _chart_bars = getattr(self._chart, '_bars', None) or getattr(self._chart, '_kline_data', None)
        if _chart_bars and len(_chart_bars) >= 2:
            _b0 = _chart_bars[0]
            _b1 = _chart_bars[1]
            _b0_dt = getattr(_b0, 'datetime', None) or getattr(_b0, 'dt', None)
            _b1_dt = getattr(_b1, 'datetime', None) or getattr(_b1, 'dt', None)
            if _b0_dt is not None and _b1_dt is not None:
                try:
                    _bar_gap = (_b1_dt - _b0_dt).total_seconds()
                except Exception:
                    _bar_gap = 0
                if _bar_gap < 86400 * 0.5:
                    if _bar_gap <= 360:
                        self._interval = _Iv.MINUTE_5
                    elif _bar_gap <= 1200:
                        self._interval = _Iv.MINUTE_15
                    elif _bar_gap <= 4500:
                        self._interval = _Iv.HOUR_1
                    else:
                        self._interval = _Iv.MINUTE_5
                    print(f'[V24-FS] bars 间隔反推 _interval: '
                          f'bars={len(_chart_bars)} gap={_bar_gap:.0f}s -> {self._interval}')
except Exception as _e_v24:
    print(f'[V24-FS] bars 间隔反推失败: {_e_v24}')
```

## 6. 验证步骤

1. 启动 VNPY，确认 banner 显示 **"V24"**
2. 打开 Monitor → 加载双周期数据
3. 点击"日线全屏"按钮（开第 1 个全屏窗口）
4. 点击"分钟线全屏"按钮（开第 2 个全屏窗口）
5. **在日线全屏上点击任意一根 K 线**
6. 观察终端输出，应看到：
   - `[联动V24] 候选全屏窗口 2 个: [...]`
   - `[联动V24] 路径A命中` 或 `路径B命中` 或 `路径C兜底命中`
   - `[联动V24] ✓ 跳转到 _KlineFullscreenWindow (YYYY-MM-DD) 中心完成`
7. 观察**分钟线全屏窗口**：vline 应跳到你点的日线对应日期的**中间区域**

## 7. 验证结果判读

| 终端输出 | 含义 | 后续动作 |
|---|---|---|
| `[联动V24] ✓ 跳转到 ... 中心完成` | V24 成功 | 结束 |
| `[联动V24] A/B/C 三条路径都没找到` | A/B/C 都失败，**全屏窗口根本没注册到列表** | V25 方案：检查 `_fullscreen_windows` 注册逻辑 |
| `[联动V24] ✗ 没有 chart.focus_datetime 接口` | 找到分钟线窗口但 chart 没有 focus_datetime | V25 方案：补 `focus_datetime` 方法（V22 可能未覆盖到这个类） |
| `[联动V24] focus_datetime 失败: ...` | focus_datetime 内部异常 | 看 traceback 决定 |

## 8. V25 备选方案（如果 V24 仍不 work）

- **方案 1（QTimer 异步解耦）**：把"日线全屏点击"和"分钟线全屏跳转"解耦——用 `QTimer.singleShot(100ms)` 延迟到下一帧再扫 `_fullscreen_windows`
- **方案 2（用户手动指定）**：Monitor 工具栏加一个下拉框"联动目标窗口"，让用户手动指定哪个全屏是分钟线——最稳

## 9. V1-V24 总结表

| 版本 | 方案 | 失败原因 |
|---|---|---|
| V1-V4 | 加 `bar_clicked` 信号 + connect | 信号未正确 emit |
| V5 | 注册到 `_fullscreen_windows` | 列表为空时静默失败 |
| V8 | 全屏窗口独立监听 | `_owner_monitor` 注入失败 |
| V11 | 全屏可见性 | focus_datetime 不可用 |
| V12 | 关键属性注入 | _interval 错误 |
| V15 | 严格匹配 interval | _interval 全是 DAILY |
| V16 | 内嵌分钟面板 | 不解决全屏联动 |
| V17 | dispatch 到全屏窗口 | 全屏窗口 _interval 错 |
| V20 | datetimes 间隔反推 | datetimes 为 None |
| V22 | focus_datetime 方法 | 全屏 chart 类未覆盖 |
| V23 | 负向判断 _interval | _interval 全是 DAILY |
| **V24** | **三段独立保险 A+B+C** | **本次验证** |

---

**完成时间**：2026-08-25 14:30
**修复文件**：
- `vnpy/strategy_condition/ui/condition_monitor_widget.py`
- `vnpy/strategy_condition/ui/kline_view.py`

**应用脚本**：`_apply_v24_fix.py`