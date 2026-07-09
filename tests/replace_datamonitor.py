"""replace_datamonitor.py — 整块替换 DataMonitor 类"""
import pathlib, ast

P = pathlib.Path(r"D:\veighna_studio\Lib\site-packages\vnpy_ctastrategy\ui\widget.py")
src = P.read_text(encoding="utf-8")

OLD = '''class DataMonitor(QtWidgets.QTableWidget):
    """
    Table monitor for parameters and variables.
    """

    def __init__(self, data: dict) -> None:
        """"""
        super().__init__()

        self._data: dict = data
        self.cells: dict = {}

        self.init_ui()

    def init_ui(self) -> None:
        """"""
        labels: list = [FIELD_NAME_MAP.get(k, (k, k))[0] for k in self._data.keys()]
        self.setColumnCount(len(labels))
        self.setHorizontalHeaderLabels(labels)

        self.setRowCount(1)
        two_line_header = TwoLineHeader(
            QtCore.Qt.Orientation.Horizontal, self
        )
        two_line_header.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        two_line_header.setStretchLastSection(False)
        two_line_header.setMinimumSectionSize(80)
        self.setHorizontalHeader(two_line_header)
        self.horizontalHeader().setMinimumHeight(44)
        self.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        for column, name in enumerate(self._data.keys()):
            value = self._data[name]

            cell: QtWidgets.QTableWidgetItem = QtWidgets.QTableWidgetItem(str(value))
            cell.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.setItem(0, column, cell)
            self.cells[name] = cell

            zh, en = FIELD_NAME_MAP.get(name, (name, name))
            tip = QtWidgets.QTableWidgetItem()
            tip.setToolTip(f"{zh}\\n{en}")
            self.setHorizontalHeaderItem(column, tip)
            self.horizontalHeaderItem(column).setText(zh)


    def update_data(self, data: dict) -> None:
        """"""
        for name, value in data.items():
            cell: QtWidgets.QTableWidgetItem = self.cells[name]
            cell.setText(str(value))'''

NEW = '''class DataMonitor(QtWidgets.QTableWidget):
    """
    Table monitor for parameters and variables.
    """

    def __init__(self, data: dict) -> None:
        """"""
        super().__init__()

        self._data: dict = data
        self.cells: dict = {}

        self.init_ui()

    def init_ui(self) -> None:
        """"""
        keys = list(self._data.keys())
        self.setColumnCount(len(keys))

        self.setRowCount(1)
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

        for column, name in enumerate(keys):
            zh, en = FIELD_NAME_MAP.get(name, (name, name))

            header_item = QtWidgets.QTableWidgetItem(zh)
            header_item.setToolTip(f"{zh}\\n{en}")
            self.setHorizontalHeaderItem(column, header_item)

            value = self._data[name]
            cell = QtWidgets.QTableWidgetItem(str(value))
            cell.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.setItem(0, column, cell)
            self.cells[name] = cell

    def update_data(self, data: dict) -> None:
        """"""
        for name, value in data.items():
            cell: QtWidgets.QTableWidgetItem = self.cells[name]
            cell.setText(str(value))'''

assert OLD in src, "DataMonitor old block not found"
src = src.replace(OLD, NEW, 1)
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("Done. Lines:", len(src.splitlines()))
