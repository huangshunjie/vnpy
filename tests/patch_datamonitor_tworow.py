"""patch_datamonitor_tworow.py — 表头两行显示：第一行中文，第二行英文"""
import pathlib, ast

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

# ── 1. 插入 TwoLineHeader 类（放在 DataMonitor 类定义之前）─────────
TWO_LINE_CLS = '''
class TwoLineHeader(QtWidgets.QHeaderView):
    """表头两行显示：第一行中文，第二行英文小字"""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )

    def sectionSizeHint(self, logical_index: int) -> int:
        return self.defaultSectionSize()

    def paintSection(self, painter, rect, logical_index: int) -> None:
        painter.save()
        super().paintSection(painter, rect, logical_index)
        label: str = self.model().headerData(
            logical_index,
            self.orientation(),
            QtCore.Qt.ItemDataRole.DisplayRole
        ) or ""

        if "\\n" in label:
            zh, en = label.split("\\n", 1)
        else:
            parts = label.split(" ", 1)
            zh = parts[0]
            en = parts[1] if len(parts) > 1 else ""

        mid_y = rect.top() + rect.height() // 2

        zh_rect = QtCore.QRect(rect.left(), rect.top(), rect.width(), mid_y - rect.top())
        en_rect = QtCore.QRect(rect.left(), mid_y, rect.width(), rect.bottom() - mid_y)

        zh_font = painter.font()
        zh_font.setPointSize(10)
        painter.setFont(zh_font)
        painter.drawText(
            zh_rect,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignBottom,
            zh
        )

        en_font = painter.font()
        en_font.setPointSize(8)
        painter.setFont(en_font)
        painter.setPen(painter.pen().color().lighter(160))
        painter.drawText(
            en_rect,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
            en
        )
        painter.restore()

'''

ANCHOR = "class DataMonitor(QtWidgets.QTableWidget):"
assert ANCHOR in src, "DataMonitor class not found"

if "class TwoLineHeader" not in src:
    src = src.replace(ANCHOR, TWO_LINE_CLS + ANCHOR, 1)
    print("TwoLineHeader class inserted")
else:
    print("TwoLineHeader already present")

# ── 2. 在 DataMonitor.init_ui 里换成 TwoLineHeader，并加大行高 ────
OLD_INIT = (
    "        self.setRowCount(1)\n"
    "        self.verticalHeader().setSectionResizeMode(\n"
    "            QtWidgets.QHeaderView.ResizeMode.Stretch\n"
    "        )\n"
    "        self.verticalHeader().setVisible(False)\n"
    "        self.setEditTriggers(self.EditTrigger.NoEditTriggers)\n"
)
NEW_INIT = (
    "        self.setRowCount(1)\n"
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
    "        self.verticalHeader().setSectionResizeMode(\n"
    "            QtWidgets.QHeaderView.ResizeMode.Stretch\n"
    "        )\n"
    "        self.verticalHeader().setVisible(False)\n"
    "        self.setEditTriggers(self.EditTrigger.NoEditTriggers)\n"
    "        self.setHorizontalScrollBarPolicy(\n"
    "            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded\n"
    "        )\n"
)

assert OLD_INIT in src, "DataMonitor init_ui pattern not found"
src = src.replace(OLD_INIT, NEW_INIT, 1)
print("DataMonitor init_ui patched")

# ── 3. 撤销上次加的 ResizeToContents（避免重复）─────────────────────
LEFTOVER = (
    "        self.horizontalHeader().setSectionResizeMode(\n"
    "            QtWidgets.QHeaderView.ResizeMode.ResizeToContents\n"
    "        )\n"
    "        self.horizontalHeader().setStretchLastSection(False)\n"
    "        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)\n"
)
if LEFTOVER in src:
    src = src.replace(LEFTOVER, "", 1)
    print("Removed leftover resize block")

# ── 4. 语法验证并写入 ─────────────────────────────────────────────
ast.parse(src)
P.write_text(src, encoding="utf-8")
print(f"Done. Total lines: {len(src.splitlines())}")
