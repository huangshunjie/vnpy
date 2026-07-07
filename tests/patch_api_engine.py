"""patch_api_engine.py — switch route key to METHOD:path"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\engine\api_engine.py"
)
src = P.read_text(encoding="utf-8")

# 1. key comment
src = src.replace(
    '# key = path',
    '# key = "METHOD:path" per-method registration'
)

# 2. register: one entry per method
old = (
    '        route = Route(path, handler,\n'
    '                      methods=methods or ["GET"],\n'
    '                      description=description,\n'
    '                      group=group,\n'
    '                      auth_required=auth_required,\n'
    '                      rate_limit=rate_limit)\n'
    '        self._routes[path] = route\n'
    '        return route'
)
new = (
    '        methods = methods or ["GET"]\n'
    '        route = Route(path, handler,\n'
    '                      methods=methods,\n'
    '                      description=description,\n'
    '                      group=group,\n'
    '                      auth_required=auth_required,\n'
    '                      rate_limit=rate_limit)\n'
    '        for m in route.methods:\n'
    '            self._routes[m.upper() + ":" + path] = route\n'
    '        return route'
)
assert old in src, "register block not found"
src = src.replace(old, new, 1)

# 3. include_router
old = (
    '    def include_router(self, router: ApiRouter) -> None:\n'
    '        for r in router.routes:\n'
    '            self._routes[r.path] = r'
)
new = (
    '    def include_router(self, router: ApiRouter) -> None:\n'
    '        for r in router.routes:\n'
    '            for m in r.methods:\n'
    '                self._routes[m.upper() + ":" + r.path] = r'
)
assert old in src, "include_router block not found"
src = src.replace(old, new, 1)

# 4. unregister
old = (
    '    def unregister(self, path: str) -> bool:\n'
    '        return self._routes.pop(path, None) is not None'
)
new = (
    '    def unregister(self, path: str) -> bool:\n'
    '        removed = False\n'
    '        for key in list(self._routes):\n'
    '            if self._routes[key].path == path:\n'
    '                del self._routes[key]; removed = True\n'
    '        return removed'
)
assert old in src, "unregister block not found"
src = src.replace(old, new, 1)

# 5. call — look up METHOD:path
old = '        route = self._routes.get(path)\n'
new = '        route = self._routes.get(req.method + ":" + path)\n'
assert old in src, "call lookup not found"
src = src.replace(old, new, 1)

# 6. get_route
old = (
    '    def get_route(self, path: str) -> Optional[Route]:\n'
    '        return self._routes.get(path)'
)
new = (
    '    def get_route(self, path: str, method: str = "GET") -> Optional[Route]:\n'
    '        return self._routes.get(method.upper() + ":" + path)'
)
assert old in src, "get_route not found"
src = src.replace(old, new, 1)

# 7. list_routes: deduplicate by route_id
old = (
    '        items = list(self._routes.values())\n'
    '        if group:\n'
    '            items = [r for r in items if r.group == group]\n'
    '        return sorted(items, key=lambda r: r.path)'
)
new = (
    '        seen = {}\n'
    '        for r in self._routes.values():\n'
    '            seen[r.route_id] = r\n'
    '        items = list(seen.values())\n'
    '        if group:\n'
    '            items = [r for r in items if r.group == group]\n'
    '        return sorted(items, key=lambda r: r.path)'
)
assert old in src, "list_routes not found"
src = src.replace(old, new, 1)

ast.parse(src)
P.write_text(src, encoding="utf-8")
print("patched OK, lines:", len(src.splitlines()))
