"""
Timer

任务计时工具，记录每只股票回测耗时及整体批量回测耗时。
"""

import time
from contextlib import contextmanager
from typing import Generator


class Timer:
    """简单计时器，支持 start/stop 和上下文管理器两种用法。"""

    def __init__(self) -> None:
        self._start: float = 0.0
        self._elapsed: float = 0.0

    def start(self) -> None:
        self._start = time.perf_counter()

    def stop(self) -> float:
        """停止计时，返回本次耗时（秒）。"""
        self._elapsed = time.perf_counter() - self._start
        return self._elapsed

    @property
    def elapsed(self) -> float:
        """返回上次计时的耗时（秒）。"""
        return self._elapsed

    def __enter__(self) -> "Timer":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


@contextmanager
def timed(label: str = "") -> Generator[Timer, None, None]:
    """
    上下文管理器，打印代码块耗时。

    用法::

        with timed("批量回测"):
            engine.run_backtesting()
    """
    t = Timer()
    t.start()
    try:
        yield t
    finally:
        elapsed = t.stop()
        tag = f"[{label}] " if label else ""
        print(f"{tag}耗时: {elapsed:.3f} 秒")
