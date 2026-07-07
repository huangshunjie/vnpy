"""Patch engine.py: add Strategy Center imports and methods."""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\engine.py"
)
txt = P.read_text(encoding="utf-8")

# ── 1. imports ─────────────────────────────────────────────────────
txt = txt.replace(
    "from .constant import APP_NAME, ExperimentStatus, DatasetStatus, FeatureStatus",
    "from .constant import APP_NAME, ExperimentStatus, DatasetStatus, FeatureStatus, StrategyStatus",
)
txt = txt.replace(
    "    EVENT_FEATURE_CREATED,\n"
    "    EVENT_FEATURE_UPDATED,\n"
    "    EVENT_FEATURE_DELETED,\n"
    ")",
    "    EVENT_FEATURE_CREATED,\n"
    "    EVENT_FEATURE_UPDATED,\n"
    "    EVENT_FEATURE_DELETED,\n"
    "    EVENT_STRATEGY_CREATED,\n"
    "    EVENT_STRATEGY_UPDATED,\n"
    "    EVENT_STRATEGY_DELETED,\n"
    ")",
)
txt = txt.replace(
    "from .model.feature_model import FeatureRecord, ICRecord",
    "from .model.feature_model import FeatureRecord, ICRecord\n"
    "from .model.strategy_model import StrategyRecord, StrategyVersion",
)

# ── 2. Strategy methods ────────────────────────────────────────────
STRATEGY_METHODS = """
    # ------------------------------------------------------------------
    # Strategy Registry — Phase 5
    # ------------------------------------------------------------------

    def _gen_strategy_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"ST-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"ST-{date_str}-{count:03d}"

    def register_strategy(
        self,
        name:          str,
        version:       str                  = "v1.0",
        description:   str                  = "",
        strategy_type: str                  = "",
        author:        str                  = "",
        code_path:     str                  = "",
        universe:      str                  = "",
        params:        Optional[Dict[str, Any]] = None,
        tags:          Optional[List[str]]  = None,
        feature_ids:   Optional[List[str]]  = None,
        dataset_ids:   Optional[List[str]]  = None,
    ) -> StrategyRecord:
        now = datetime.now()
        record = StrategyRecord(
            strategy_id   = self._gen_strategy_id(),
            name          = name,
            version       = version,
            description   = description,
            strategy_type = strategy_type,
            author        = author,
            code_path     = code_path,
            universe      = universe,
            params        = params or {},
            tags          = tags or [],
            feature_ids   = feature_ids or [],
            dataset_ids   = dataset_ids or [],
            created_at    = now,
            updated_at    = now,
        )
        self.strategy_registry.create(record)
        self._put(EVENT_STRATEGY_CREATED, record)
        return record

    def update_strategy(self, record: StrategyRecord) -> None:
        record.updated_at = datetime.now()
        self.strategy_registry.update(record)
        self._put(EVENT_STRATEGY_UPDATED, record)

    def delete_strategy(self, strategy_id: str) -> None:
        self.strategy_registry.delete(strategy_id)
        self._put(EVENT_STRATEGY_DELETED, strategy_id)

    def get_strategy(self, strategy_id: str) -> Optional[StrategyRecord]:
        return self.strategy_registry.get(strategy_id)

    def list_strategies(
        self,
        status:        Optional[StrategyStatus] = None,
        strategy_type: Optional[str]            = None,
        tag:           Optional[str]            = None,
        author:        Optional[str]            = None,
    ) -> List[StrategyRecord]:
        return self.strategy_registry.filter(
            status=status, strategy_type=strategy_type, tag=tag, author=author
        )

    def search_strategies(self, keyword: str) -> List[StrategyRecord]:
        return self.strategy_registry.search(keyword)

    def update_performance(
        self,
        strategy_id:   str,
        annual_return: float = 0.0,
        max_drawdown:  float = 0.0,
        sharpe:        float = 0.0,
        sortino:       float = 0.0,
        calmar:        float = 0.0,
        win_rate:      float = 0.0,
        turnover:      float = 0.0,
        profit_factor: float = 0.0,
    ) -> None:
        self.strategy_registry.update_performance(
            strategy_id, annual_return, max_drawdown,
            sharpe, sortino, calmar, win_rate, turnover, profit_factor,
        )
        record = self.strategy_registry.get(strategy_id)
        if record:
            self._put(EVENT_STRATEGY_UPDATED, record)

    def publish_strategy(self, strategy_id: str) -> None:
        self.strategy_registry.publish(strategy_id)
        record = self.strategy_registry.get(strategy_id)
        if record:
            self._put(EVENT_STRATEGY_UPDATED, record)

    def retire_strategy(self, strategy_id: str) -> None:
        self.strategy_registry.retire(strategy_id)
        record = self.strategy_registry.get(strategy_id)
        if record:
            self._put(EVENT_STRATEGY_UPDATED, record)

    def set_strategy_testing(self, strategy_id: str) -> None:
        self.strategy_registry.set_testing(strategy_id)
        record = self.strategy_registry.get(strategy_id)
        if record:
            self._put(EVENT_STRATEGY_UPDATED, record)

    def add_strategy_version(
        self, strategy_id: str, note: str = "", created_by: str = ""
    ) -> Optional[StrategyVersion]:
        ver = self.strategy_registry.add_version(strategy_id, note, created_by)
        if ver:
            record = self.strategy_registry.get(strategy_id)
            self._put(EVENT_STRATEGY_UPDATED, record)
        return ver

    def get_strategy_versions(self, strategy_id: str) -> List[StrategyVersion]:
        return self.strategy_registry.get_versions(strategy_id)

    def link_strategy_feature(self, strategy_id: str, feature_id: str) -> None:
        self.strategy_registry.link_feature(strategy_id, feature_id)
        record = self.strategy_registry.get(strategy_id)
        if record:
            self._put(EVENT_STRATEGY_UPDATED, record)

    def unlink_strategy_feature(self, strategy_id: str, feature_id: str) -> None:
        self.strategy_registry.unlink_feature(strategy_id, feature_id)
        record = self.strategy_registry.get(strategy_id)
        if record:
            self._put(EVENT_STRATEGY_UPDATED, record)

    def link_strategy_backtest(self, strategy_id: str, backtest_id: str) -> None:
        self.strategy_registry.link_backtest(strategy_id, backtest_id)
        record = self.strategy_registry.get(strategy_id)
        if record:
            self._put(EVENT_STRATEGY_UPDATED, record)

    def top_strategies_by_sharpe(self, n: int = 10) -> List[StrategyRecord]:
        return self.strategy_registry.top_by_sharpe(n)

    def top_strategies_by_return(self, n: int = 10) -> List[StrategyRecord]:
        return self.strategy_registry.top_by_return(n)

"""

INSERT_BEFORE = (
    "    # ------------------------------------------------------------------\n"
    "    # 内部事件广播\n"
    "    # ------------------------------------------------------------------"
)
txt = txt.replace(INSERT_BEFORE, STRATEGY_METHODS + INSERT_BEFORE)

P.write_text(txt, encoding="utf-8")
print("engine.py Strategy methods patched OK, size:", P.stat().st_size)
