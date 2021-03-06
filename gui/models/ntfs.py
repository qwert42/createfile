# encoding: utf-8

# encoding: utf-8
from datetime import datetime
from PySide.QtCore import *
from ._base import BaseFileModel
from drive.fs.ntfs.indxparse.misc import parse_error_datetime_stub
from .misc import long_int, long_str, extra_long_str

from ..misc import SortableStandardItemModel, DataRole

class NTFSFileModel(BaseFileModel):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self._data = []
        self.headers = ['编号', '异常',
                        'MFT记录编号',
                        '活动',
                        '路径',
                        'LSN',
                        'SN',
                        '首LCN',
                        '$SI 创建时间',
                        '$SI 修改时间',
                        '$SI 访问时间',
                        '$SI MFT修改时间',
                        '$FN 创建时间',
                        '$FN 修改时间',
                        '$FN 访问时间',
                        '$FN MFT修改时间',
                        '可用结论',
                        '异常报警来源']
        self.header_types = [int, bool, int, bool,
                             long_str, long_int, int, long_int,
                             datetime, datetime, datetime, datetime,
                             datetime, datetime, datetime, datetime,
                             str, str]

        self.datetime_columns = {8, 9, 10, 11, 12, 13, 14, 15}

        self.checkbox_columns = {1, 3}

    def flags(self, idx):
        row, col = idx.row(), idx.column()
        if (not idx.isValid()
            or not (0 <= row < self.rowCount())
            or not (0 <= col < self.columnCount())):
            return Qt.ItemIsEnabled

        if col in {}:
            return Qt.ItemFlags(super().flags(idx) & ~Qt.ItemIsEnabled)
        else:
            return Qt.ItemFlags(super().flags(idx))

    def data(self, idx, role=Qt.DisplayRole):
        row, col = idx.row(), idx.column()
        if (not idx.isValid()
            or not (0 <= row < self.rowCount())
            or not (0 <= col < self.columnCount())):
            return None

        if role == Qt.DisplayRole:
            if col in self.checkbox_columns:
                return None
            elif col in self.datetime_columns:
                dt = self._data[row][col]
                if dt is parse_error_datetime_stub:
                    return '时间解析错误'
                else:
                    return str(dt)
            else:
                return str(self._data[row][col])
        elif role == Qt.CheckStateRole:
            if col in self.checkbox_columns:
                return Qt.Checked if self._data[row][col] else Qt.Unchecked
            else:
                return None
        elif role == SortableStandardItemModel.SortRole:
            return self.sort_types[col](self._data[row][col])
        elif role == DataRole:
            return self._data[row][col]
