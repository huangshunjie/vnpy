"""
platform_engineering/engine/api_engine.py
ApiEngine 完整版 — Phase 7
路由注册 + 中间件链 + 请求日志 + 限流 + 认证钩子 + ApiRouter
"""
from __future__ import annotations

import time
import uuid
from collections import deque, defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── data types ────────────────────────────────────────────────────

class ApiRequest:
    __slots__ = ("request_id", "path", "method", "params",
                 "headers", "body", "caller", "timestamp")

    def __init__(self, path: str, method: str,
                 params: dict = None, headers: dict = None,
                 body: Any = None, caller: str = "") -> None:
        self.request_id = "REQ-" + uuid.uuid4().hex[:8].upper()
        self.path       = path
        self.method     = method.upper()
        self.params     = params or {}
        self.headers    = headers or {}
        self.body       = body
        self.caller     = caller
        self.timestamp  = datetime.now()


class ApiResponse:
    __slots__ = ("request_id", "status_code", "data",
                 "error", "latency_ms", "timestamp")

    def __init__(self, request_id: str, status_code: int,
                 data: Any = None, error: str = "") -> None:
        self.request_id  = request_id
        self.status_code = status_code
        self.data        = data
        self.error       = error
        self.latency_ms  = 0.0
        self.timestamp   = datetime.now()

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class RequestLogEntry:
    __slots__ = ("request_id", "path", "method", "caller",
                 "status_code", "latency_ms", "error", "timestamp")

    def __init__(self, req: ApiRequest, resp: ApiResponse) -> None:
        self.request_id  = req.request_id
        self.path        = req.path
        self.method      = req.method
        self.caller      = req.caller
        self.status_code = resp.status_code
        self.latency_ms  = resp.latency_ms
        self.error       = resp.error
        self.timestamp   = req.timestamp


# ── route ─────────────────────────────────────────────────────────

class Route:
    def __init__(
        self,
        path:        str,
        handler:     Callable[[ApiRequest], Any],
        methods:     List[str]  = None,
        description: str        = "",
        group:       str        = "",
        auth_required: bool     = False,
        rate_limit:  int        = 0,       # requests/min, 0 = no limit
    ) -> None:
        self.route_id     = "RTE-" + uuid.uuid4().hex[:6].upper()
        self.path         = path
        self.handler      = handler
        self.methods      = [m.upper() for m in (methods or ["GET"])]
        self.description  = description
        self.group        = group
        self.auth_required = auth_required
        self.rate_limit   = rate_limit
        self.call_count   = 0
        self.error_count  = 0
        self.total_latency= 0.0
        self.created_at   = datetime.now()

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency / self.call_count if self.call_count else 0.0


# ── middleware ────────────────────────────────────────────────────

class Middleware:
    """基类中间件。"""
    name: str = "base"

    def before(self, req: ApiRequest) -> Optional[ApiResponse]:
        """返回 None 表示继续，返回 ApiResponse 表示短路。"""
        return None

    def after(self, req: ApiRequest, resp: ApiResponse) -> None:
        pass


class LoggingMiddleware(Middleware):
    name = "logging"

    def __init__(self, log_store: deque) -> None:
        self._store = log_store

    def after(self, req: ApiRequest, resp: ApiResponse) -> None:
        self._store.appendleft(RequestLogEntry(req, resp))
        if len(self._store) > 1000:
            self._store.pop()


class RateLimitMiddleware(Middleware):
    """简单滑动窗口限流（每路由每分钟）。"""
    name = "rate_limit"

    def __init__(self) -> None:
        self._windows: Dict[str, deque] = defaultdict(deque)

    def check(self, route: Route) -> bool:
        if route.rate_limit <= 0:
            return True
        key = route.route_id
        now = time.time()
        win = self._windows[key]
        # remove entries older than 60s
        while win and win[-1] < now - 60:
            win.pop()
        if len(win) >= route.rate_limit:
            return False
        win.appendleft(now)
        return True


class AuthMiddleware(Middleware):
    """认证钩子中间件，注入自定义校验函数。"""
    name = "auth"

    def __init__(self) -> None:
        self._auth_fn: Optional[Callable[[ApiRequest], bool]] = None

    def set_auth_fn(self, fn: Callable[[ApiRequest], bool]) -> None:
        self._auth_fn = fn

    def before(self, req: ApiRequest) -> Optional[ApiResponse]:
        if self._auth_fn and not self._auth_fn(req):
            return ApiResponse(req.request_id, 401, error="Unauthorized")
        return None


# ── ApiRouter ─────────────────────────────────────────────────────

class ApiRouter:
    """
    路由分组，支持 prefix + version。
    router = ApiRouter("/api/v1", group="strategy")
    router.get("/health", handler)
    router.post("/run", handler, auth_required=True)
    """

    def __init__(self, prefix: str = "", group: str = "",
                 version: str = "") -> None:
        self.prefix  = prefix.rstrip("/")
        self.group   = group
        self.version = version
        self._routes: List[Route] = []

    def _add(self, path: str, handler: Callable,
             methods: List[str], **kw) -> Route:
        full_path = self.prefix + path
        r = Route(full_path, handler, methods=methods,
                  group=self.group, **kw)
        self._routes.append(r)
        return r

    def get(self, path: str, handler: Callable, **kw) -> Route:
        return self._add(path, handler, ["GET"], **kw)

    def post(self, path: str, handler: Callable, **kw) -> Route:
        return self._add(path, handler, ["POST"], **kw)

    def put(self, path: str, handler: Callable, **kw) -> Route:
        return self._add(path, handler, ["PUT"], **kw)

    def delete(self, path: str, handler: Callable, **kw) -> Route:
        return self._add(path, handler, ["DELETE"], **kw)

    @property
    def routes(self) -> List[Route]:
        return self._routes


# ── ApiEngine ─────────────────────────────────────────────────────

class ApiEngine:
    """
    统一 API 网关引擎。
    - register(path, handler, methods, ...)  注册单条路由
    - include_router(router)                 批量注册路由分组
    - call(path, method, params, ...)        内部调用
    - add_middleware(mw)                     添加中间件
    - set_auth_fn(fn)                        设置认证函数
    - list_routes()                          查询路由
    - list_logs(n)                           最近 n 条请求日志
    - stats()                                汇总统计
    """

    MAX_LOG = 1000

    def __init__(self) -> None:
        self._routes:  Dict[str, Route]  = {}     # key = "METHOD:path" per-method registration
        self._log:     deque             = deque()
        self._rate_mw  = RateLimitMiddleware()
        self._auth_mw  = AuthMiddleware()
        self._log_mw   = LoggingMiddleware(self._log)
        self._middlewares: List[Middleware] = [
            self._auth_mw,
            self._rate_mw,
        ]
        self._after_mws: List[Middleware] = [self._log_mw]
        self._total_calls  = 0
        self._total_errors = 0

    def start(self) -> None: pass
    def stop(self)  -> None: pass

    # ── registration ──────────────────────────────────────────────

    def register(
        self,
        path:         str,
        handler:      Callable[[ApiRequest], Any],
        methods:      List[str] = None,
        description:  str       = "",
        group:        str       = "",
        auth_required: bool     = False,
        rate_limit:   int       = 0,
    ) -> Route:
        methods = methods or ["GET"]
        route = Route(path, handler,
                      methods=methods,
                      description=description,
                      group=group,
                      auth_required=auth_required,
                      rate_limit=rate_limit)
        for m in route.methods:
            self._routes[m.upper() + ":" + path] = route
        return route

    def include_router(self, router: ApiRouter) -> None:
        for r in router.routes:
            for m in r.methods:
                self._routes[m.upper() + ":" + r.path] = r

    def unregister(self, path: str) -> bool:
        removed = False
        for key in list(self._routes):
            if self._routes[key].path == path:
                del self._routes[key]; removed = True
        return removed

    # ── middleware ────────────────────────────────────────────────

    def add_middleware(self, mw: Middleware) -> None:
        self._middlewares.append(mw)

    def set_auth_fn(self, fn: Callable[[ApiRequest], bool]) -> None:
        self._auth_mw.set_auth_fn(fn)

    # ── call ──────────────────────────────────────────────────────

    def call(
        self,
        path:    str,
        method:  str   = "GET",
        params:  dict  = None,
        headers: dict  = None,
        body:    Any   = None,
        caller:  str   = "",
    ) -> ApiResponse:
        req = ApiRequest(path, method, params=params,
                         headers=headers, body=body, caller=caller)
        t0  = time.perf_counter()

        route = self._routes.get(req.method + ":" + path)
        if route is None:
            # check if path exists under any method → 405
            path_exists = any(
                r.path == path for r in self._routes.values())
            if path_exists:
                resp = ApiResponse(req.request_id, 405,
                                   error=f"Method {req.method} not allowed")
            else:
                resp = ApiResponse(req.request_id, 404,
                                   error=f"Route not found: {path}")
            resp.latency_ms = (time.perf_counter() - t0) * 1000
            self._after(req, resp)
            return resp

        # auth check
        if route.auth_required:
            early = self._auth_mw.before(req)
            if early:
                early.latency_ms = (time.perf_counter() - t0) * 1000
                self._after(req, early)
                return early

        # rate limit
        if not self._rate_mw.check(route):
            resp = ApiResponse(req.request_id, 429,
                               error="Rate limit exceeded")
            resp.latency_ms = (time.perf_counter() - t0) * 1000
            self._after(req, resp)
            return resp

        # before middlewares (custom)
        for mw in self._middlewares[2:]:   # skip auth/rate already handled
            early = mw.before(req)
            if early:
                early.latency_ms = (time.perf_counter() - t0) * 1000
                self._after(req, early)
                return early

        # execute handler
        try:
            result = route.handler(req)
            resp   = ApiResponse(req.request_id, 200, data=result)
        except Exception as e:
            resp = ApiResponse(req.request_id, 500, error=str(e))
            route.error_count += 1
            self._total_errors += 1

        resp.latency_ms    = (time.perf_counter() - t0) * 1000
        route.call_count  += 1
        route.total_latency += resp.latency_ms
        self._total_calls  += 1
        self._after(req, resp)
        return resp

    def _after(self, req: ApiRequest, resp: ApiResponse) -> None:
        for mw in self._after_mws:
            try:
                mw.after(req, resp)
            except Exception:
                pass

    # ── query ─────────────────────────────────────────────────────

    def list_routes(
        self, group: Optional[str] = None
    ) -> List[Route]:
        seen = {}
        for r in self._routes.values():
            seen[r.route_id] = r
        items = list(seen.values())
        if group:
            items = [r for r in items if r.group == group]
        return sorted(items, key=lambda r: r.path)

    def get_route(self, path: str, method: str = "GET") -> Optional[Route]:
        return self._routes.get(method.upper() + ":" + path)

    def list_logs(
        self, n: int = 100,
        path_filter: str = "",
        method_filter: str = "",
    ) -> List[RequestLogEntry]:
        logs = list(self._log)
        if path_filter:
            logs = [l for l in logs if path_filter in l.path]
        if method_filter:
            logs = [l for l in logs if l.method == method_filter.upper()]
        return logs[:n]

    # ── stats ─────────────────────────────────────────────────────

    def stats(self) -> dict:
        routes = list(self._routes.values())
        total_latency = sum(r.total_latency for r in routes)
        total_calls   = sum(r.call_count for r in routes)
        return {
            "routes":       len(routes),
            "total_calls":  self._total_calls,
            "total_errors": self._total_errors,
            "avg_latency_ms": round(total_latency / total_calls, 2)
                              if total_calls else 0.0,
            "error_rate":   round(self._total_errors / self._total_calls, 4)
                            if self._total_calls else 0.0,
            "log_entries":  len(self._log),
            "groups":       list({r.group for r in routes if r.group}),
        }
