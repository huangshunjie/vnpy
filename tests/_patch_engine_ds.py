"""Append Dataset Center methods to engine.py"""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\engine.py"
)

# 先在顶部 import 区增加 Dataset 相关 import
txt = P.read_text(encoding="utf-8")

# 追加 import
old_import = "from .constant import APP_NAME, ExperimentStatus"
new_import = "from .constant import APP_NAME, ExperimentStatus, DatasetStatus"
txt = txt.replace(old_import, new_import)

old_event_import = (
    "from .event import (\n"
    "    EVENT_EXPERIMENT_CREATED,\n"
    "    EVENT_EXPERIMENT_UPDATED,\n"
    "    EVENT_EXPERIMENT_DELETED,\n"
    ")"
)
new_event_import = (
    "from .event import (\n"
    "    EVENT_EXPERIMENT_CREATED,\n"
    "    EVENT_EXPERIMENT_UPDATED,\n"
    "    EVENT_EXPERIMENT_DELETED,\n"
    "    EVENT_DATASET_CREATED,\n"
    "    EVENT_DATASET_UPDATED,\n"
    "    EVENT_DATASET_DELETED,\n"
    ")"
)
txt = txt.replace(old_event_import, new_event_import)

old_model_import = "from .model.experiment_model import ExperimentRecord"
new_model_import = (
    "from .model.experiment_model import ExperimentRecord\n"
    "from .model.dataset_model import DatasetRecord, DatasetSnapshot"
)
txt = txt.replace(old_model_import, new_model_import)

P.write_text(txt, encoding="utf-8")

# 追加 Dataset 业务方法
METHODS = """
    # ------------------------------------------------------------------
    # Dataset Registry — Phase 3
    # ------------------------------------------------------------------

    def _gen_dataset_id(self) -> str:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        count = self._exp_counter.get(f"DS-{date_str}", 0) + 1
        self._exp_counter[f"DS-{date_str}"] = count
        return f"DS-{date_str}-{count:03d}"

    def register_dataset(
        self,
        name:         str,
        version:      str                   = "v1.0",
        description:  str                   = "",
        source:       str                   = "",
        symbols:      Optional[List[str]]   = None,
        start_date:   str                   = "",
        end_date:     str                   = "",
        fields:       Optional[List[str]]   = None,
        row_count:    int                   = 0,
        size_mb:      float                 = 0.0,
        tags:         Optional[List[str]]   = None,
        created_by:   str                   = "",
    ) -> DatasetRecord:
        now = datetime.now()
        record = DatasetRecord(
            dataset_id  = self._gen_dataset_id(),
            name        = name,
            version     = version,
            description = description,
            source      = source,
            symbols     = symbols or [],
            start_date  = start_date,
            end_date    = end_date,
            fields      = fields or [],
            row_count   = row_count,
            size_mb     = size_mb,
            tags        = tags or [],
            created_by  = created_by,
            created_at  = now,
            updated_at  = now,
        )
        self.dataset_registry.create(record)
        self._put(EVENT_DATASET_CREATED, record)
        return record

    def update_dataset(self, record: DatasetRecord) -> None:
        record.updated_at = datetime.now()
        self.dataset_registry.update(record)
        self._put(EVENT_DATASET_UPDATED, record)

    def delete_dataset(self, dataset_id: str) -> None:
        self.dataset_registry.delete(dataset_id)
        self._put(EVENT_DATASET_DELETED, dataset_id)

    def get_dataset(self, dataset_id: str) -> Optional[DatasetRecord]:
        return self.dataset_registry.get(dataset_id)

    def list_datasets(
        self,
        status: Optional[DatasetStatus] = None,
        source: Optional[str]           = None,
        tag:    Optional[str]           = None,
    ) -> List[DatasetRecord]:
        return self.dataset_registry.filter(status=status, source=source, tag=tag)

    def search_datasets(self, keyword: str) -> List[DatasetRecord]:
        return self.dataset_registry.search(keyword)

    def take_snapshot(self, dataset_id: str) -> Optional[DatasetSnapshot]:
        snap = self.dataset_registry.take_snapshot(dataset_id)
        if snap:
            record = self.dataset_registry.get(dataset_id)
            self._put(EVENT_DATASET_UPDATED, record)
        return snap

    def get_snapshots(self, dataset_id: str) -> List[DatasetSnapshot]:
        return self.dataset_registry.get_snapshots(dataset_id)

    def add_dependency(self, dataset_id: str, dep_id: str) -> None:
        self.dataset_registry.add_dependency(dataset_id, dep_id)
        record = self.dataset_registry.get(dataset_id)
        if record:
            self._put(EVENT_DATASET_UPDATED, record)

    def remove_dependency(self, dataset_id: str, dep_id: str) -> None:
        self.dataset_registry.remove_dependency(dataset_id, dep_id)
        record = self.dataset_registry.get(dataset_id)
        if record:
            self._put(EVENT_DATASET_UPDATED, record)

    def get_lineage(self, dataset_id: str) -> List[str]:
        return self.dataset_registry.get_lineage(dataset_id)

    def get_dependents(self, dataset_id: str) -> List[str]:
        return self.dataset_registry.get_dependents(dataset_id)

    def update_quality(
        self,
        dataset_id:    str,
        quality_score: float,
        metrics:       Optional[Dict[str, float]] = None,
    ) -> None:
        self.dataset_registry.update_quality(dataset_id, quality_score, metrics)
        record = self.dataset_registry.get(dataset_id)
        if record:
            self._put(EVENT_DATASET_UPDATED, record)
"""

with open(P, "r", encoding="utf-8") as f:
    content = f.read()

# 在 _put 方法之前插入 Dataset 方法
INSERT_BEFORE = "    # ------------------------------------------------------------------\n    # 内部事件广播\n    # ------------------------------------------------------------------"
content = content.replace(INSERT_BEFORE, METHODS + "\n" + INSERT_BEFORE)

with open(P, "w", encoding="utf-8") as f:
    f.write(content)

print("engine.py patched OK, size:", P.stat().st_size)
