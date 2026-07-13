"""
research_ops/utils/id_gen.py

统一 ID 生成器。
格式：{PREFIX}-{YYYYMMDD}-{SEQ:04d}
前缀按模块区分，序列号在进程内单调递增。
"""
from __future__ import annotations
from datetime import datetime
from threading import Lock
from typing import Dict

_lock     = Lock()
_counters: Dict[str, int] = {}


def _next(prefix: str) -> str:
    """生成下一个 ID，线程安全。"""
    with _lock:
        date_str = datetime.now().strftime("%Y%m%d")
        key      = f"{prefix}-{date_str}"
        _counters[key] = _counters.get(key, 0) + 1
        return f"{key}-{_counters[key]:04d}"


# ── 公开 API ────────────────────────────────────────────────────────

def gen_workspace_id()   -> str: return _next("WS")
def gen_project_id()     -> str: return _next("PRJ")
def gen_folder_id()      -> str: return _next("FOL")

def gen_experiment_id()  -> str: return _next("EXP")
def gen_run_id()         -> str: return _next("RUN")

def gen_dataset_id()     -> str: return _next("DS")
def gen_dataset_ver_id() -> str: return _next("DSV")
def gen_feature_id()     -> str: return _next("FT")
def gen_ic_record_id()   -> str: return _next("ICR")
def gen_strategy_id()    -> str: return _next("ST")
def gen_strategy_ver_id()-> str: return _next("STV")
def gen_model_id()       -> str: return _next("ML")
def gen_training_run_id()-> str: return _next("TRN")

def gen_pipeline_id()    -> str: return _next("PL")
def gen_node_id()        -> str: return _next("NOD")
def gen_pl_run_id()      -> str: return _next("PLR")

def gen_report_id()      -> str: return _next("RPT")
def gen_section_id()     -> str: return _next("SEC")
def gen_template_id()    -> str: return _next("TPL")

def gen_note_id()        -> str: return _next("KBN")
def gen_card_id()        -> str: return _next("KBC")
def gen_case_id()        -> str: return _next("KBF")

def gen_request_id()     -> str: return _next("GOV")
def gen_freeze_id()      -> str: return _next("FRZ")
def gen_audit_id()       -> str: return _next("AUD")


def reset_counters() -> None:
    """仅用于测试，重置所有计数器。"""
    with _lock:
        _counters.clear()
