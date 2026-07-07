"""Patch engine.py: add Model Center imports and methods."""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\engine.py"
)
txt = P.read_text(encoding="utf-8")

# ── 1. imports ─────────────────────────────────────────────────────
txt = txt.replace(
    "from .constant import APP_NAME, ExperimentStatus, DatasetStatus, FeatureStatus, StrategyStatus",
    "from .constant import APP_NAME, ExperimentStatus, DatasetStatus, FeatureStatus, StrategyStatus, ModelStatus",
)
txt = txt.replace(
    "    EVENT_STRATEGY_CREATED,\n"
    "    EVENT_STRATEGY_UPDATED,\n"
    "    EVENT_STRATEGY_DELETED,\n"
    ")",
    "    EVENT_STRATEGY_CREATED,\n"
    "    EVENT_STRATEGY_UPDATED,\n"
    "    EVENT_STRATEGY_DELETED,\n"
    "    EVENT_MODEL_CREATED,\n"
    "    EVENT_MODEL_UPDATED,\n"
    "    EVENT_MODEL_DELETED,\n"
    ")",
)
txt = txt.replace(
    "from .model.strategy_model import StrategyRecord, StrategyVersion",
    "from .model.strategy_model import StrategyRecord, StrategyVersion\n"
    "from .model.model_model import MLModelRecord, TrainingRun",
)

# ── 2. Model methods ────────────────────────────────────────────────
MODEL_METHODS = """
    # ------------------------------------------------------------------
    # Model Registry — Phase 6
    # ------------------------------------------------------------------

    def _gen_model_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"ML-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"ML-{date_str}-{count:03d}"

    def register_model(
        self,
        name:        str,
        version:     str                   = "v1.0",
        description: str                   = "",
        model_type:  str                   = "",
        author:      str                   = "",
        model_path:  str                   = "",
        config_path: str                   = "",
        framework:   str                   = "",
        hyperparams: Optional[Dict[str, Any]] = None,
        tags:        Optional[List[str]]   = None,
        feature_ids: Optional[List[str]]   = None,
        dataset_ids: Optional[List[str]]   = None,
    ) -> MLModelRecord:
        now = datetime.now()
        record = MLModelRecord(
            model_id    = self._gen_model_id(),
            name        = name,
            version     = version,
            description = description,
            model_type  = model_type,
            author      = author,
            model_path  = model_path,
            config_path = config_path,
            framework   = framework,
            hyperparams = hyperparams or {},
            tags        = tags or [],
            feature_ids = feature_ids or [],
            dataset_ids = dataset_ids or [],
            created_at  = now,
            updated_at  = now,
        )
        self.model_registry.create(record)
        self._put(EVENT_MODEL_CREATED, record)
        return record

    def update_model(self, record: MLModelRecord) -> None:
        record.updated_at = datetime.now()
        self.model_registry.update(record)
        self._put(EVENT_MODEL_UPDATED, record)

    def delete_model(self, model_id: str) -> None:
        self.model_registry.delete(model_id)
        self._put(EVENT_MODEL_DELETED, model_id)

    def get_model(self, model_id: str) -> Optional[MLModelRecord]:
        return self.model_registry.get(model_id)

    def list_models(
        self,
        status:     Optional[ModelStatus] = None,
        model_type: Optional[str]         = None,
        tag:        Optional[str]         = None,
        author:     Optional[str]         = None,
    ) -> List[MLModelRecord]:
        return self.model_registry.filter(
            status=status, model_type=model_type, tag=tag, author=author
        )

    def search_models(self, keyword: str) -> List[MLModelRecord]:
        return self.model_registry.search(keyword)

    def update_eval_metrics(
        self,
        model_id:      str,
        accuracy:      float                       = 0.0,
        auc:           float                       = 0.0,
        rmse:          float                       = 0.0,
        mae:           float                       = 0.0,
        f1:            float                       = 0.0,
        custom_metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        self.model_registry.update_eval_metrics(
            model_id, accuracy, auc, rmse, mae, f1, custom_metrics
        )
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def add_training_run(
        self,
        model_id:     str,
        run_note:     str                       = "",
        hyperparams:  Optional[Dict[str, Any]]  = None,
        metrics:      Optional[Dict[str, float]] = None,
        dataset_id:   str                       = "",
        duration_sec: float                     = 0.0,
        created_by:   str                       = "",
    ) -> Optional[TrainingRun]:
        run = self.model_registry.add_training_run(
            model_id, run_note, hyperparams, metrics,
            dataset_id, duration_sec, created_by,
        )
        if run:
            record = self.model_registry.get(model_id)
            self._put(EVENT_MODEL_UPDATED, record)
        return run

    def get_training_runs(self, model_id: str) -> List[TrainingRun]:
        return self.model_registry.get_training_runs(model_id)

    def deploy_model(
        self, model_id: str, env: str = "", endpoint: str = ""
    ) -> None:
        self.model_registry.deploy(model_id, env, endpoint)
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def retire_model(self, model_id: str) -> None:
        self.model_registry.retire(model_id)
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def set_model_evaluated(self, model_id: str) -> None:
        self.model_registry.set_evaluated(model_id)
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def link_model_feature(self, model_id: str, feature_id: str) -> None:
        self.model_registry.link_feature(model_id, feature_id)
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def unlink_model_feature(self, model_id: str, feature_id: str) -> None:
        self.model_registry.unlink_feature(model_id, feature_id)
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def link_model_dataset(self, model_id: str, dataset_id: str) -> None:
        self.model_registry.link_dataset(model_id, dataset_id)
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def link_model_strategy(self, model_id: str, strategy_id: str) -> None:
        self.model_registry.link_strategy(model_id, strategy_id)
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def link_model_experiment(self, model_id: str, experiment_id: str) -> None:
        self.model_registry.link_experiment(model_id, experiment_id)
        record = self.model_registry.get(model_id)
        if record:
            self._put(EVENT_MODEL_UPDATED, record)

    def top_models_by_auc(self, n: int = 10) -> List[MLModelRecord]:
        return self.model_registry.top_by_auc(n)

    def top_models_by_accuracy(self, n: int = 10) -> List[MLModelRecord]:
        return self.model_registry.top_by_accuracy(n)

"""

INSERT_BEFORE = (
    "    # ------------------------------------------------------------------\n"
    "    # 内部事件广播\n"
    "    # ------------------------------------------------------------------"
)
txt = txt.replace(INSERT_BEFORE, MODEL_METHODS + INSERT_BEFORE)

P.write_text(txt, encoding="utf-8")
print("engine.py Model methods patched OK, size:", P.stat().st_size)
