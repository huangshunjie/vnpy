"""Append Strategy + Model + stats to registry_engine.py"""
import pathlib
P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\engine\registry_engine.py"
)

APPEND = """
    # ==================================================================
    # Strategy
    # ==================================================================

    def register_strategy(
        self,
        name:         str,
        description:  str = "",
        version:      str = "v1.0.0",
        author:       str = "",
        feature_ids:  Optional[List[str]] = None,
        dataset_ids:  Optional[List[str]] = None,
        tags:         Optional[List[str]] = None,
        git_commit:   str = "",
        created_by:   str = "",
    ) -> StrategyEntry:
        now = datetime.now()
        st  = StrategyEntry(
            strategy_id = gen_strategy_id(),
            name        = name,
            version     = version,
            description = description,
            status      = StrategyStatus.IDEA,
            author      = author,
            feature_ids = feature_ids or [],
            dataset_ids = dataset_ids or [],
            tags        = tags or [],
            git_commit  = git_commit,
            created_by  = created_by,
            created_at  = now,
            updated_at  = now,
        )
        self._st_repo.save(st)
        self.lineage.add_node(st.strategy_id, label=st.name, node_type="strategy")
        for fid in st.feature_ids:
            if self.lineage.get_node(fid):
                self.lineage.add_edge(fid, st.strategy_id)
        return st

    def get_strategy(self, strategy_id: str) -> Optional[StrategyEntry]:
        return self._st_repo.get(strategy_id)

    def list_strategies(self, status: Optional[StrategyStatus] = None) -> List[StrategyEntry]:
        return self._st_repo.query(status=status) if status else self._st_repo.list()

    def update_strategy(self, st: StrategyEntry) -> None:
        st.updated_at = datetime.now()
        self._st_repo.save(st)

    def delete_strategy(self, strategy_id: str) -> None:
        self._st_repo.delete(strategy_id)
        self.lineage.remove_node(strategy_id)

    def set_strategy_status(self, strategy_id: str, status: StrategyStatus) -> None:
        st = self._st_repo.get(strategy_id)
        if st:
            st.status = status; st.updated_at = datetime.now()
            self._st_repo.save(st)

    def add_strategy_version(
        self,
        strategy_id: str, version: str = "", git_commit: str = "",
        params: Optional[Dict[str, Any]] = None,
        note: str = "", created_by: str = "",
    ) -> Optional[StrategyVersion]:
        st = self._st_repo.get(strategy_id)
        if not st:
            return None
        ver = StrategyVersion(
            version_id  = gen_strategy_ver_id(),
            strategy_id = strategy_id,
            version     = version or st.version,
            git_commit  = git_commit,
            params      = params or {},
            note        = note,
            created_by  = created_by,
        )
        st.versions.append(ver)
        st.updated_at = datetime.now()
        self._st_repo.save(st)
        return ver

    def update_strategy_perf(
        self,
        strategy_id: str,
        annual_return: float = 0.0, max_drawdown: float = 0.0,
        sharpe: float = 0.0, sortino: float = 0.0,
        calmar: float = 0.0, win_rate: float = 0.0,
    ) -> None:
        st = self._st_repo.get(strategy_id)
        if st:
            st.annual_return = annual_return; st.max_drawdown = max_drawdown
            st.sharpe = sharpe; st.sortino = sortino
            st.calmar = calmar; st.win_rate = win_rate
            st.updated_at = datetime.now()
            self._st_repo.save(st)

    def search_strategies(self, keyword: str) -> List[StrategyEntry]:
        return self._st_repo.search(keyword, fields=["name","description","author","tags"])

    def top_by_sharpe(self, n: int = 10) -> List[StrategyEntry]:
        return sorted(self._st_repo.list(), key=lambda s: s.sharpe, reverse=True)[:n]

    # ==================================================================
    # Model
    # ==================================================================

    def register_model(
        self,
        name:         str,
        model_type:   str = "",
        framework:    str = "",
        description:  str = "",
        version:      str = "v1.0.0",
        author:       str = "",
        hyperparams:  Optional[Dict[str, Any]] = None,
        feature_ids:  Optional[List[str]] = None,
        dataset_ids:  Optional[List[str]] = None,
        git_commit:   str = "",
        tags:         Optional[List[str]] = None,
        created_by:   str = "",
    ) -> ModelEntry:
        now = datetime.now()
        ml  = ModelEntry(
            model_id    = gen_model_id(),
            name        = name,
            version     = version,
            description = description,
            status      = ModelStatus.TRAINING,
            model_type  = model_type,
            framework   = framework,
            author      = author,
            hyperparams = hyperparams or {},
            feature_ids = feature_ids or [],
            dataset_ids = dataset_ids or [],
            git_commit  = git_commit,
            tags        = tags or [],
            created_by  = created_by,
            created_at  = now,
            updated_at  = now,
        )
        self._ml_repo.save(ml)
        self.lineage.add_node(ml.model_id, label=ml.name, node_type="model")
        for fid in ml.feature_ids:
            if self.lineage.get_node(fid):
                self.lineage.add_edge(fid, ml.model_id)
        return ml

    def get_model(self, model_id: str) -> Optional[ModelEntry]:
        return self._ml_repo.get(model_id)

    def list_models(self, status: Optional[ModelStatus] = None) -> List[ModelEntry]:
        return self._ml_repo.query(status=status) if status else self._ml_repo.list()

    def update_model(self, ml: ModelEntry) -> None:
        ml.updated_at = datetime.now()
        self._ml_repo.save(ml)

    def delete_model(self, model_id: str) -> None:
        self._ml_repo.delete(model_id)
        self.lineage.remove_node(model_id)

    def set_model_status(self, model_id: str, status: ModelStatus) -> None:
        ml = self._ml_repo.get(model_id)
        if ml:
            ml.status = status; ml.updated_at = datetime.now()
            self._ml_repo.save(ml)

    def add_training_run(
        self,
        model_id: str, version: str = "",
        hyperparams: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        dataset_id: str = "", duration_sec: float = 0.0,
        artifact_path: str = "", note: str = "", created_by: str = "",
    ) -> Optional[TrainingRun]:
        ml = self._ml_repo.get(model_id)
        if not ml:
            return None
        run = TrainingRun(
            run_id        = gen_training_run_id(),
            model_id      = model_id,
            version       = version or ml.version,
            framework     = ml.framework,
            hyperparams   = hyperparams   or {},
            metrics       = metrics       or {},
            dataset_id    = dataset_id,
            duration_sec  = duration_sec,
            artifact_path = artifact_path,
            note          = note,
            created_by    = created_by,
        )
        ml.training_runs.append(run)
        if metrics:
            ml.accuracy = metrics.get("accuracy", ml.accuracy)
            ml.auc      = metrics.get("auc",      ml.auc)
            ml.f1       = metrics.get("f1",        ml.f1)
        ml.updated_at = datetime.now()
        self._ml_repo.save(ml)
        return run

    def deploy_model(self, model_id: str, deploy_env: str = "prod", endpoint: str = "") -> None:
        ml = self._ml_repo.get(model_id)
        if ml:
            ml.status = ModelStatus.DEPLOYED
            ml.deploy_env = deploy_env; ml.deploy_endpoint = endpoint
            ml.updated_at = datetime.now()
            self._ml_repo.save(ml)

    def search_models(self, keyword: str) -> List[ModelEntry]:
        return self._ml_repo.search(keyword, fields=["name","description","model_type","framework","tags"])

    def top_by_auc(self, n: int = 10) -> List[ModelEntry]:
        return sorted(self._ml_repo.list(), key=lambda m: m.auc, reverse=True)[:n]

    # ==================================================================
    # Stats
    # ==================================================================

    def stats(self) -> dict:
        return {
            "datasets":      self._ds_repo.count(),
            "features":      self._ft_repo.count(),
            "strategies":    self._st_repo.count(),
            "models":        self._ml_repo.count(),
            "lineage_nodes": self.lineage.node_count(),
            "lineage_edges": self.lineage.edge_count(),
        }
"""

txt = P.read_text(encoding="utf-8")
txt = txt.replace("    # PLACEHOLDER_STRATEGY_MODEL", APPEND)
P.write_text(txt, encoding="utf-8")
print("registry_engine.py appended OK, size:", P.stat().st_size)
