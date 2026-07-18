"""
strategy_condition/engine/rule_engine.py
策略规则引擎：JSON 存取 / 版本管理 / 策略注册表
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime
from typing import Dict, List, Optional

from ..core.strategy import Strategy, empty_strategy


class RuleEngine:
    """
    策略规则管理引擎。
    负责：
    - 策略 JSON 文件的读写
    - 内存注册表（name -> Strategy）
    - 版本历史记录（每次保存追加版本号）
    """

    DEFAULT_DIR = pathlib.Path.home() / ".vnpy" / "strategy_condition"

    def __init__(self, storage_dir: Optional[pathlib.Path] = None,
                 log_fn=None):
        self._dir = pathlib.Path(storage_dir) if storage_dir else self.DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._log      = log_fn or print
        self._registry: Dict[str, Strategy] = {}   # name -> Strategy

    # ── 注册表操作 ────────────────────────────────────────────────────

    def register(self, strategy: Strategy) -> None:
        """将策略加入内存注册表"""
        self._registry[strategy.name] = strategy
        self._log(f"[RuleEngine] 注册策略: {strategy.name}")

    def get(self, name: str) -> Optional[Strategy]:
        return self._registry.get(name)

    def list_names(self) -> List[str]:
        return sorted(self._registry.keys())

    def remove(self, name: str) -> bool:
        if name in self._registry:
            del self._registry[name]
            return True
        return False

    # ── 文件存取 ──────────────────────────────────────────────────────

    def save(self, strategy: Strategy, bump_version: bool = False) -> pathlib.Path:
        """
        保存策略到 JSON 文件。
        bump_version=True 时自动递增 patch 版本号。
        """
        strategy.touch()
        if bump_version:
            strategy.meta.version = self._bump_patch(strategy.meta.version)

        filename = self._safe_name(strategy.name) + ".json"
        path     = self._dir / filename
        path.write_text(strategy.to_json(indent=2), encoding="utf-8")
        self._log(f"[RuleEngine] 保存策略: {path}")
        self.register(strategy)
        return path

    def load(self, name_or_path: str) -> Optional[Strategy]:
        """
        按名称或路径加载策略。
        先尝试作为文件路径，再拼接默认目录查找。
        """
        path = pathlib.Path(name_or_path)
        if not path.exists():
            path = self._dir / (self._safe_name(name_or_path) + ".json")
        if not path.exists():
            self._log(f"[RuleEngine] 策略文件不存在: {path}")
            return None
        try:
            s = Strategy.from_json(path.read_text(encoding="utf-8"))
            self.register(s)
            self._log(f"[RuleEngine] 加载策略: {s.name} v{s.meta.version}")
            return s
        except Exception as e:
            self._log(f"[RuleEngine] 加载失败: {e}")
            return None

    def load_all(self) -> List[Strategy]:
        """加载存储目录下所有策略"""
        strategies = []
        for f in sorted(self._dir.glob("*.json")):
            s = self.load(str(f))
            if s:
                strategies.append(s)
        self._log(f"[RuleEngine] 加载 {len(strategies)} 个策略")
        return strategies

    def list_files(self) -> List[pathlib.Path]:
        return sorted(self._dir.glob("*.json"))

    def delete_file(self, name: str) -> bool:
        path = self._dir / (self._safe_name(name) + ".json")
        if path.exists():
            path.unlink()
            self.remove(name)
            return True
        return False

    # ── 版本历史（简单实现：带时间戳的备份文件） ──────────────────────

    def save_version(self, strategy: Strategy) -> pathlib.Path:
        """保存带时间戳的历史版本快照"""
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self._safe_name(strategy.name)}_{ts}.json"
        hist_dir = self._dir / "history"
        hist_dir.mkdir(exist_ok=True)
        path = hist_dir / filename
        path.write_text(strategy.to_json(indent=2), encoding="utf-8")
        self._log(f"[RuleEngine] 版本快照: {path}")
        return path

    def list_versions(self, name: str) -> List[pathlib.Path]:
        hist_dir = self._dir / "history"
        prefix   = self._safe_name(name)
        return sorted(hist_dir.glob(f"{prefix}_*.json")) if hist_dir.exists() else []

    # ── 工具 ──────────────────────────────────────────────────────────

    @staticmethod
    def _safe_name(name: str) -> str:
        """将策略名称转换为安全的文件名"""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

    @staticmethod
    def _bump_patch(version: str) -> str:
        """递增 patch 版本号：1.0.2 -> 1.0.3"""
        parts = version.split(".")
        if len(parts) == 3:
            try:
                parts[2] = str(int(parts[2]) + 1)
                return ".".join(parts)
            except ValueError:
                pass
        return version
