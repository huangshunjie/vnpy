"""Patch engine.py: add Backtest Center imports and methods."""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\engine.py"
)
txt = P.read_text(encoding="utf-8")

# ── 1. imports ─────────────────────────────────────────────────────
txt = txt.replace(
    "from .constant import APP_NAME, ExperimentStatus, DatasetStatus, FeatureStatus, StrategyStatus, ModelStatus",
    "from .constant import APP_NAME, ExperimentStatus, DatasetStatus, FeatureStatus, StrategyStatus, ModelStatus, BacktestStatus",
)
txt = txt.replace(
    "    EVENT_MODEL_CREATED,\n"
    "    EVENT_MODEL_UPDATED,\n"
    "    EVENT_MODEL_DELETED,\n"
    ")",
    "    EVENT_MODEL_CREATED,\n"
    "    EVENT_MODEL_UPDATED,\n"
    "    EVENT_MODEL_DELETED,\n"
    "    EVENT_BACKTEST_CREATED,\n"
    "    EVENT_BACKTEST_UPDATED,\n"
    "    EVENT_BACKTEST_DELETED,\n"
    ")",
)
txt = txt.replace(
    "from .model.model_model import MLModelRecord, TrainingRun",
    "from .model.model_model import MLModelRecord, TrainingRun\n"
    "from .model.backtest_model import BacktestRecord, DailyEquity",
)

# ── 2. Backtest methods ─────────────────────────────────────────────
BACKTEST_METHODS = """
    # ------------------------------------------------------------------
    # Backtest Registry — Phase 7
    # ------------------------------------------------------------------

    def _gen_backtest_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"BT-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"BT-{date_str}-{count:03d}"

    def submit_backtest(
        self,
        name:            str,
        strategy_id:     str                   = "",
        strategy_name:   str                   = "",
        description:     str                   = "",
        start_date:      str                   = "",
        end_date:        str                   = "",
        initial_capital: float                 = 1_000_000.0,
        commission:      float                 = 0.0003,
        slippage:        float                 = 0.0,
        universe:        str                   = "",
        params:          Optional[Dict[str, Any]] = None,
        tags:            Optional[List[str]]   = None,
        feature_ids:     Optional[List[str]]   = None,
        dataset_ids:     Optional[List[str]]   = None,
        model_ids:       Optional[List[str]]   = None,
        created_by:      str                   = "",
    ) -> BacktestRecord:
        now = datetime.now()
        record = BacktestRecord(
            backtest_id     = self._gen_backtest_id(),
            name            = name,
            description     = description,
            status          = BacktestStatus.PENDING,
            strategy_id     = strategy_id,
            strategy_name   = strategy_name,
            start_date      = start_date,
            end_date        = end_date,
            initial_capital = initial_capital,
            commission      = commission,
            slippage        = slippage,
            universe        = universe,
            params          = params or {},
            tags            = tags or [],
            feature_ids     = feature_ids or [],
            dataset_ids     = dataset_ids or [],
            model_ids       = model_ids or [],
            created_by      = created_by,
            created_at      = now,
            updated_at      = now,
        )
        self.backtest_registry.create(record)
        self._put(EVENT_BACKTEST_CREATED, record)
        return record

    def update_backtest(self, record: BacktestRecord) -> None:
        record.updated_at = datetime.now()
        self.backtest_registry.update(record)
        self._put(EVENT_BACKTEST_UPDATED, record)

    def delete_backtest(self, backtest_id: str) -> None:
        self.backtest_registry.delete(backtest_id)
        self._put(EVENT_BACKTEST_DELETED, backtest_id)

    def get_backtest(self, backtest_id: str) -> Optional[BacktestRecord]:
        return self.backtest_registry.get(backtest_id)

    def list_backtests(
        self,
        status:      Optional[BacktestStatus] = None,
        strategy_id: Optional[str]            = None,
        tag:         Optional[str]            = None,
    ) -> List[BacktestRecord]:
        return self.backtest_registry.filter(
            status=status, strategy_id=strategy_id, tag=tag
        )

    def search_backtests(self, keyword: str) -> List[BacktestRecord]:
        return self.backtest_registry.search(keyword)

    def run_backtest(self, backtest_id: str) -> None:
        self.backtest_registry.submit(backtest_id)
        record = self.backtest_registry.get(backtest_id)
        if record:
            self._put(EVENT_BACKTEST_UPDATED, record)

    def complete_backtest(
        self,
        backtest_id:     str,
        annual_return:   float = 0.0,
        max_drawdown:    float = 0.0,
        sharpe:          float = 0.0,
        sortino:         float = 0.0,
        calmar:          float = 0.0,
        win_rate:        float = 0.0,
        turnover:        float = 0.0,
        profit_factor:   float = 0.0,
        total_return:    float = 0.0,
        alpha:           float = 0.0,
        beta:            float = 0.0,
        information_ratio: float = 0.0,
        total_trades:    int   = 0,
        avg_holding_days: float = 0.0,
        max_position_conc: float = 0.0,
        equity_curve:    Optional[List[DailyEquity]] = None,
        monthly_returns: Optional[Dict[str, float]]  = None,
    ) -> None:
        self.backtest_registry.complete(
            backtest_id, annual_return, max_drawdown, sharpe,
            sortino, calmar, win_rate, turnover, profit_factor,
            total_return, alpha, beta, information_ratio,
            total_trades, avg_holding_days, max_position_conc,
            equity_curve, monthly_returns,
        )
        record = self.backtest_registry.get(backtest_id)
        if record:
            self._put(EVENT_BACKTEST_UPDATED, record)

    def fail_backtest(self, backtest_id: str, error_msg: str = "") -> None:
        self.backtest_registry.fail(backtest_id, error_msg)
        record = self.backtest_registry.get(backtest_id)
        if record:
            self._put(EVENT_BACKTEST_UPDATED, record)

    def compare_backtests(self, backtest_ids: List[str]) -> List[BacktestRecord]:
        return self.backtest_registry.compare(backtest_ids)

    def link_backtest_model(self, backtest_id: str, model_id: str) -> None:
        self.backtest_registry.link_model(backtest_id, model_id)
        record = self.backtest_registry.get(backtest_id)
        if record:
            self._put(EVENT_BACKTEST_UPDATED, record)

    def unlink_backtest_model(self, backtest_id: str, model_id: str) -> None:
        self.backtest_registry.unlink_model(backtest_id, model_id)
        record = self.backtest_registry.get(backtest_id)
        if record:
            self._put(EVENT_BACKTEST_UPDATED, record)

    def link_backtest_feature(self, backtest_id: str, feature_id: str) -> None:
        self.backtest_registry.link_feature(backtest_id, feature_id)
        record = self.backtest_registry.get(backtest_id)
        if record:
            self._put(EVENT_BACKTEST_UPDATED, record)

    def link_backtest_dataset(self, backtest_id: str, dataset_id: str) -> None:
        self.backtest_registry.link_dataset(backtest_id, dataset_id)
        record = self.backtest_registry.get(backtest_id)
        if record:
            self._put(EVENT_BACKTEST_UPDATED, record)

    def top_backtests_by_sharpe(self, n: int = 10) -> List[BacktestRecord]:
        return self.backtest_registry.top_by_sharpe(n)

    def top_backtests_by_return(self, n: int = 10) -> List[BacktestRecord]:
        return self.backtest_registry.top_by_return(n)

"""

INSERT_BEFORE = (
    "    # ------------------------------------------------------------------\n"
    "    # 内部事件广播\n"
    "    # ------------------------------------------------------------------"
)
txt = txt.replace(INSERT_BEFORE, BACKTEST_METHODS + INSERT_BEFORE)

P.write_text(txt, encoding="utf-8")
print("engine.py Backtest methods patched OK, size:", P.stat().st_size)
