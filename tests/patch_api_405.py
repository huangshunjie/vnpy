"""patch_api_405.py — fix 405 detection after METHOD:path key change"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\engine\api_engine.py"
)
src = P.read_text(encoding="utf-8")

old = (
    '        route = self._routes.get(req.method + ":" + path)\n'
    '        if route is None:\n'
    '            resp = ApiResponse(req.request_id, 404, error=f"Route not found: {path}")\n'
    '            resp.latency_ms = (time.perf_counter() - t0) * 1000\n'
    '            self._after(req, resp)\n'
    '            return resp\n'
    '\n'
    '        if req.method not in route.methods:\n'
    '            resp = ApiResponse(req.request_id, 405,\n'
    '                               error=f"Method {req.method} not allowed")\n'
    '            resp.latency_ms = (time.perf_counter() - t0) * 1000\n'
    '            self._after(req, resp)\n'
    '            return resp'
)

new = (
    '        route = self._routes.get(req.method + ":" + path)\n'
    '        if route is None:\n'
    '            # check if path exists under any method → 405\n'
    '            path_exists = any(\n'
    '                r.path == path for r in self._routes.values())\n'
    '            if path_exists:\n'
    '                resp = ApiResponse(req.request_id, 405,\n'
    '                                   error=f"Method {req.method} not allowed")\n'
    '            else:\n'
    '                resp = ApiResponse(req.request_id, 404,\n'
    '                                   error=f"Route not found: {path}")\n'
    '            resp.latency_ms = (time.perf_counter() - t0) * 1000\n'
    '            self._after(req, resp)\n'
    '            return resp'
)

assert old in src, f"target block not found"
src = src.replace(old, new, 1)
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("405 fix OK, lines:", len(src.splitlines()))
