"""
quant_research/registry/model_registry.py

ModelRegistry — Phase 6 完整实现。
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..model.model_model import MLModelRecord, TrainingRun
from ..constant import ModelStatus


class ModelRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, MLModelRecord] = {}
        self._run_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: MLModelRecord) -> MLModelRecord:
        self._records[record.model_id] = record
        return record

    def get(self, model_id: str) -> Optional[MLModelRecord]:
        return self._records.get(model_id)

    def list(self) -> List[MLModelRecord]:
        return list(self._records.values())

    def update(self, record: MLModelRecord) -> None:
        self._records[record.model_id] = record

    def delete(self, model_id: str) -> None:
        self._records.pop(model_id, None)

    def clear(self) -> None:
        self._records.clear()
        self._run_counter.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        status:     Optional[ModelStatus] = None,
        model_type: Optional[str]         = None,
        tag:        Optional[str]         = None,
        author:     Optional[str]         = None,
    ) -> List[MLModelRecord]:
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if model_type is not None:
            result = [r for r in result
                      if model_type.lower() in r.model_type.lower()]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        if author is not None:
            result = [r for r in result
                      if author.lower() in r.author.lower()]
        return result

    def search(self, keyword: str) -> List[MLModelRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.name.lower()
            or kw in r.description.lower()
            or kw in r.model_type.lower()
            or kw in r.author.lower()
            or kw in r.framework.lower()
            or any(kw in t.lower() for t in r.tags)
        ]

    # ------------------------------------------------------------------
    # 评估指标
    # ------------------------------------------------------------------

    def update_eval_metrics(
        self,
        model_id:      str,
        accuracy:      float                    = 0.0,
        auc:           float                    = 0.0,
        rmse:          float                    = 0.0,
        mae:           float                    = 0.0,
        f1:            float                    = 0.0,
        custom_metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        record = self._records.get(model_id)
        if record:
            record.accuracy       = accuracy
            record.auc            = auc
            record.rmse           = rmse
            record.mae            = mae
            record.f1             = f1
            record.custom_metrics = custom_metrics or {}
            record.updated_at     = datetime.now()

    # ------------------------------------------------------------------
    # 训练历史
    # ------------------------------------------------------------------

    def add_training_run(
        self,
        model_id:     str,
        run_note:     str                    = "",
        hyperparams:  Optional[Dict[str, Any]] = None,
        metrics:      Optional[Dict[str, float]] = None,
        dataset_id:   str                    = "",
        duration_sec: float                  = 0.0,
        created_by:   str                    = "",
    ) -> Optional[TrainingRun]:
        record = self._records.get(model_id)
        if record is None:
            return None
        count = self._run_counter.get(model_id, 0) + 1
        self._run_counter[model_id] = count
        now = datetime.now()
        run = TrainingRun(
            run_id       = f"RUN-{model_id}-{count:03d}",
            model_id     = model_id,
            run_note     = run_note,
            hyperparams  = hyperparams or {},
            metrics      = metrics or {},
            dataset_id   = dataset_id,
            duration_sec = duration_sec,
            started_at   = now,
            finished_at  = now,
            created_by   = created_by,
        )
        record.training_runs.append(run)
        record.updated_at = datetime.now()
        return run

    def get_training_runs(self, model_id: str) -> List[TrainingRun]:
        record = self._records.get(model_id)
        return list(record.training_runs) if record else []

    # ------------------------------------------------------------------
    # 部署 / 退役
    # ------------------------------------------------------------------

    def deploy(
        self,
        model_id:   str,
        env:        str = "",
        endpoint:   str = "",
    ) -> None:
        record = self._records.get(model_id)
        if record:
            record.status     = ModelStatus.DEPLOYED
            record.deploy_env = env
            record.endpoint   = endpoint
            record.deploy_at  = datetime.now()
            record.updated_at = datetime.now()

    def retire(self, model_id: str) -> None:
        record = self._records.get(model_id)
        if record:
            record.status     = ModelStatus.RETIRED
            record.retired_at = datetime.now()
            record.updated_at = datetime.now()

    def set_evaluated(self, model_id: str) -> None:
        record = self._records.get(model_id)
        if record:
            record.status     = ModelStatus.EVALUATED
            record.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # 关联资源
    # ------------------------------------------------------------------

    def link_feature(self, model_id: str, feature_id: str) -> None:
        r = self._records.get(model_id)
        if r and feature_id not in r.feature_ids:
            r.feature_ids.append(feature_id)
            r.updated_at = datetime.now()

    def unlink_feature(self, model_id: str, feature_id: str) -> None:
        r = self._records.get(model_id)
        if r and feature_id in r.feature_ids:
            r.feature_ids.remove(feature_id)
            r.updated_at = datetime.now()

    def link_dataset(self, model_id: str, dataset_id: str) -> None:
        r = self._records.get(model_id)
        if r and dataset_id not in r.dataset_ids:
            r.dataset_ids.append(dataset_id)
            r.updated_at = datetime.now()

    def link_strategy(self, model_id: str, strategy_id: str) -> None:
        r = self._records.get(model_id)
        if r and strategy_id not in r.strategy_ids:
            r.strategy_ids.append(strategy_id)
            r.updated_at = datetime.now()

    def link_experiment(self, model_id: str, experiment_id: str) -> None:
        r = self._records.get(model_id)
        if r and experiment_id not in r.experiment_ids:
            r.experiment_ids.append(experiment_id)
            r.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # 排行榜
    # ------------------------------------------------------------------

    def top_by_auc(self, n: int = 10) -> List[MLModelRecord]:
        active = [r for r in self._records.values()
                  if r.status != ModelStatus.RETIRED]
        return sorted(active, key=lambda r: r.auc, reverse=True)[:n]

    def top_by_accuracy(self, n: int = 10) -> List[MLModelRecord]:
        active = [r for r in self._records.values()
                  if r.status != ModelStatus.RETIRED]
        return sorted(active, key=lambda r: r.accuracy, reverse=True)[:n]
