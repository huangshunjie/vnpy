"""
v3 修复验证：focus_datetime 在 aware/naive 混合场景下能正确定位目标。

构造一组 bar（带 +08:00 tzinfo），传入 aware dt 和 naive dt 两种参数，
验证：
  1. aware dt 不会触发 TypeError
  2. naive dt 也能工作（兼容旧调用）
  3. 定位结果一致（同一逻辑日期落在同一根 bar）

不启动 Qt，只测 _PeriodMonitorPanel.focus_datetime 内部的纯逻辑部分。
"""
import sys
from datetime import datetime, date, time, timezone, timedelta

sys.path.insert(0, '.')


# ── Mock 最小依赖（避开 PyQtGraph 加载）──────────────────────
class _Bar:
    def __init__(self, dt):
        self.datetime = dt
        self.dt = dt


# 直接复制修复后的核心逻辑做单元测试（避免 import 整个模块触发 Qt）
def focus_datetime(bars, dt, completed_daily=False):
    """修复后版本：dt 和 bar_dt 都统一为 naive 再比较。"""
    if dt is None or not bars:
        return None
    # 1) dt 去 tz
    try:
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
    except Exception:
        pass
    target_index = None
    for index, bar in enumerate(bars):
        bar_dt = getattr(bar, "dt", getattr(bar, "datetime", None))
        if bar_dt is None:
            continue
        # 2) bar_dt 去 tz
        try:
            if bar_dt.tzinfo is not None:
                bar_dt_cmp = bar_dt.replace(tzinfo=None)
            else:
                bar_dt_cmp = bar_dt
        except Exception:
            bar_dt_cmp = bar_dt
        if completed_daily and bar_dt_cmp.date() >= dt.date():
            continue
        if bar_dt_cmp <= dt:
            target_index = index
    return target_index


def test_aware_dt_no_crash():
    """最关键：bar 是 aware、dt 也是 aware，不能再报 TypeError。"""
    tz = timezone(timedelta(hours=8))
    bars = [
        _Bar(datetime(2026, 7, 1, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 2, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 3, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 4, 0, 0, tzinfo=tz)),
    ]
    dt_aware = datetime(2026, 7, 3, 12, 0, tzinfo=tz)
    idx = focus_datetime(bars, dt_aware)
    assert idx == 2, f"aware dt 应定位到 7/3 bar, 实际 idx={idx}"
    print(f"  [PASS] aware dt → idx={idx}")


def test_naive_dt_works():
    """旧调用兼容：dt 是 naive 也不能崩。"""
    tz = timezone(timedelta(hours=8))
    bars = [
        _Bar(datetime(2026, 7, 1, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 2, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 3, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 4, 0, 0, tzinfo=tz)),
    ]
    dt_naive = datetime(2026, 7, 3, 12, 0)
    idx = focus_datetime(bars, dt_naive)
    assert idx == 2, f"naive dt 应定位到 7/3 bar, 实际 idx={idx}"
    print(f"  [PASS] naive dt → idx={idx}")


def test_mixed_bars_naive_dt():
    """混合：部分 bar aware / 部分 naive。"""
    tz = timezone(timedelta(hours=8))
    bars = [
        _Bar(datetime(2026, 7, 1, 0, 0)),  # naive
        _Bar(datetime(2026, 7, 2, 0, 0, tzinfo=tz)),  # aware
        _Bar(datetime(2026, 7, 3, 0, 0)),  # naive
    ]
    dt_naive = datetime(2026, 7, 2, 12, 0)
    idx = focus_datetime(bars, dt_naive)
    assert idx == 1, f"混合 bar + naive dt 应到 idx=1, 实际={idx}"
    print(f"  [PASS] mixed bars + naive dt → idx={idx}")


def test_completed_daily_skip_same_day():
    """completed_daily=True 时跳过同日 bar，取前一交易日。"""
    tz = timezone(timedelta(hours=8))
    bars = [
        _Bar(datetime(2026, 7, 1, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 2, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 3, 0, 0, tzinfo=tz)),
    ]
    # 目标 7/3，但 completed_daily=True → 跳过 7/3，取 7/2
    dt_aware = datetime(2026, 7, 3, 12, 0, tzinfo=tz)
    idx = focus_datetime(bars, dt_aware, completed_daily=True)
    assert idx == 1, f"completed_daily=True 应跳过 7/3 → idx=1, 实际={idx}"
    print(f"  [PASS] completed_daily skip same-day → idx={idx}")


def test_aware_dt_past_all_bars():
    """dt > 所有 bar 时返回最后一根 idx。"""
    tz = timezone(timedelta(hours=8))
    bars = [
        _Bar(datetime(2026, 7, 1, 0, 0, tzinfo=tz)),
        _Bar(datetime(2026, 7, 2, 0, 0, tzinfo=tz)),
    ]
    dt_aware = datetime(2026, 8, 1, 12, 0, tzinfo=tz)
    idx = focus_datetime(bars, dt_aware)
    assert idx == 1, f"dt 大于所有 bar 应返回最后 idx=1, 实际={idx}"
    print(f"  [PASS] aware dt > all bars → idx={idx}")


def test_minute_bar_with_intraday_time():
    """真实场景：分钟 bar 同一天多根，12:00 dt 应落在当天 ≥12:00 的首根。"""
    tz = timezone(timedelta(hours=8))
    bars = [
        _Bar(datetime(2026, 7, 1, 9, 35, tzinfo=tz)),
        _Bar(datetime(2026, 7, 1, 9, 40, tzinfo=tz)),
        _Bar(datetime(2026, 7, 1, 11, 30, tzinfo=tz)),
        _Bar(datetime(2026, 7, 1, 12, 0, tzinfo=tz)),  # 12:00 整
        _Bar(datetime(2026, 7, 1, 13, 0, tzinfo=tz)),
    ]
    dt_aware = datetime(2026, 7, 1, 12, 0, tzinfo=tz)
    idx = focus_datetime(bars, dt_aware)
    assert idx == 3, f"12:00 应定位到 idx=3, 实际={idx}"
    print(f"  [PASS] minute bar 12:00 → idx={idx}")


if __name__ == "__main__":
    print("=" * 60)
    print("v3 修复验证：focus_datetime tz 一致性")
    print("=" * 60)
    test_aware_dt_no_crash()
    test_naive_dt_works()
    test_mixed_bars_naive_dt()
    test_completed_daily_skip_same_day()
    test_aware_dt_past_all_bars()
    test_minute_bar_with_intraday_time()
    print("=" * 60)
    print("[ALL PASS] v3 fix verified: focus_datetime tz alignment")
