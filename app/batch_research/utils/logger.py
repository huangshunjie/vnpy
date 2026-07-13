"""
Logger

批量回测平台专用日志模块。
封装标准 logging，统一格式，支持文件和控制台输出。
"""

import logging
from pathlib import Path


BATCH_LOGGER_NAME = "batch_research"


def get_logger(name: str = BATCH_LOGGER_NAME) -> logging.Logger:
    """获取 batch_research 日志记录器。"""
    return logging.getLogger(name)


def setup_logger(
    log_level: int = logging.INFO,
    log_file: Path | None = None,
) -> logging.Logger:
    """
    初始化日志记录器。

    :param log_level: 日志级别，默认 INFO。
    :param log_file: 可选日志文件路径；不传则只输出到控制台。
    """
    logger = logging.getLogger(BATCH_LOGGER_NAME)
    logger.setLevel(log_level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
