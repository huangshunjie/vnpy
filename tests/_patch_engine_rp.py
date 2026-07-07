"""Patch engine.py: add Report + Pipeline methods."""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\engine.py"
)
txt = P.read_text(encoding="utf-8")

# ── 1. imports ─────────────────────────────────────────────────────
txt = txt.replace(
    "from .model.backtest_model import BacktestRecord, DailyEquity",
    "from .model.backtest_model import BacktestRecord, DailyEquity\n"
    "from .model.report_model import ReportRecord, ReportSection\n"
    "from .model.pipeline_model import PipelineRecord, PipelineStepRecord, PipelineRun",
)

# ── 2. Report + Pipeline methods ────────────────────────────────────
METHODS = """
    # ------------------------------------------------------------------
    # Report Center — Phase 9
    # ------------------------------------------------------------------

    def _gen_report_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"RPT-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"RPT-{date_str}-{count:03d}"

    def create_report(
        self,
        title:        str,
        report_type:  str                  = "research",
        description:  str                  = "",
        author:       str                  = "",
        summary:      str                  = "",
        experiment_id: Optional[str]       = None,
        strategy_id:  Optional[str]        = None,
        backtest_id:  Optional[str]        = None,
        feature_ids:  Optional[List[str]]  = None,
        model_ids:    Optional[List[str]]  = None,
        output_path:  str                  = "",
        tags:         Optional[List[str]]  = None,
    ) -> ReportRecord:
        now = datetime.now()
        record = ReportRecord(
            report_id     = self._gen_report_id(),
            title         = title,
            report_type   = report_type,
            description   = description,
            author        = author,
            summary       = summary,
            experiment_id = experiment_id,
            strategy_id   = strategy_id,
            backtest_id   = backtest_id,
            feature_ids   = feature_ids or [],
            model_ids     = model_ids or [],
            output_path   = output_path,
            tags          = tags or [],
            created_by    = author,
            created_at    = now,
            updated_at    = now,
        )
        self.report_registry.create(record)
        self._put(EVENT_REPORT_CREATED, record)
        return record

    def update_report(self, record: ReportRecord) -> None:
        record.updated_at = datetime.now()
        self.report_registry.update(record)
        self._put(EVENT_REPORT_UPDATED, record)

    def delete_report(self, report_id: str) -> None:
        self.report_registry.delete(report_id)

    def get_report(self, report_id: str) -> Optional[ReportRecord]:
        return self.report_registry.get(report_id)

    def list_reports(
        self,
        report_type:   Optional[str]  = None,
        author:        Optional[str]  = None,
        tag:           Optional[str]  = None,
        published:     Optional[bool] = None,
    ) -> List[ReportRecord]:
        return self.report_registry.filter(
            report_type=report_type, author=author,
            tag=tag, published=published,
        )

    def search_reports(self, keyword: str) -> List[ReportRecord]:
        return self.report_registry.search(keyword)

    def add_report_section(
        self, report_id: str, title: str,
        content: str = "", order: int = 0,
    ) -> Optional[ReportSection]:
        sec = self.report_registry.add_section(report_id, title, content, order)
        if sec:
            record = self.report_registry.get(report_id)
            self._put(EVENT_REPORT_UPDATED, record)
        return sec

    def update_report_section(
        self, report_id: str, section_id: str,
        title: str = "", content: str = "",
    ) -> None:
        self.report_registry.update_section(report_id, section_id, title, content)
        record = self.report_registry.get(report_id)
        if record:
            self._put(EVENT_REPORT_UPDATED, record)

    def remove_report_section(self, report_id: str, section_id: str) -> None:
        self.report_registry.remove_section(report_id, section_id)
        record = self.report_registry.get(report_id)
        if record:
            self._put(EVENT_REPORT_UPDATED, record)

    def publish_report(self, report_id: str) -> None:
        self.report_registry.publish(report_id)
        record = self.report_registry.get(report_id)
        if record:
            self._put(EVENT_REPORT_UPDATED, record)

    def unpublish_report(self, report_id: str) -> None:
        self.report_registry.unpublish(report_id)
        record = self.report_registry.get(report_id)
        if record:
            self._put(EVENT_REPORT_UPDATED, record)

    # ------------------------------------------------------------------
    # Pipeline Center — Phase 9
    # ------------------------------------------------------------------

    def _gen_pipeline_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"PL-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"PL-{date_str}-{count:03d}"

    def create_pipeline(
        self,
        name:         str,
        description:  str                 = "",
        author:       str                 = "",
        schedule:     str                 = "",
        experiment_id: Optional[str]      = None,
        strategy_id:  Optional[str]       = None,
        dataset_ids:  Optional[List[str]] = None,
        feature_ids:  Optional[List[str]] = None,
        tags:         Optional[List[str]] = None,
    ) -> PipelineRecord:
        now = datetime.now()
        record = PipelineRecord(
            pipeline_id   = self._gen_pipeline_id(),
            name          = name,
            description   = description,
            author        = author,
            schedule      = schedule,
            experiment_id = experiment_id,
            strategy_id   = strategy_id,
            dataset_ids   = dataset_ids or [],
            feature_ids   = feature_ids or [],
            tags          = tags or [],
            created_by    = author,
            created_at    = now,
            updated_at    = now,
        )
        self.pipeline_registry.create(record)
        self._put(EVENT_PIPELINE_CREATED, record)
        return record

    def update_pipeline(self, record: PipelineRecord) -> None:
        record.updated_at = datetime.now()
        self.pipeline_registry.update(record)
        self._put(EVENT_PIPELINE_UPDATED, record)

    def delete_pipeline(self, pipeline_id: str) -> None:
        self.pipeline_registry.delete(pipeline_id)

    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineRecord]:
        return self.pipeline_registry.get(pipeline_id)

    def list_pipelines(
        self,
        status: Optional[PipelineStatus] = None,
        tag:    Optional[str]            = None,
        author: Optional[str]            = None,
    ) -> List[PipelineRecord]:
        return self.pipeline_registry.filter(status=status, tag=tag, author=author)

    def search_pipelines(self, keyword: str) -> List[PipelineRecord]:
        return self.pipeline_registry.search(keyword)

    def add_pipeline_step(
        self,
        pipeline_id: str,
        name:        str,
        step_type:   str                       = "custom",
        params:      Optional[Dict[str, Any]]  = None,
        depends_on:  Optional[List[str]]       = None,
        timeout_sec: int                       = 3600,
    ) -> Optional[PipelineStepRecord]:
        step = self.pipeline_registry.add_step(
            pipeline_id, name, step_type, params, depends_on, timeout_sec)
        if step:
            record = self.pipeline_registry.get(pipeline_id)
            self._put(EVENT_PIPELINE_UPDATED, record)
        return step

    def remove_pipeline_step(self, pipeline_id: str, step_id: str) -> None:
        self.pipeline_registry.remove_step(pipeline_id, step_id)
        record = self.pipeline_registry.get(pipeline_id)
        if record:
            self._put(EVENT_PIPELINE_UPDATED, record)

    def run_pipeline(
        self, pipeline_id: str, trigger: str = "manual"
    ) -> Optional[PipelineRun]:
        run = self.pipeline_registry.start(pipeline_id, trigger)
        if run:
            record = self.pipeline_registry.get(pipeline_id)
            self._put(EVENT_PIPELINE_STARTED, record)
        return run

    def complete_pipeline(
        self, pipeline_id: str,
        duration_sec: float               = 0.0,
        step_logs: Optional[Dict[str, str]] = None,
    ) -> None:
        self.pipeline_registry.complete(pipeline_id, duration_sec, step_logs)
        record = self.pipeline_registry.get(pipeline_id)
        if record:
            self._put(EVENT_PIPELINE_COMPLETED, record)

    def fail_pipeline(
        self, pipeline_id: str,
        error_msg: str = "", failed_step: str = "",
    ) -> None:
        self.pipeline_registry.fail(pipeline_id, error_msg, failed_step)
        record = self.pipeline_registry.get(pipeline_id)
        if record:
            self._put(EVENT_PIPELINE_FAILED, record)

    def pause_pipeline(self, pipeline_id: str) -> None:
        self.pipeline_registry.pause(pipeline_id)
        record = self.pipeline_registry.get(pipeline_id)
        if record:
            self._put(EVENT_PIPELINE_UPDATED, record)

    def reset_pipeline(self, pipeline_id: str) -> None:
        self.pipeline_registry.reset(pipeline_id)
        record = self.pipeline_registry.get(pipeline_id)
        if record:
            self._put(EVENT_PIPELINE_UPDATED, record)

    def get_pipeline_runs(self, pipeline_id: str) -> List[PipelineRun]:
        return self.pipeline_registry.get_runs(pipeline_id)

"""

INSERT_BEFORE = (
    "    # ------------------------------------------------------------------\n"
    "    # 内部事件广播\n"
    "    # ------------------------------------------------------------------"
)
txt = txt.replace(INSERT_BEFORE, METHODS + INSERT_BEFORE)

# ── 3. 补全 PipelineStatus import ──────────────────────────────────
if "PipelineStatus" not in txt:
    txt = txt.replace(
        "from .constant import APP_NAME,",
        "from .constant import APP_NAME, PipelineStatus,",
    )

P.write_text(txt, encoding="utf-8")
print("engine.py Report+Pipeline patched OK, size:", P.stat().st_size)
