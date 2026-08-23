"""
Smoke test for the daily-bar-click linkage fix.

Bug (pre-fix):
    ConditionMonitorWidget._connect_daily_click_handler() referenced
    `self._kline_tab` (which does NOT exist on the widget) and connected
    `chart.bar_clicked` to a non-existent slot `self._on_bar_clicked`.
    As a result the `chart.bar_clicked` signal was never wired up.

Fix:
    Walk through `self._daily_panel._kline_tab._chart` to fetch the
    chart, and connect `bar_clicked` to the real slot
    `self._on_daily_bar_clicked`.

This test avoids instantiating ConditionMonitorWidget (which is
unstable under veighna_studio's PySide6 build – it triggers a native
0xC0000409 in unrelated code paths during import).  Instead we do a
pure-source-level check via ast:  parse the module and assert that
the `_connect_daily_click_handler` method body is wired correctly.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "vnpy" / "strategy_condition" / "ui" / "condition_monitor_widget.py"


def _read_source() -> str:
    return MODULE.read_text(encoding="utf-8")


def _parse(src: str) -> ast.Module:
    return ast.parse(src)


def _find_method(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _method_source(fn: ast.FunctionDef, src: str) -> str:
    # ast.get_source_segment returns None on some edge cases, so be
    # defensive.
    seg = ast.get_source_segment(src, fn)
    if seg is not None:
        return seg
    lines = src.splitlines(keepends=True)
    return "".join(lines[fn.lineno - 1 : fn.end_lineno])


def main() -> int:
    assert MODULE.is_file(), f"Cannot find module: {MODULE}"
    src = _read_source()
    tree = _parse(src)

    fn = _find_method(tree, "_connect_daily_click_handler")
    assert fn is not None, (
        "Bug not fixed: _connect_daily_click_handler method missing"
    )
    body_src = _method_source(fn, src)
    print("--- _connect_daily_click_handler source ---")
    print(body_src)
    print("--- end source ---")

    # 1. Must NOT contain the obsolete self._kline_tab reference.
    assert "self._kline_tab" not in body_src, (
        "Bug not fixed: _connect_daily_click_handler still references "
        "self._kline_tab (which doesn't exist on the widget)"
    )

    # 2. Must walk through the real path: self._daily_panel._kline_tab._chart
    assert "_daily_panel" in body_src, (
        "Bug not fixed: did not walk through self._daily_panel"
    )
    assert "_kline_tab._chart" in body_src, (
        "Bug not fixed: did not reach chart via "
        "self._daily_panel._kline_tab._chart"
    )

    # 3. Must NOT connect to the non-existent _on_bar_clicked slot.
    assert "_on_bar_clicked" not in body_src, (
        "Bug not fixed: still wires bar_clicked to "
        "self._on_bar_clicked (which doesn't exist)"
    )

    # 4. Must connect bar_clicked to _on_daily_bar_clicked.
    assert "bar_clicked" in body_src, (
        "Bug not fixed: bar_clicked signal not referenced"
    )
    assert "_on_daily_bar_clicked" in body_src, (
        "Bug not fixed: _on_daily_bar_clicked slot not used"
    )

    # 5. _on_daily_bar_clicked method must exist on the class.
    slot = _find_method(tree, "_on_daily_bar_clicked")
    assert slot is not None, (
        "Bug not fixed: _on_daily_bar_clicked slot method missing"
    )

    # 6. The widget must expose a _bar_clicked_connected success flag.
    #    (We accept either a self._bar_clicked_connected assignment in
    #    the method, or a class-level default.)
    flag_assigned = "_bar_clicked_connected" in body_src
    flag_default = re_default_bar_clicked_connected(tree)
    assert flag_assigned or flag_default, (
        "Bug not fixed: no _bar_clicked_connected success flag "
        "(constructor never set it)"
    )

    print("PASS: daily-bar-click linkage is wired correctly.")
    return 0


def re_default_bar_clicked_connected(tree: ast.Module) -> bool:
    """Return True if any class body sets self._bar_clicked_connected
    somewhere outside the connect method itself (i.e. as a default
    in __init__)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name in (
                    "__init__",
                ):
                    for line in ast.walk(sub):
                        if (
                            isinstance(line, ast.Attribute)
                            and line.attr == "_bar_clicked_connected"
                        ):
                            return True
    return False


if __name__ == "__main__":
    sys.exit(main())