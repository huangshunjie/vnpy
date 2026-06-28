"""
patch_datamanager.py

在 vnpy_datamanager 的 ManagerWidget 工具栏里注入
"下载全市场"按钮，不修改已安装的库文件。

在 run.py 里 import 本模块即可激活：
    import vnpy.app.batch_research.patch_datamanager  # noqa
"""

from vnpy_datamanager.ui.widget import ManagerWidget
from vnpy.trader.ui import QtWidgets

from .ui.bulk_download_dialog import BulkDownloadDialog


def _bulk_download(self: ManagerWidget) -> None:
    dlg = BulkDownloadDialog(parent=self)
    dlg.exec_()


def _patched_init_ui(self: ManagerWidget) -> None:
    """替换原 init_ui，在原有按钮行末追加"下载全市场"按钮。"""
    _original_init_ui(self)

    # 找到工具栏所在的第一个 QHBoxLayout
    main_layout: QtWidgets.QVBoxLayout = self.layout()
    hbox: QtWidgets.QHBoxLayout = main_layout.itemAt(0).layout()

    bulk_btn = QtWidgets.QPushButton("下载全市场")
    bulk_btn.setToolTip("从 Tushare 批量下载全 A 股日线数据到本地数据库")
    bulk_btn.clicked.connect(lambda: _bulk_download(self))
    hbox.addWidget(bulk_btn)


# 保存原始方法，patch 后仍可调用
_original_init_ui = ManagerWidget.init_ui

# 注入
ManagerWidget.init_ui = _patched_init_ui
