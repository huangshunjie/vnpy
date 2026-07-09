"""remove_twolineheader_ref.py"""
import pathlib, ast, re

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

# 用正则替换 DataMonitor.init_ui 里 TwoLineHeader 相关的整块
src = re.sub(
    r'        self\.setRowCount\(1\)\s+two_line_header\s*=\s*TwoLineHeader\(.*?self\.setHorizontalScrollBarPolicy\(\s*QtCore\.Qt\.ScrollBarPolicy\.ScrollBarAsNeeded\s*\)\s*',
    '''        self.setRowCount(1)
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
''',
    src,
    count=1,
    flags=re.DOTALL
)

ast.parse(src)
P.write_text(src, encoding="utf-8")
print("Done. Lines:", len(src.splitlines()))
