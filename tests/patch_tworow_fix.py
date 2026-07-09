"""patch_tworow_fix.py — 修复 TwoLineHeader.paintSection，完全自绘"""
import pathlib, ast

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

OLD_CLS = '''class TwoLineHeader(QtWidgets.QHeaderView):
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

NEW_CLS = '''class TwoLineHeader(QtWidgets.QHeaderView):
    """表头两行显示：第一行中文，第二行英文小字"""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def paintSection(self, painter, rect, logical_index: int) -> None:
        painter.save()

        # 绘制背景和边框（不绘制文字）
        opt = QtWidgets.QStyleOptionHeader()
        self.initStyleOption(opt)
        opt.rect = rect
        opt.section = logical_index
        opt.text = ""
        style = self.style()
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_Header, opt, painter, self)

        # 取标题文字
        label: str = self.model().headerData(
            logical_index,
            self.orientation(),
            QtCore.Qt.ItemDataRole.DisplayRole
        ) or ""

        parts = label.split(" ", 1)
        zh = parts[0]
        en = parts[1] if len(parts) > 1 else ""

        half = rect.height() // 2
        zh_rect = QtCore.QRect(rect.left() + 2, rect.top(), rect.width() - 4, half)
        en_rect = QtCore.QRect(rect.left() + 2, rect.top() + half, rect.width() - 4, rect.height() - half)

        # 中文行
        zh_font = QtGui.QFont(painter.font())
        zh_font.setPointSize(10)
        zh_font.setBold(False)
        painter.setFont(zh_font)
        painter.setPen(self.palette().color(QtGui.QPalette.ColorRole.ButtonText))
        painter.drawText(
            zh_rect,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignBottom,
            zh
        )

        # 英文行（浅色小字）
        en_font = QtGui.QFont(painter.font())
        en_font.setPointSize(8)
        painter.setFont(en_font)
        en_color = self.palette().color(QtGui.QPalette.ColorRole.ButtonText)
        en_color.setAlpha(140)
        painter.setPen(en_color)
        painter.drawText(
            en_rect,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
            en
        )

        painter.restore()
'''

assert OLD_CLS in src, "TwoLineHeader old class not found"
src = src.replace(OLD_CLS, NEW_CLS, 1)

ast.parse(src)
P.write_text(src, encoding="utf-8")
print("Done. Lines:", len(src.splitlines()))
