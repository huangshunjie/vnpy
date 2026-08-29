"""Dump _on_outer_daily_bar_clicked and _on_mouse_clicked_for_link to file."""
import re
from pathlib import Path

t = Path(r"vnpy\strategy_condition\ui\kline_view.py").read_text(encoding="utf-8")
out = []
for name in ("_on_outer_daily_bar_clicked", "_on_mouse_clicked_for_link", "_on_x_range_changed"):
    out.append(f"========= {name} =========")
    m = re.search(rf'    def {name}\([^)]*\)[\s\S]*?(?=\n    def |\nclass )', t)
    if m:
        out.append(m.group())
    else:
        out.append("NOT FOUND")
Path(r"_dump_methods.txt").write_text("\n\n".join(out), encoding="utf-8")
print(f"wrote {len('\n\n'.join(out))} chars")