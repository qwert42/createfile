# encoding: utf-8
from PySide.QtGui import *
from ..widgets import ColumnListView
from drive.fs.fat32 import FAT32
from drive.fs.ntfs import NTFS


class FilesWidget(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self._clv = ColumnListView(['路径'],
                                   self,
                                   headers_fit_content=True,
                                   order_column=True)
        self.setup_headers_by(self.parent().partition.type)

        _l = QVBoxLayout()
        _l.addWidget(self._clv)
        self.setLayout(_l)

    def append(self, *args, **kwargs):
        self._clv.append(*args, **kwargs)

    def setup_headers_by(self, type_):
        if type_ == FAT32.type:
            self._clv.setup_headers(['异常',
                                     'FDT编号',
                                     '路径',
                                     '首簇',
                                     '创建时间',
                                     '修改时间',
                                     '访问日期',
                                     '可用结论',
                                     '异常报警来源',
                                     '正确创建时间推测'],
                                    [0, 1, 3])
        elif type_ == NTFS.type:
            self._clv.setup_headers(['异常',
                                     '路径',
                                     'LSN',
                                     'SN',
                                     '首VCN',
                                     '$SI 创建时间',
                                     '$SI 修改时间',
                                     '$SI 访问时间',
                                     '$SI MFT修改时间',
                                     '$FN 创建时间',
                                     '$FN 修改时间',
                                     '$FN 访问时间',
                                     '$FN MFT修改时间',
                                     '可用结论',
                                     '异常报警来源',
                                     '正确创建时间推测'])

    def clear(self):
        self._clv.clear()