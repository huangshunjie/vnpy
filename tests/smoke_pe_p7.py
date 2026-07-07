"""smoke_pe_p7.py — Phase 7 smoke test"""

# ── 1. ApiEngine 基础功能 ─────────────────────────────────────────
from vnpy.platform_engineering.engine.api_engine import (
    ApiEngine, ApiRouter, ApiRequest, ApiResponse,
    Route, Middleware, LoggingMiddleware, RateLimitMiddleware,
    AuthMiddleware, RequestLogEntry,
)

ae = ApiEngine()

# register single route
ae.register("/health", lambda req: {"ok": True}, methods=["GET"],
            description="健康检查", group="system")
ae.register("/echo",   lambda req: {"echo": req.params},
            methods=["GET", "POST"], group="system")
ae.register("/strategy/list", lambda req: {"strategies": []},
            methods=["GET"], group="strategy")
ae.register("/strategy/run",  lambda req: {"started": True},
            methods=["POST"], group="strategy", auth_required=True)
ae.register("/error_route",   lambda req: (_ for _ in ()).throw(
    RuntimeError("forced error")), methods=["GET"])
assert len(ae.list_routes()) == 5
print(f"  register: PASSED  routes={len(ae.list_routes())}")

# GET /health
resp = ae.call("/health", "GET", caller="smoke")
assert resp.ok
assert resp.status_code == 200
assert resp.data["ok"] is True
assert resp.latency_ms >= 0
print(f"  call GET /health: PASSED  latency={resp.latency_ms:.2f}ms")

# POST /echo with params
resp2 = ae.call("/echo", "POST", params={"x": 42}, caller="test")
assert resp2.ok
assert resp2.data["echo"]["x"] == 42
print(f"  call POST /echo: PASSED")

# 404
resp3 = ae.call("/not/exist")
assert resp3.status_code == 404
print(f"  404: PASSED")

# 405 method not allowed
resp4 = ae.call("/health", "DELETE")
assert resp4.status_code == 405
print(f"  405: PASSED")

# 500 handler error
resp5 = ae.call("/error_route", "GET")
assert resp5.status_code == 500
assert resp5.error != ""
print(f"  500 handler error: PASSED")

# request log
logs = ae.list_logs(n=50)
assert len(logs) >= 4
print(f"  request_log: PASSED  entries={len(logs)}")

# path + method filter
get_logs = ae.list_logs(method_filter="GET")
assert all(l.method == "GET" for l in get_logs)
health_logs = ae.list_logs(path_filter="/health")
assert all("/health" in l.path for l in health_logs)
print(f"  log_filter: PASSED  get={len(get_logs)}  health={len(health_logs)}")

# auth middleware (no auth_fn set → passes by default)
resp_auth = ae.call("/strategy/run", "POST", caller="alice")
assert resp_auth.ok   # no auth_fn → passes
print(f"  auth_no_fn: PASSED  status={resp_auth.status_code}")

# set auth fn → reject
ae.set_auth_fn(lambda req: req.caller == "admin")
resp_rej = ae.call("/strategy/run", "POST", caller="alice")
assert resp_rej.status_code == 401
resp_ok  = ae.call("/strategy/run", "POST", caller="admin")
assert resp_ok.ok
print(f"  auth_fn: PASSED  alice={resp_rej.status_code}  admin={resp_ok.status_code}")
ae.set_auth_fn(None)   # reset

# rate limit (set low limit, trigger 429)
ae.register("/limited", lambda req: {"ok": True},
            methods=["GET"], rate_limit=2)
ae.call("/limited"); ae.call("/limited")
resp_429 = ae.call("/limited")
assert resp_429.status_code == 429
print(f"  rate_limit: PASSED  status={resp_429.status_code}")

# unregister
assert ae.unregister("/limited") is True
assert ae.get_route("/limited") is None
print(f"  unregister: PASSED")

# ── 2. ApiRouter ──────────────────────────────────────────────────
from vnpy.platform_engineering.engine.api_engine import ApiRouter

ae2 = ApiEngine()
router = ApiRouter(prefix="/api/v1", group="trading")
router.get("/orders",       lambda req: {"orders": []}, description="查询订单")
router.post("/orders",      lambda req: {"created": True}, description="创建订单")
router.delete("/orders/{id}", lambda req: {"deleted": True})
ae2.include_router(router)

assert len(ae2.list_routes(group="trading")) == 3
resp_r = ae2.call("/api/v1/orders", "GET")
assert resp_r.ok
print(f"  ApiRouter: PASSED  routes={len(ae2.list_routes(group='trading'))}")

# ── 3. stats ──────────────────────────────────────────────────────
s = ae.stats()
assert s["routes"]      >= 4
assert s["total_calls"] >= 5
assert "avg_latency_ms" in s
assert "error_rate"     in s
print(f"  stats: PASSED  {s}")

# route-level stats
route = ae.get_route("/health")
assert route.call_count >= 1
assert route.avg_latency_ms >= 0
print(f"  route_stats: PASSED  call_count={route.call_count}  avg_latency={route.avg_latency_ms:.2f}ms")

# ── 4. custom middleware ──────────────────────────────────────────
class CountMiddleware(Middleware):
    count = 0
    def before(self, req):
        CountMiddleware.count += 1
        return None

ae.add_middleware(CountMiddleware())
ae.call("/health", "GET")
assert CountMiddleware.count >= 1
print(f"  custom_middleware: PASSED  count={CountMiddleware.count}")

# ── 5. UI class imports ───────────────────────────────────────────
from vnpy.platform_engineering.ui.api import (
    ApiTab, RouteList, RequestLog, TestConsole, StatPanel,
    StatCard, RegisterRouteDialog,
    METHOD_COLOR, STATUS_COLOR, ROLE_PATH,
)
assert len(METHOD_COLOR) == 5
assert len(STATUS_COLOR) == 3
assert hasattr(RouteList,           "refresh")
assert hasattr(RequestLog,          "refresh")
assert hasattr(StatPanel,           "refresh")
assert hasattr(TestConsole,         "set_path")
assert hasattr(ApiTab,              "_refresh")
assert hasattr(RegisterRouteDialog, "get_path")
print("  ApiTab UI: PASSED")

# ── 6. stub_tabs re-export ────────────────────────────────────────
from vnpy.platform_engineering.ui.stub_tabs import (
    ApiTab as AT2, DashboardTab, ObservabilityTab,
    TaskTab, DeploymentTab, StrategyHealthTab,
    ConfigTab, SecurityTab, LogTab,
)
assert ApiTab is AT2
print("  stub_tabs re-export: PASSED")

# ── 7. Phase 1-6 regression ──────────────────────────────────────
from vnpy.platform_engineering import PlatformEngineeringApp
from vnpy.platform_engineering.engine.config_engine import ConfigEngine, ConfigDiffEngine
from vnpy.platform_engineering.constant import ConfigType
ce = ConfigEngine()
c  = ce.create_config("回归测试", config_type=ConfigType.SYSTEM, data={"v": 1})
ce.update_config(c.config_id, {"v": 2})
entries, _ = ce.diff_with_current(c.config_id, c.versions[0].version_id)
assert len(entries) >= 1
print("  Phase1-6 regression: PASSED")

print()
print("=== Phase 7 Smoke Test: ALL PASSED ===")
