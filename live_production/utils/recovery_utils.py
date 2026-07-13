"""
live_production/utils/recovery_utils.py

Checkpoint 序列化 / 反序列化工具（Phase 3）。

职责：
  - 将系统快照写入本地 JSON 文件
  - 从文件加载最近的 Checkpoint
  - 维护滚动存档（保留最近 N 份）

❌ 不包含任何交易逻辑
❌ 不访问任何交易所 API
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


_DEFAULT_DIR  = Path(".vnpy") / "live_production" / "checkpoints"
_MAX_KEEP     = 10          # 最多保留 N 份 checkpoint
_FILE_PREFIX  = "checkpoint_"
_FILE_EXT     = ".json"


def _ensure_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


def save_checkpoint(data: dict, directory: Path | str | None = None) -> Path:
    """
    将 data 序列化为 JSON 并写入 checkpoint 文件。

    文件名格式：checkpoint_YYYYMMDD_HHMMSS.json

    Parameters
    ----------
    data      : 待保存的字典（必须 JSON 可序列化）
    directory : 存储目录，默认 .vnpy/live_production/checkpoints/

    Returns
    -------
    Path  写入成功的文件路径
    """
    dir_path = Path(directory) if directory else _DEFAULT_DIR
    _ensure_dir(dir_path)

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_FILE_PREFIX}{ts}{_FILE_EXT}"
    filepath = dir_path / filename

    payload = {
        "version":    1,
        "saved_at":   str(datetime.now()),
        "data":       data,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    _rotate(dir_path)
    return filepath


def load_latest_checkpoint(
    directory: Path | str | None = None,
) -> dict | None:
    """
    加载最新的 checkpoint 文件。

    Returns
    -------
    dict   checkpoint 的 "data" 字段，若无文件则返回 None
    """
    dir_path = Path(directory) if directory else _DEFAULT_DIR
    if not dir_path.exists():
        return None

    files = sorted(
        dir_path.glob(f"{_FILE_PREFIX}*{_FILE_EXT}"),
        key=lambda p: p.name,
        reverse=True,
    )
    if not files:
        return None

    with open(files[0], encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("data")


def load_checkpoint_at(
    filepath: Path | str,
) -> dict | None:
    """从指定路径加载 checkpoint。"""
    fp = Path(filepath)
    if not fp.exists():
        return None
    with open(fp, encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("data")


def list_checkpoints(
    directory: Path | str | None = None,
) -> list[dict]:
    """
    列出所有 checkpoint 文件的元信息。

    Returns
    -------
    list[dict]  每项包含 path / filename / saved_at / size_kb
    """
    dir_path = Path(directory) if directory else _DEFAULT_DIR
    if not dir_path.exists():
        return []

    result = []
    for fp in sorted(
        dir_path.glob(f"{_FILE_PREFIX}*{_FILE_EXT}"),
        key=lambda p: p.name,
        reverse=True,
    ):
        try:
            with open(fp, encoding="utf-8") as f:
                meta = json.load(f)
            result.append({
                "path":     str(fp),
                "filename": fp.name,
                "saved_at": meta.get("saved_at", ""),
                "size_kb":  round(fp.stat().st_size / 1024, 1),
            })
        except Exception:
            pass
    return result


def _rotate(directory: Path) -> None:
    """删除超出 _MAX_KEEP 数量的旧 checkpoint。"""
    files = sorted(
        directory.glob(f"{_FILE_PREFIX}*{_FILE_EXT}"),
        key=lambda p: p.name,
        reverse=True,
    )
    for old in files[_MAX_KEEP:]:
        try:
            old.unlink()
        except Exception:
            pass
