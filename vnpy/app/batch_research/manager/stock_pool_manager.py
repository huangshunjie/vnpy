"""
manager/stock_pool_manager.py

StockPoolManager — 股票池持久化管理器。

职责：
  - 扫描 ~/.vnpy/batch_research/stock_pools/ 目录，加载所有 JSON
  - 创建 / 保存 / 删除 / 重命名股票池
  - 导入 CSV / TXT → StockPoolModel
  - 导出 StockPoolModel → CSV / TXT
  - 提供 list_pools / get_pool / get_symbols 查询接口
  - 维护"当前选中股票池"名称（供批量回测窗口读取）

不负责：
  - 任何 Qt 对象
  - UI 事件
  - 网络请求
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Iterator

from ..model.stock_pool_model import StockPoolModel
from ..utils.symbol_parser import SymbolParser, CsvParser, CsvParseResult
from .default_pools import get_default_pool_defs, OnlineUpdater, DEFAULT_UPDATER

logger = logging.getLogger(__name__)

# 默认存储目录
_DEFAULT_DIR = Path.home() / ".vnpy" / "batch_research" / "stock_pools"

# 文件名中不允许出现的字符
_RE_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def _safe_filename(name: str) -> str:
    """将股票池名称转为合法文件名（替换非法字符为 _）。"""
    return _RE_INVALID_CHARS.sub("_", name).strip()



from dataclasses import dataclass, field as _field


@dataclass
class ImportResult:
    """Result returned by StockPoolManager.import_from_file_with_preview()."""

    pool:          StockPoolModel
    parse_result:  CsvParseResult
    overwritten:   bool = False

    @property
    def imported_count(self) -> int:
        return self.parse_result.imported_count

    @property
    def skipped_rows(self) -> int:
        return self.parse_result.skipped_rows

    def summary(self) -> str:
        action = "\u8986\u76d6" if self.overwritten else "\u65b0\u5efa"
        return (
            f"{action}\u80a1\u7968\u6c60 \u300c{self.pool.name}\u300d\uff1a"
            f"{self.parse_result.summary()}"
        )


class StockPoolManager:
    """
    股票池持久化管理器。

    所有读写操作均针对 pool_dir 目录下的 JSON 文件。
    内部维护一个名称→模型的字典缓存，避免频繁磁盘 I/O。

    用法::

        mgr = StockPoolManager()

        # 创建并保存
        pool = mgr.create_pool("我的股票池", ["000001.SZSE", "600519.SSE"])

        # 查询
        symbols = mgr.get_symbols("我的股票池")

        # 删除
        mgr.delete_pool("我的股票池")
    """

    def __init__(self, pool_dir: Path | None = None) -> None:
        """
        :param pool_dir: 股票池 JSON 文件目录，默认为
                         ~/.vnpy/batch_research/stock_pools/
        """
        self._pool_dir: Path = pool_dir or _DEFAULT_DIR
        self._pool_dir.mkdir(parents=True, exist_ok=True)

        # 名称 → StockPoolModel 缓存
        self._cache: dict[str, StockPoolModel] = {}
        self._current_name: str = ""

        self._parser   = SymbolParser()
        self._updater: OnlineUpdater = DEFAULT_UPDATER
        self._load_all()
        self._seed_defaults()

    # ── 查询接口 ───────────────────────────────── #

    def list_pools(self) -> list[str]:
        """
        返回所有股票池名称列表，按名称字典序排序。

        :return: 名称字符串列表。
        """
        return sorted(self._cache.keys())

    def get_pool(self, name: str) -> StockPoolModel | None:
        """
        按名称获取股票池模型。

        :param name: 股票池名称。
        :return:     StockPoolModel 或 None（不存在时）。
        """
        return self._cache.get(name)

    def get_symbols(self, name: str) -> list[str]:
        """
        获取指定股票池的 vt_symbol 列表。

        :param name: 股票池名称。
        :return:     vt_symbol 列表，不存在时返回空列表。
        """
        pool = self._cache.get(name)
        return list(pool.symbols) if pool else []

    def exists(self, name: str) -> bool:
        """判断股票池名称是否已存在。"""
        return name in self._cache

    def __len__(self) -> int:
        return len(self._cache)

    def __iter__(self) -> Iterator[StockPoolModel]:
        return iter(self._cache.values())

    # ── 当前选中股票池 ─────────────────────────── #

    @property
    def current_name(self) -> str:
        """当前选中的股票池名称（空字符串表示未选择）。"""
        return self._current_name

    def set_current(self, name: str) -> bool:
        """
        设置当前选中的股票池。

        :param name: 股票池名称，必须已存在。
        :return:     True 设置成功，False 名称不存在。
        """
        if name and name not in self._cache:
            return False
        self._current_name = name
        return True

    def get_current_symbols(self) -> list[str]:
        """
        获取当前选中股票池的 vt_symbol 列表。

        :return: vt_symbol 列表，未选择时返回空列表。
        """
        return self.get_symbols(self._current_name)

    # ── 创建 / 保存 ───────────────────────────── #

    def create_pool(
        self,
        name: str,
        symbols: list[str] | None = None,
        description: str = "",
    ) -> StockPoolModel:
        """
        创建一个新股票池并持久化。

        :param name:        股票池名称（不能与现有名称重复）。
        :param symbols:     初始 vt_symbol 列表。
        :param description: 可选描述。
        :return:            新建的 StockPoolModel。
        :raises ValueError: 名称为空或已存在。
        """
        name = name.strip()
        if not name:
            raise ValueError("股票池名称不能为空")
        if name in self._cache:
            raise ValueError(f"股票池 '{name}' 已存在")

        pool = StockPoolModel(
            name=name,
            symbols=list(symbols or []),
            description=description,
        )
        pool.deduplicate()
        self._cache[name] = pool
        self._write(pool)
        logger.info("创建股票池 '%s'（%d 只）", name, pool.count)
        return pool

    def save_pool(self, pool: StockPoolModel) -> None:
        """
        保存（或更新）股票池到磁盘。

        若 pool.name 不在缓存中，则视为新建；
        若已存在，则覆盖写入。

        :param pool: 要保存的 StockPoolModel。
        """
        pool.touch()
        pool.deduplicate()
        self._cache[pool.name] = pool
        self._write(pool)
        logger.info("保存股票池 '%s'（%d 只）", pool.name, pool.count)

    def update_symbols(self, name: str, symbols: list[str]) -> StockPoolModel:
        """
        替换指定股票池的股票列表并保存。

        :param name:    股票池名称。
        :param symbols: 新的 vt_symbol 列表（自动去重）。
        :return:        更新后的 StockPoolModel。
        :raises KeyError: 股票池不存在。
        """
        pool = self._require(name)
        pool.set_symbols(symbols)
        pool.deduplicate()
        self._write(pool)
        logger.info("更新股票池 '%s'（%d 只）", name, pool.count)
        return pool

    # ── 删除 ──────────────────────────────────── #

    def delete_pool(self, name: str) -> bool:
        """
        删除股票池（内存缓存 + 磁盘文件）。

        调用方负责在 UI 层做二次确认，此方法直接执行删除。

        :param name: 股票池名称。
        :return:     True 删除成功，False 不存在。
        """
        if name not in self._cache:
            return False

        path = self._path_of(name)
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("删除文件失败 '%s': %s", path, e)

        del self._cache[name]
        if self._current_name == name:
            self._current_name = ""

        logger.info("删除股票池 '%s'", name)
        return True

    # ── 重命名 ────────────────────────────────── #

    def rename_pool(self, old_name: str, new_name: str) -> StockPoolModel:
        """
        重命名股票池（删除旧文件，写入新文件）。

        :param old_name: 当前名称。
        :param new_name: 新名称（不能已存在）。
        :return:         更新后的 StockPoolModel。
        :raises ValueError: 新名称已存在或为空。
        :raises KeyError:   旧名称不存在。
        """
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("新名称不能为空")
        if new_name in self._cache:
            raise ValueError(f"股票池 '{new_name}' 已存在")

        pool = self._require(old_name)
        old_path = self._path_of(old_name)

        pool.name = new_name
        pool.touch()

        self._cache[new_name] = pool
        del self._cache[old_name]

        self._write(pool)
        try:
            old_path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("删除旧文件失败 '%s': %s", old_path, e)

        if self._current_name == old_name:
            self._current_name = new_name

        logger.info("重命名股票池 '%s' → '%s'", old_name, new_name)
        return pool

    def copy_pool(self, source_name: str, new_name: str) -> StockPoolModel:
        """
        复制股票池（深拷贝 symbols，重置时间戳）。

        :param source_name: 来源股票池名称。
        :param new_name:    新股票池名称（不能已存在）。
        :return:            新建的 StockPoolModel。
        """
        source = self._require(source_name)
        return self.create_pool(
            name=new_name,
            symbols=list(source.symbols),
            description=source.description,
        )

    # ── 导入 ──────────────────────────────────── #

    def import_from_text(
        self,
        name: str,
        text: str,
        description: str = "",
        overwrite: bool = False,
    ) -> StockPoolModel:
        """
        从文本内容导入股票池（支持任意 SymbolParser 可识别格式）。

        :param name:        股票池名称。
        :param text:        原始文本（多行、逗号分隔等均可）。
        :param description: 可选描述。
        :param overwrite:   True = 若已存在则覆盖，False = 抛出 ValueError。
        :return:            导入后的 StockPoolModel。
        """
        symbols = self._parser.parse(text)
        if overwrite and name in self._cache:
            return self.update_symbols(name, symbols)
        return self.create_pool(name, symbols, description)

    def import_from_file(
        self,
        name: str,
        filepath: "Path | str",
        encoding: str = "",
        description: str = "",
        overwrite: bool = False,
    ) -> StockPoolModel:
        """
        从 CSV / TXT 文件导入股票池（自动识别编码、表头、列位）。

        :param name:        股票池名称。
        :param filepath:    文件路径。
        :param encoding:    已废弃参数（保留向下兼容），编码现由 CsvParser 自动探测。
        :param description: 可选描述。
        :param overwrite:   True = 若已存在则覆盖。
        :return:            导入后的 StockPoolModel。
        :raises FileNotFoundError: 文件不存在。
        :raises OSError:           文件读取失败。
        """
        result = self.import_from_file_with_preview(
            name, filepath, description, overwrite
        )
        return result.pool

    def import_from_file_with_preview(
        self,
        name: str,
        filepath: "Path | str",
        description: str = "",
        overwrite: bool = False,
    ) -> "ImportResult":
        """
        从 CSV / TXT 文件导入股票池，返回包含预览信息的 ImportResult。

        自动识别能力：
          - 文件编码（utf-8-sig / gbk / gb18030 等）
          - 表头行（自动论断并跳过）
          - 代码所在列（列名匹配关键字或自动扫描）
          - 分隔符（逗号/Tab/竖线/分号）
          - 股票代码格式（纯数字/vt_symbol/Tushare）

        :param name:        股票池名称。
        :param filepath:    文件路径。
        :param description: 可选描述。
        :param overwrite:   True = 若已存在则覆盖。
        :return:            ImportResult（pool + parse_result + overwritten）。
        """
        csv_result = CsvParser().parse_file(Path(filepath))
        symbols    = csv_result.symbols
        overwritten = overwrite and name in self._cache
        if overwrite and name in self._cache:
            pool = self.update_symbols(name, symbols)
            if description:
                pool.description = description
                self._write(pool)
        else:
            pool = self.create_pool(name, symbols, description)
        logger.info(
            "导入股票池 '%s'：%s", name, csv_result.summary()
        )
        return ImportResult(
            pool=pool,
            parse_result=csv_result,
            overwritten=overwritten,
        )

    # ── 导出 ──────────────────────────────────── #

    def export_to_file(
        self,
        name: str,
        filepath: Path | str,
        encoding: str = "utf-8-sig",
    ) -> int:
        """
        将股票池导出为每行一个 vt_symbol 的文本文件。

        :param name:     股票池名称。
        :param filepath: 目标文件路径（.csv 或 .txt）。
        :param encoding: 文件编码，默认 utf-8-sig。
        :return:         导出的股票数量。
        :raises KeyError: 股票池不存在。
        """
        pool = self._require(name)
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(pool.symbols), encoding=encoding)
        logger.info("导出股票池 '%s' → %s（%d 只）", name, path, pool.count)
        return pool.count

    # ── 内部方法 ──────────────────────────────── #

    def _load_all(self) -> None:
        """扫描目录，加载所有 JSON 文件到缓存。"""
        loaded = failed = 0
        for json_file in sorted(self._pool_dir.glob("*.json")):
            pool = self._read(json_file)
            if pool is not None:
                self._cache[pool.name] = pool
                loaded += 1
            else:
                failed += 1
        if loaded or failed:
            logger.debug(
                "股票池目录扫描完成：加载 %d 个，失败 %d 个 (%s)",
                loaded, failed, self._pool_dir,
            )

    def _read(self, path: Path) -> StockPoolModel | None:
        """从单个 JSON 文件读取 StockPoolModel，异常时返回 None。"""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            pool = StockPoolModel.from_dict(data)
            # 文件名优先（防止手动改了文件内容 name 字段）
            if not pool.name:
                pool.name = path.stem
            return pool
        except json.JSONDecodeError as e:
            logger.warning("JSON 解析失败 '%s': %s", path, e)
        except Exception as e:
            logger.warning("读取股票池文件失败 '%s': %s", path, e)
        return None

    def _write(self, pool: StockPoolModel) -> None:
        """将 StockPoolModel 序列化并写入对应 JSON 文件。"""
        path = self._path_of(pool.name)
        try:
            path.write_text(
                json.dumps(pool.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("写入股票池文件失败 '%s': %s", path, e)
            raise

    def _path_of(self, name: str) -> Path:
        """根据股票池名称返回对应 JSON 文件路径。"""
        return self._pool_dir / f"{_safe_filename(name)}.json"

    def _require(self, name: str) -> StockPoolModel:
        """
        获取股票池，不存在时抛出 KeyError。

        :raises KeyError: 股票池名称不存在。
        """
        pool = self._cache.get(name)
        if pool is None:
            raise KeyError(f"股票池 '{name}' 不存在")
        return pool

    def __repr__(self) -> str:
        return (
            f"StockPoolManager(dir={self._pool_dir}, "
            f"pools={len(self._cache)}, "
            f"current={self._current_name!r})"
        )

    # ------------------------------------------------------------------ #
    #  Default pools & online update
    # ------------------------------------------------------------------ #

    def _seed_defaults(self) -> None:
        """首次启动时创建内置默认股票池。

        内幂将置（idempotent）：如果同名股票池已存在，直接跳过，不覆盖用户已有的修改。
        """
        for defn in get_default_pool_defs():
            if defn.name in self._cache:
                continue
            try:
                self.create_pool(
                    defn.name,
                    list(defn.symbols),
                    defn.description,
                )
                logger.debug("创建默认股票池 '%s'", defn.name)
            except Exception as e:
                logger.warning("创建默认股票池 '%s' 失败: %s", defn.name, e)

    def set_updater(self, updater: "OnlineUpdater") -> None:
        """注入在线更新器（供未来 Tushare / AkShare 实现使用）。

        :param updater: 实现了 OnlineUpdater 协议的对象。
        """
        self._updater = updater

    def refresh_pool_online(
        self,
        name: str,
        create_if_missing: bool = True,
    ) -> StockPoolModel:
        """通过已注入的 OnlineUpdater 刷新指定股票池。

        该方法为骨架接口，当前默认使用 _StubUpdater，返回空列表。
        未来接入 TushareUpdater / AkShareUpdater 后即可正常工作。

        :param name:              要刷新的股票池名称。
        :param create_if_missing: True = 若不存在则新建；False = 不存在则抛 KeyError。
        :return:                  更新后的 StockPoolModel。
        :raises RuntimeError:     OnlineUpdater 报错时。
        :raises KeyError:         池不存在且 create_if_missing=False。
        """
        try:
            symbols = self._updater.fetch(name)
        except NotImplementedError:
            raise NotImplementedError(
                f"当前更新器不支持股票池 {name!r}，"
                "请调用 set_updater() 传入支持该池的实现"
            )
        except Exception as e:
            raise RuntimeError(
                f"在线获取股票池 {name!r} 失败: {e}"
            ) from e

        if not symbols:
            logger.warning("在线获取股票池 '%s' 返回空列表，跳过更新", name)
            return self._require(name) if name in self._cache else (
                self.create_pool(name) if create_if_missing
                else self._require(name)
            )

        if name in self._cache:
            return self.update_symbols(name, symbols)
        if create_if_missing:
            return self.create_pool(name, symbols)
        raise KeyError(f"股票池 '{name}' 不存在")
