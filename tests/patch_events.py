"""patch_events.py — 追加 Registry 事件常量到 event.py"""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\event.py"
)

APPEND = """
# ── Registry ──────────────────────────────────────────────────────
EVENT_RO_DS_CREATED    = "eRODsCreated"
EVENT_RO_DS_UPDATED    = "eRODsUpdated"
EVENT_RO_DS_DELETED    = "eRODsDeleted"

EVENT_RO_FT_CREATED    = "eROFtCreated"
EVENT_RO_FT_UPDATED    = "eROFtUpdated"
EVENT_RO_FT_DELETED    = "eROFtDeleted"

EVENT_RO_ST_CREATED    = "eROStCreated"
EVENT_RO_ST_UPDATED    = "eROStUpdated"
EVENT_RO_ST_DELETED    = "eROStDeleted"

EVENT_RO_ML_CREATED    = "eROMLCreated"
EVENT_RO_ML_UPDATED    = "eROMLUpdated"
EVENT_RO_ML_DELETED    = "eROMLDeleted"
EVENT_RO_ML_DEPLOYED   = "eROMLDeployed"
"""

src = P.read_text(encoding="utf-8")
if "EVENT_RO_DS_CREATED" not in src:
    P.write_text(src + APPEND, encoding="utf-8")
    print("events appended OK, total lines:", len(P.read_text(encoding="utf-8").splitlines()))
else:
    print("events already present")
