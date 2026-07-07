"""append_gov_aliases.py — 追加 approve/reject/freeze/unfreeze 短名别名"""
import pathlib, ast

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\main_engine.py")
src = P.read_text(encoding="utf-8")

ALIASES = """
    # ==================================================================
    # 补充代理 — Governance 短名别名（Tab 用短名调用）
    # ==================================================================

    def approve(self, request_id: str, approver: str = "", comment: str = "") -> None:
        self.governance.approve(request_id, approver, comment)

    def reject(self, request_id: str, approver: str = "", comment: str = "") -> None:
        self.governance.reject(request_id, approver, comment)

    def freeze(self, **kw):
        return self.governance.freeze(**kw)

    def unfreeze(self, freeze_id: str, released_by: str = "") -> None:
        self.governance.unfreeze(freeze_id, released_by)
"""

if "    def approve(" not in src:
    src = src.rstrip() + "\n" + ALIASES + "\n"

ast.parse(src)
P.write_text(src, encoding="utf-8")
print("Aliases appended, lines:", len(src.splitlines()))
