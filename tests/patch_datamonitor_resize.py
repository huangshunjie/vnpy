"""patch_datamonitor_resize.py — 让 DataMonitor 列宽自适应内容"""
import pathlib, ast

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

OLD = (
    "        for column, name in enumerate(self._data.keys()):\n"
    "            value = self._data[name]\n"
    "\n"
    "            cell: QtWidgets.QTableWidgetItem = QtWidgets.QTableWidgetItem(str(value))\n"
    "            cell.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)\n"
    "\n"
    "            self.setItem(0, column, cell)\n"
    "            self.cells[name] = cell\n"
)

NEW = (
    "        for column, name in enumerate(self._data.keys()):\n"
    "            value = self._data[name]\n"
    "\n"
    "            cell: QtWidgets.QTableWidgetItem = QtWidgets.QTableWidgetItem(str(value))\n"
    "            cell.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)\n"
    "\n"
    "            self.setItem(0, column, cell)\n"
    "            self.cells[name] = cell\n"
    "\n"
    "        self.horizontalHeader().setSectionResizeMode(\n"
    "            QtWidgets.QHeaderView.ResizeMode.ResizeToContents\n"
    "        )\n"
    "        self.horizontalHeader().setStretchLastSection(False)\n"
    "        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)\n"
)

assert OLD in src, "pattern not found"
src = src.replace(OLD, NEW, 1)
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("Done. Lines:", len(src.splitlines()))
