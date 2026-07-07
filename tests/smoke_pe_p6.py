"""smoke_pe_p6.py — Phase 6 smoke test"""
import json

# ── 1. ConfigDiffEngine ───────────────────────────────────────────
from vnpy.platform_engineering.engine.config_engine import (
    ConfigEngine, ConfigDiffEngine, DiffEntry,
)

diff = ConfigDiffEngine()
old = {"a": 1, "b": {"x": 10, "y": 20}, "c": "hello"}
new = {"a": 1, "b": {"x": 99, "z": 30}, "d": "world"}

entries = diff.diff(old, new)
ops = {e.key: e.op for e in entries}
assert ops.get("b.x")  == "change"
assert ops.get("b.y")  == "remove"
assert ops.get("b.z")  == "add"
assert ops.get("c")    == "remove"
assert ops.get("d")    == "add"
summary = diff.summary(entries)
assert "+2" in summary and "-2" in summary and "~1" in summary
print(f"  ConfigDiffEngine: PASSED  entries={len(entries)}  summary={summary}")

# ── 2. ConfigEngine CRUD ──────────────────────────────────────────
from vnpy.platform_engineering.constant import ConfigType

ce = ConfigEngine()

# create
c1 = ce.create_config(
    name="策略参数", config_type=ConfigType.STRATEGY,
    data={"lookback": 20, "threshold": 0.5},
    owner="alice", note="初始配置",
)
assert c1.config_id.startswith("CFG-")
assert len(c1.versions) == 1
assert c1.versions[0].data["lookback"] == 20
print(f"  create_config: PASSED  id={c1.config_id}  versions={len(c1.versions)}")

# update
ver2 = ce.update_config(c1.config_id, {"lookback": 30, "threshold": 0.6}, note="调参")
assert ver2 is not None
rec = ce.get_config(c1.config_id)
assert rec.current_data["lookback"] == 30
assert len(rec.versions) == 2
print(f"  update_config: PASSED  versions={len(rec.versions)}")

# patch
ce.patch_config(c1.config_id, {"extra": True}, note="追加字段")
rec = ce.get_config(c1.config_id)
assert rec.current_data.get("extra") is True
assert rec.current_data["lookback"] == 30   # merged
print(f"  patch_config: PASSED  keys={list(rec.current_data.keys())}")

# rollback
v1_id = rec.versions[0].version_id
ok = ce.rollback_config(c1.config_id, v1_id, note="回滚初始")
assert ok
rec = ce.get_config(c1.config_id)
assert rec.current_data["lookback"] == 20
assert "extra" not in rec.current_data
print(f"  rollback_config: PASSED  lookback={rec.current_data['lookback']}")

# lock prevents update
ce.lock(c1.config_id)
assert ce.get_config(c1.config_id).is_locked
try:
    ce.update_config(c1.config_id, {"x": 1})
    assert False, "should raise"
except ValueError:
    pass
try:
    ce.delete_config(c1.config_id)
    assert False, "should raise"
except ValueError:
    pass
ce.unlock(c1.config_id)
assert not ce.get_config(c1.config_id).is_locked
print("  lock/unlock: PASSED")

# delete
c2 = ce.create_config("临时配置", data={"tmp": True})
ce.delete_config(c2.config_id)
assert ce.get_config(c2.config_id) is None
print("  delete_config: PASSED")

# list + search + filter
c3 = ce.create_config("风控参数", config_type=ConfigType.RISK, data={"max_pos": 100})
all_cfgs = ce.list_configs()
assert len(all_cfgs) >= 2
risk_cfgs = ce.list_configs(config_type=ConfigType.RISK)
assert any(c.config_type == ConfigType.RISK for c in risk_cfgs)
results = ce.search_configs("风控")
assert len(results) >= 1
print(f"  list/search: PASSED  total={len(all_cfgs)}  risk={len(risk_cfgs)}")

# diff_versions
entries2, summary2 = ce.diff_versions(
    c1.config_id,
    c1.versions[0].version_id,
    c1.versions[1].version_id,
)
assert len(entries2) >= 1
print(f"  diff_versions: PASSED  entries={len(entries2)}  summary={summary2}")

# diff_with_current
entries3, summary3 = ce.diff_with_current(c1.config_id, c1.versions[0].version_id)
print(f"  diff_with_current: PASSED  entries={len(entries3)}")

# export / import
json_str = ce.export_config(c1.config_id)
obj = json.loads(json_str)
assert obj["name"] == "策略参数"
c_imported = ce.import_config(json_str, created_by="test", note="导入测试")
assert c_imported.current_data == c1.current_data
print(f"  export/import: PASSED  imported_id={c_imported.config_id}")

# callback
fired = []
ce.on_config_changed(lambda r, a: fired.append(a))
ce.update_config(c1.config_id, {"lookback": 50}, note="回调测试")
assert "update" in fired
print(f"  on_config_changed: PASSED  fired={fired}")

# stats
s = ce.stats()
assert s["total"] >= 2
assert "by_type" in s
assert s["total_versions"] >= 5
print(f"  stats: PASSED  {s}")

# ── 3. UI class imports ───────────────────────────────────────────
from vnpy.platform_engineering.ui.config import (
    ConfigTab, ConfigList, DetailPanel, CreateConfigDialog,
    _JsonHighlighter, TYPE_COLOR, ROLE_ID,
)
assert len(TYPE_COLOR) == 5
assert hasattr(ConfigList,           "refresh")
assert hasattr(DetailPanel,          "load")
assert hasattr(ConfigTab,            "_refresh")
assert hasattr(CreateConfigDialog,   "get_data")
print("  ConfigTab UI: PASSED")

# ── 4. stub_tabs re-export ────────────────────────────────────────
from vnpy.platform_engineering.ui.stub_tabs import (
    ConfigTab as CT2, DashboardTab, ObservabilityTab,
    TaskTab, DeploymentTab, StrategyHealthTab, LogTab,
    ApiTab, SecurityTab,
)
assert ConfigTab is CT2
print("  stub_tabs re-export: PASSED")

# ── 5. Phase 1-5 regression ──────────────────────────────────────
from vnpy.platform_engineering import PlatformEngineeringApp
from vnpy.platform_engineering.engine.health_engine import HealthEngine
from vnpy.platform_engineering.model.health import HealthMetricSnapshot
from datetime import datetime
he = HealthEngine()
he.register_strategy("S1", "Test")
snap = HealthMetricSnapshot(
    sharpe=1.5, max_drawdown=0.08, win_rate=0.58,
    risk_exposure=0.18, ic_mean=0.06, alpha_decay=0.12,
    order_delay_ms=180.0, fill_rate=0.97, slippage_bps=4.0,
    updated_at=datetime.now(),
)
he.update_snapshot("S1", snap)
assert he.get_health("S1").score >= 80
print("  Phase1-5 regression: PASSED")

print()
print("=== Phase 6 Smoke Test: ALL PASSED ===")
