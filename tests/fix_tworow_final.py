"""fix_tworow_final.py — 彻底换方案：删除 TwoLineHeader，改用 WordWrap"""
import pathlib, ast, re

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

# ── 1. 删除整个 TwoLineHeader 类 ────────────────────────────────
old_cls = re.search(
    r"\nclass TwoLineHeader\(QtWidgets\.QHeaderView\):.*?(?=\nclass DataMonitor)",
    src, re.DOTALL
)
assert old_cls, "TwoLineHeader not found"
src = src[:old_cls.start()] + "\n" + src[old_cls.end():]
print("TwoLineHeader removed")

# ── 2. 把 FIELD_NAME_MAP 的值改成 "中文\n英文" 格式 ──────────────
# 当前格式是 "中文 英文"，改成 "中文\n英文"
def reformat_map(m):
    """把 "中文 英文" 格式改成 "中文\n英文" """
    value = m.group(1)
    # 找第一个空格分隔中英文
    parts = value.split(" ", 1)
    if len(parts) == 2:
        return f'"{parts[0]}\\n{parts[1]}"'
    return m.group(0)

# 替换 FIELD_NAME_MAP 里所有值
src = re.sub(
    r'"([^\\"]+\s[a-zA-Z_0-9%]+)"',
    reformat_map,
    src,
    flags=re.MULTILINE
)
print("FIELD_NAME_MAP values reformatted")

# ── 3. 修复 DataMonitor.init_ui：
#    - 恢复原始 horizontalHeader（去掉 TwoLineHeader）
#    - 加 WordWrap + 足够高度 ─────────────────────────────────────
OLD_HEADER_BLOCK = (
    "        two_line_header = TwoLineHeader(\n"
    "            QtCore.Qt.Orientation.Horizontal, self\n"
    "        )\n"
    "        two_line_header.setSectionResizeMode(\n"
    "            QtWidgets.QHeaderView.ResizeMode.ResizeToContents\n"
    "        )\n"
    "        two_line_header.setStretchLastSection(False)\n"
    "        two_line_header.setMinimumSectionSize(80)\n"
    "        self.setHorizontalHeader(two_line_header)\n"
    "        self.horizontalHeader().setMinimumHeight(44)\n"
)

NEW_HEADER_BLOCK = (
    "        self.horizontalHeader().setSectionResizeMode(\n"
    "            QtWidgets.QHeaderView.ResizeMode.ResizeToContents\n"
    "        )\n"
    "        self.horizontalHeader().setStretchLastSection(False)\n"
    "        self.horizontalHeader().setMinimumSectionSize(80)\n"
    "        self.horizontalHeader().setMinimumHeight(48)\n"
    "        self.horizontalHeader().setDefaultAlignment(\n"
    "            QtCore.Qt.AlignmentFlag.AlignCenter\n"
    "        )\n"
)

assert OLD_HEADER_BLOCK in src, "header block not found"
src = src.replace(OLD_HEADER_BLOCK, NEW_HEADER_BLOCK, 1)
print("DataMonitor header block updated")

# ── 4. 设置 QTableWidget 允许 WordWrap（换行显示表头） ────────────
# 在 setHorizontalScrollBarPolicy 后加 setWordWrap
OLD_SCROLL = (
    "        self.setHorizontalScrollBarPolicy(\n"
    "            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded\n"
    "        )\n"
)
NEW_SCROLL = (
    "        self.setHorizontalScrollBarPolicy(\n"
    "            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded\n"
    "        )\n"
    "        self.setWordWrap(True)\n"
)
if OLD_SCROLL in src and NEW_SCROLL not in src:
    src = src.replace(OLD_SCROLL, NEW_SCROLL, 1)
    print("setWordWrap added")

# ── 5. 语法验证并写入 ─────────────────────────────────────────────
ast.parse(src)
P.write_text(src, encoding="utf-8")
print(f"Done. Total lines: {len(src.splitlines())}")
