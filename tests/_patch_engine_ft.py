"""Patch engine.py: add Feature Center imports and methods."""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\engine.py"
)
txt = P.read_text(encoding="utf-8")

# ── 1. 追加 import ─────────────────────────────────────────────────
txt = txt.replace(
    "from .constant import APP_NAME, ExperimentStatus, DatasetStatus",
    "from .constant import APP_NAME, ExperimentStatus, DatasetStatus, FeatureStatus",
)
txt = txt.replace(
    "    EVENT_DATASET_CREATED,\n"
    "    EVENT_DATASET_UPDATED,\n"
    "    EVENT_DATASET_DELETED,\n"
    ")",
    "    EVENT_DATASET_CREATED,\n"
    "    EVENT_DATASET_UPDATED,\n"
    "    EVENT_DATASET_DELETED,\n"
    "    EVENT_FEATURE_CREATED,\n"
    "    EVENT_FEATURE_UPDATED,\n"
    "    EVENT_FEATURE_DELETED,\n"
    ")",
)
txt = txt.replace(
    "from .model.dataset_model import DatasetRecord, DatasetSnapshot",
    "from .model.dataset_model import DatasetRecord, DatasetSnapshot\n"
    "from .model.feature_model import FeatureRecord, ICRecord",
)

# ── 2. 追加 Feature 方法（插在 _put 之前）─────────────────────────
FEATURE_METHODS = """
    # ------------------------------------------------------------------
    # Feature Registry — Phase 4
    # ------------------------------------------------------------------

    def _gen_feature_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"FT-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"FT-{date_str}-{count:03d}"

    def register_feature(
        self,
        name:         str,
        version:      str                  = "v1.0",
        description:  str                  = "",
        category:     str                  = "",
        formula:      str                  = "",
        author:       str                  = "",
        tags:         Optional[List[str]]  = None,
        dependencies: Optional[List[str]]  = None,
        dataset_ids:  Optional[List[str]]  = None,
    ) -> FeatureRecord:
        now = datetime.now()
        record = FeatureRecord(
            feature_id   = self._gen_feature_id(),
            name         = name,
            version      = version,
            description  = description,
            category     = category,
            formula      = formula,
            author       = author,
            tags         = tags or [],
            dependencies = dependencies or [],
            dataset_ids  = dataset_ids or [],
            created_at   = now,
            updated_at   = now,
        )
        self.feature_registry.create(record)
        self._put(EVENT_FEATURE_CREATED, record)
        return record

    def update_feature(self, record: FeatureRecord) -> None:
        record.updated_at = datetime.now()
        self.feature_registry.update(record)
        self._put(EVENT_FEATURE_UPDATED, record)

    def delete_feature(self, feature_id: str) -> None:
        self.feature_registry.delete(feature_id)
        self._put(EVENT_FEATURE_DELETED, feature_id)

    def get_feature(self, feature_id: str) -> Optional[FeatureRecord]:
        return self.feature_registry.get(feature_id)

    def list_features(
        self,
        status:      Optional[FeatureStatus] = None,
        category:    Optional[str]           = None,
        tag:         Optional[str]           = None,
        author:      Optional[str]           = None,
        active_only: bool                    = False,
    ) -> List[FeatureRecord]:
        return self.feature_registry.filter(
            status=status, category=category,
            tag=tag, author=author, active_only=active_only,
        )

    def search_features(self, keyword: str) -> List[FeatureRecord]:
        return self.feature_registry.search(keyword)

    def update_ic_metrics(
        self,
        feature_id: str,
        ic:         float,
        rank_ic:    float,
        ir:         float,
        icir:       float        = 0.0,
        coverage:   float        = 0.0,
        period:     str          = "",
        dataset_id: str          = "",
    ) -> Optional[ICRecord]:
        eval_rec = self.feature_registry.update_ic_metrics(
            feature_id, ic, rank_ic, ir, icir, coverage, period, dataset_id
        )
        if eval_rec:
            record = self.feature_registry.get(feature_id)
            self._put(EVENT_FEATURE_UPDATED, record)
        return eval_rec

    def get_ic_history(self, feature_id: str) -> List[ICRecord]:
        return self.feature_registry.get_ic_history(feature_id)

    def deprecate_feature(self, feature_id: str, reason: str = "") -> None:
        self.feature_registry.deprecate(feature_id, reason)
        record = self.feature_registry.get(feature_id)
        if record:
            self._put(EVENT_FEATURE_UPDATED, record)

    def restore_feature(self, feature_id: str) -> None:
        self.feature_registry.restore(feature_id)
        record = self.feature_registry.get(feature_id)
        if record:
            self._put(EVENT_FEATURE_UPDATED, record)

    def add_feature_dependency(self, feature_id: str, dep_id: str) -> None:
        self.feature_registry.add_dependency(feature_id, dep_id)
        record = self.feature_registry.get(feature_id)
        if record:
            self._put(EVENT_FEATURE_UPDATED, record)

    def remove_feature_dependency(self, feature_id: str, dep_id: str) -> None:
        self.feature_registry.remove_dependency(feature_id, dep_id)
        record = self.feature_registry.get(feature_id)
        if record:
            self._put(EVENT_FEATURE_UPDATED, record)

    def add_feature_dataset(self, feature_id: str, dataset_id: str) -> None:
        self.feature_registry.add_dataset(feature_id, dataset_id)
        record = self.feature_registry.get(feature_id)
        if record:
            self._put(EVENT_FEATURE_UPDATED, record)

    def get_feature_dependents(self, feature_id: str) -> List[str]:
        return self.feature_registry.get_dependents(feature_id)

    def top_features_by_ic(self, n: int = 10) -> List[FeatureRecord]:
        return self.feature_registry.top_by_ic(n)

    def top_features_by_icir(self, n: int = 10) -> List[FeatureRecord]:
        return self.feature_registry.top_by_icir(n)

"""

INSERT_BEFORE = (
    "    # ------------------------------------------------------------------\n"
    "    # 内部事件广播\n"
    "    # ------------------------------------------------------------------"
)
txt = txt.replace(INSERT_BEFORE, FEATURE_METHODS + INSERT_BEFORE)

P.write_text(txt, encoding="utf-8")
print("engine.py Feature methods patched OK, size:", P.stat().st_size)
