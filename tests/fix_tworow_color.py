"""fix_tworow_color.py — 修复 TwoLineHeader 文字颜色"""
import pathlib, ast, re

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

# 替换整个 TwoLineHeader 类为简化可靠版本
OLD = re.search(
    r"class TwoLineHeader\(QtWidgets\.QHeaderView\):.*?(?=\nclass DataMonitor)",
    src, re.DOTALL
)
if not OLD:
    raise AssertionError("TwoLineHeader class not found")

NEW_CLS = '''class TwoLineHeader(QtWidgets.QHeaderView):
    """表头两行显示：第一行中文，第二行英文小字"""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def paintSection(self, painter, rect, logical_index: int) -> None:
        painter.save()

        # 绘制背景和边框（text留空，由自己绘制）
        opt = QtWidgets.QStyleOptionHeader()
        self.initStyleOption(opt)
        opt.rect = rect
        opt.section = logical_index
        opt.text = ""
        self.style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_Header, opt, painter, self
        )

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

        zh_font = QtGui.QFont(painter.font())
        zh_font.setPointSize(10)
        painter.setFont(zh_font)
        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.drawText(
            zh_rect,
            int(QtCore.Qt.AlignmentFlag.AlignHCenter) | int(QtCore.Qt.AlignmentFlag.AlignBottom),
            zh
        )

        en_font = QtGui.QFont(painter.font())
        en_font.setPointSize(8)
        painter.setFont(en_font)
        painter.setPen(QtGui.QColor(180, 180, 180))
        painter.drawText(
            en_rect,
            int(QtCore.Qt.AlignmentFlag.AlignHCenter) | int(QtCore.Qt.AlignmentFlag.AlignTop),
            en
        )

        painter.restore()

'''

src = src[:OLD.start()] + NEW_CLS + src[OLD.end():]
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("Done. Lines:", len(src.splitlines()))
