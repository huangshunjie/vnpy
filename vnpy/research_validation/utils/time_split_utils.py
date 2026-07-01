"""
research_validation/utils/time_split_utils.py

时间窗口切分工具（Phase 2 实现）。

核心原则：严格防止未来函数——
  test 数据的任何时间点 > train 数据的所有时间点（无重叠、无泄漏）。
"""

from __future__ import annotations

from datetime import datetime


def split_train_test(
    dates:     list[datetime],
    oos_ratio: float = 0.3,
) -> tuple[list[datetime], list[datetime]]:
    """
    按时间顺序切分 in-sample / out-of-sample。

    切分点 = int(n × (1 - oos_ratio))，train 取前段，test 取后段，无重叠。

    Parameters
    ----------
    dates     : 按升序排列的日期序列（调用方保证有序）
    oos_ratio : 样本外比例 (0, 1)，默认 0.3

    Returns
    -------
    (train_dates, test_dates)

    Raises
    ------
    ValueError : dates 为空，或 oos_ratio ∉ (0,1)，或切后任意段为空
    """
    if not dates:
        raise ValueError("dates 不能为空。")
    if not (0.0 < oos_ratio < 1.0):
        raise ValueError(f"oos_ratio 必须在 (0, 1) 内，当前值：{oos_ratio}")

    n       = len(dates)
    split   = max(1, int(n * (1 - oos_ratio)))
    train   = dates[:split]
    test    = dates[split:]

    if not train:
        raise ValueError("训练集为空，请减小 oos_ratio 或增加数据量。")
    if not test:
        raise ValueError("样本外集为空，请增大 oos_ratio 或增加数据量。")

    # 严格检查：train 最后一天 < test 第一天
    assert train[-1] < test[0], (
        f"时间切分违规：train[-1]={train[-1]}  test[0]={test[0]}"
    )
    return train, test


def rolling_windows(
    dates:        list[datetime],
    train_window: int,
    test_window:  int,
    step_size:    int,
) -> list[tuple[list[datetime], list[datetime]]]:
    """
    生成 Walk Forward 滚动窗口序列。

    每次滚动：
      train = dates[start : start + train_window]
      test  = dates[start + train_window : start + train_window + test_window]
    然后 start += step_size。

    Parameters
    ----------
    dates        : 按升序排列的日期序列
    train_window : 训练窗口期数（条数，非日历天）
    test_window  : 测试窗口期数
    step_size    : 每次滚动步长（期数）

    Returns
    -------
    list of (train_dates, test_dates)
      每个元组保证 train 完全早于 test，无任何重叠。
      若无法生成至少一个完整窗口则返回空列表。

    Raises
    ------
    ValueError : 参数非正
    """
    if train_window <= 0 or test_window <= 0 or step_size <= 0:
        raise ValueError("train_window / test_window / step_size 必须为正整数。")

    windows: list[tuple[list[datetime], list[datetime]]] = []
    n     = len(dates)
    start = 0

    while start + train_window + test_window <= n:
        train = dates[start : start + train_window]
        test  = dates[start + train_window : start + train_window + test_window]

        # 严格检查
        assert train[-1] < test[0], (
            f"窗口 {len(windows)} 时间违规："
            f"train[-1]={train[-1]}  test[0]={test[0]}"
        )
        windows.append((train, test))
        start += step_size

    return windows


def validate_no_lookahead(
    factor_timestamp: datetime,
    return_timestamp: datetime,
    lag: int = 1,
) -> bool:
    """
    验证因子时间戳与收益计算起始时间戳之间是否满足最小滞后要求。

    规则：return_timestamp 必须 ≥ factor_timestamp + lag（期数无法直接比较，
    此处简化为 return_timestamp > factor_timestamp）。

    Parameters
    ----------
    factor_timestamp : 因子值最终确定时间（不含当日收盘数据）
    return_timestamp : 持仓起始时间（用于计算持有期收益）
    lag              : 最小合法滞后期数（默认 1，即必须至少晚 1 天）

    Returns
    -------
    bool  True = 无前视偏差；False = 存在前视偏差（return_timestamp 早于因子时间）
    """
    # 简化实现：lag=1 要求 return_timestamp > factor_timestamp
    # 更精确实现（考虑交易日历）在 Phase 5 BiasEngine 中处理
    if lag <= 0:
        return True
    return return_timestamp > factor_timestamp


def count_valid_windows(
    n:            int,
    train_window: int,
    test_window:  int,
    step_size:    int,
) -> int:
    """
    在不实际切分的情况下，计算可生成的滚动窗口数量。

    用于 UI 预览 / 参数合法性校验。
    """
    if train_window <= 0 or test_window <= 0 or step_size <= 0:
        return 0
    count = 0
    start = 0
    while start + train_window + test_window <= n:
        count += 1
        start += step_size
    return count
