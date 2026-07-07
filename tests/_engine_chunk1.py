"""Append Experiment + Registry API to engine.py"""
import pathlib
P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\engine.py")

CHUNK1 = """
    # ==================================================================
    # Experiment API
    # ==================================================================

    def create_experiment(self, name: str, **kw) -> ExperimentRecord:
        exp = self.experiment.create_experiment(name, **kw)
        from .event import EVENT_RO_EXP_CREATED
        self._put(EVENT_RO_EXP_CREATED, exp); return exp

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentRecord]:
        return self.experiment.get_experiment(experiment_id)

    def list_experiments(self, **kw) -> List[ExperimentRecord]:
        return self.experiment.list_experiments(**kw)

    def update_experiment(self, exp: ExperimentRecord) -> None:
        self.experiment.update_experiment(exp)
        from .event import EVENT_RO_EXP_UPDATED
        self._put(EVENT_RO_EXP_UPDATED, exp)

    def delete_experiment(self, experiment_id: str) -> None:
        self.experiment.delete_experiment(experiment_id)
        from .event import EVENT_RO_EXP_DELETED
        self._put(EVENT_RO_EXP_DELETED, experiment_id)

    def search_experiments(self, keyword: str) -> List[ExperimentRecord]:
        return self.experiment.search_experiments(keyword)

    def start_run(self, experiment_id: str, **kw) -> RunRecord:
        run = self.experiment.start_run(experiment_id, **kw)
        from .event import EVENT_RO_RUN_CREATED
        self._put(EVENT_RO_RUN_CREATED, run); return run

    def complete_run(self, run_id: str, metrics: Optional[Dict] = None) -> None:
        self.experiment.complete_run(run_id, metrics)
        from .event import EVENT_RO_RUN_COMPLETED
        self._put(EVENT_RO_RUN_COMPLETED, run_id)

    def fail_run(self, run_id: str, error_msg: str = "") -> None:
        self.experiment.fail_run(run_id, error_msg)
        from .event import EVENT_RO_RUN_FAILED
        self._put(EVENT_RO_RUN_FAILED, run_id)

    def log_metric(self, run_id: str, key: str, value: float, step: int = 0) -> None:
        self.experiment.log_metric(run_id, key, value, step)
        from .event import EVENT_RO_METRIC_LOGGED
        self._put(EVENT_RO_METRIC_LOGGED, {"run_id": run_id, "key": key, "value": value})

    def log_params(self, run_id: str, params: Dict) -> None:
        self.experiment.log_params(run_id, params)

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        return self.experiment.get_run(run_id)

    def list_runs(self, experiment_id: str) -> List[RunRecord]:
        return self.experiment.list_runs(experiment_id)

    def compare_runs(self, run_ids: List[str], metric_keys: Optional[List[str]] = None) -> List[Dict]:
        return self.experiment.compare_runs(run_ids, metric_keys)

    # ==================================================================
    # Registry API — Dataset / Feature / Strategy / Model
    # ==================================================================

    def register_dataset(self, name: str, **kw) -> DatasetEntry:
        ds = self.registry.register_dataset(name, **kw)
        from .event import EVENT_RO_DS_REGISTERED
        self._put(EVENT_RO_DS_REGISTERED, ds); return ds

    def get_dataset(self, dataset_id: str) -> Optional[DatasetEntry]:
        return self.registry.get_dataset(dataset_id)

    def list_datasets(self, **kw) -> List[DatasetEntry]:
        return self.registry.list_datasets(**kw)

    def update_dataset(self, ds: DatasetEntry) -> None:
        self.registry.update_dataset(ds)

    def delete_dataset(self, dataset_id: str) -> None:
        self.registry.delete_dataset(dataset_id)
        from .event import EVENT_RO_DS_DELETED
        self._put(EVENT_RO_DS_DELETED, dataset_id)

    def set_dataset_ready(self, dataset_id: str) -> None:
        self.registry.set_dataset_ready(dataset_id)

    def add_dataset_version(self, dataset_id: str, **kw) -> Optional[DatasetVersion]:
        return self.registry.add_dataset_version(dataset_id, **kw)

    def search_datasets(self, keyword: str) -> List[DatasetEntry]:
        return self.registry.search_datasets(keyword)

    def register_feature(self, name: str, **kw) -> FeatureEntry:
        ft = self.registry.register_feature(name, **kw)
        from .event import EVENT_RO_FT_REGISTERED
        self._put(EVENT_RO_FT_REGISTERED, ft); return ft

    def get_feature(self, feature_id: str) -> Optional[FeatureEntry]:
        return self.registry.get_feature(feature_id)

    def list_features(self, **kw) -> List[FeatureEntry]:
        return self.registry.list_features(**kw)

    def update_feature(self, ft: FeatureEntry) -> None:
        self.registry.update_feature(ft)

    def delete_feature(self, feature_id: str) -> None:
        self.registry.delete_feature(feature_id)

    def update_ic_metrics(self, feature_id: str, **kw) -> Optional[ICRecord]:
        return self.registry.update_ic_metrics(feature_id, **kw)

    def set_feature_status(self, feature_id: str, status: FeatureStatus) -> None:
        self.registry.set_feature_status(feature_id, status)

    def search_features(self, keyword: str) -> List[FeatureEntry]:
        return self.registry.search_features(keyword)

    def top_features_by_ic(self, n: int = 10) -> List[FeatureEntry]:
        return self.registry.top_by_ic(n)

    def register_strategy(self, name: str, **kw) -> StrategyEntry:
        st = self.registry.register_strategy(name, **kw)
        from .event import EVENT_RO_ST_REGISTERED
        self._put(EVENT_RO_ST_REGISTERED, st); return st

    def get_strategy(self, strategy_id: str) -> Optional[StrategyEntry]:
        return self.registry.get_strategy(strategy_id)

    def list_strategies(self, **kw) -> List[StrategyEntry]:
        return self.registry.list_strategies(**kw)

    def update_strategy(self, st: StrategyEntry) -> None:
        self.registry.update_strategy(st)

    def delete_strategy(self, strategy_id: str) -> None:
        self.registry.delete_strategy(strategy_id)

    def set_strategy_status(self, strategy_id: str, status: StrategyStatus) -> None:
        self.registry.set_strategy_status(strategy_id, status)
        from .event import EVENT_RO_ST_STATUS
        self._put(EVENT_RO_ST_STATUS, {"id": strategy_id, "status": status.value})

    def add_strategy_version(self, strategy_id: str, **kw) -> Optional[StrategyVersion]:
        return self.registry.add_strategy_version(strategy_id, **kw)

    def update_strategy_perf(self, strategy_id: str, **kw) -> None:
        self.registry.update_strategy_perf(strategy_id, **kw)

    def search_strategies(self, keyword: str) -> List[StrategyEntry]:
        return self.registry.search_strategies(keyword)

    def top_strategies_by_sharpe(self, n: int = 10) -> List[StrategyEntry]:
        return self.registry.top_by_sharpe(n)

    def register_model(self, name: str, **kw) -> ModelEntry:
        ml = self.registry.register_model(name, **kw)
        from .event import EVENT_RO_ML_REGISTERED
        self._put(EVENT_RO_ML_REGISTERED, ml); return ml

    def get_model(self, model_id: str) -> Optional[ModelEntry]:
        return self.registry.get_model(model_id)

    def list_models(self, **kw) -> List[ModelEntry]:
        return self.registry.list_models(**kw)

    def update_model(self, ml: ModelEntry) -> None:
        self.registry.update_model(ml)

    def delete_model(self, model_id: str) -> None:
        self.registry.delete_model(model_id)

    def add_training_run(self, model_id: str, **kw) -> Optional[TrainingRun]:
        return self.registry.add_training_run(model_id, **kw)

    def deploy_model(self, model_id: str, **kw) -> None:
        self.registry.deploy_model(model_id, **kw)
        from .event import EVENT_RO_ML_DEPLOYED
        self._put(EVENT_RO_ML_DEPLOYED, model_id)

    def set_model_status(self, model_id: str, status: ModelStatus) -> None:
        self.registry.set_model_status(model_id, status)

    def search_models(self, keyword: str) -> List[ModelEntry]:
        return self.registry.search_models(keyword)

    def top_models_by_auc(self, n: int = 10) -> List[ModelEntry]:
        return self.registry.top_by_auc(n)

    def get_lineage(self, node_id: str) -> Dict:
        lin = self.registry.lineage.full_lineage(node_id)
        return {k: list(v) for k, v in lin.items()}

    # PLACEHOLDER_PIPELINE_REPORT
"""

txt = P.read_text(encoding="utf-8")
txt = txt.replace("    # PLACEHOLDER_EXP", CHUNK1)
P.write_text(txt, encoding="utf-8")
print("engine.py chunk1 OK, size:", P.stat().st_size)
