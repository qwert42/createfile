# encoding: utf-8
from PySide.QtCore import *
from PySide.QtGui import *

from judge import *
import judge.built_in.fat32 as jf
import judge.built_in.ntfs as jn
from .column_list_view import ColumnListView
import judge
from drive.fs.fat32 import FAT32
from drive.fs.ntfs import NTFS


class RulesWidget(QWidget):

    _fat32_rules = [jf.rule1]
    _ntfs_rules = [jn.rule1, jn.rule2, jn.rule3, jn.rule4, jn.rule5, jn.rule6,
                   jn.rule7, jn.rule8, jn.rule9, jn.rule10]

    def __init__(self, parent):
        super(RulesWidget, self).__init__(parent=parent)

        self._clv = ColumnListView(['已启用', '规则', '结论', '标记为异常'],
                                   parent, order_column=True)
        self._ext_rules = {}

        self._setup_layout()

        self.type = ''

    def _inflate_rules(self, which_rules, clear):
        if clear:
            self._clv.clear()

        def cb_abnormal(a):
            _ = QStandardItem('')
            _.setEditable(False)
            _.setCheckable(True)
            _.setCheckState(Qt.Checked if a else Qt.Unchecked)

            return _

        for r, c, a in which_rules:
            self._clv.append(['', r, c, cb_abnormal(a)], checkable=True)

        for cls in judge.ext.registry.values():
            obj = cls()
            if obj.type != self.type:
                continue

            self._clv.append(['',
                              obj.name,
                              obj.conclusion,
                              cb_abnormal(obj.abnormal)],
                             checkable=True)
            self._ext_rules[obj.name] = obj

    def inflate_with_fat32_rules(self, clear=True):
        self.type = FAT32.type

        self._inflate_rules(self._fat32_rules, clear)

    def inflate_with_ntfs_rules(self, clear=True):
        self.type = NTFS.type

        self._inflate_rules(self._ntfs_rules, clear)

    def _setup_layout(self):
        btn_add = QPushButton('添加')
        btn_remove = QPushButton('移除')

        le_rule = QLineEdit()
        _label = QLabel('=>')
        le_conclusion = QLineEdit()

        def add():
            _ = QStandardItem()
            _.setEditable(True)
            _.setCheckable(True)

            self._clv.append(['', le_rule.text(), le_conclusion.text(), _],
                             checkable=True)
            le_rule.setText('')
            le_conclusion.setText('')
        btn_add.clicked.connect(add)

        def remove():
            self._clv.remove(self._clv.currentIndex().row())
        btn_remove.clicked.connect(remove)

        _l = QHBoxLayout()
        _l.addWidget(_label)
        _l.addWidget(le_conclusion)

        input_layout = QGridLayout()
        input_layout.addWidget(le_rule,    0, 0, 1, 1)
        input_layout.addLayout(_l,         1, 0, 1, 1)
        input_layout.addWidget(btn_add,    0, 1, 1, 1)
        input_layout.addWidget(btn_remove, 1, 1, 1, 1)

        layout = QVBoxLayout()
        layout.addLayout(input_layout)
        layout.addWidget(self._clv)

        self.setLayout(layout)

    def rules(self):
        for r in range(self._clv.model_.rowCount()):
            id_, on, rule, conclusion, abnormal = (self._clv.model_.item(r, 0),
                                                   self._clv.model_.item(r, 1),
                                                   self._clv.model_.item(r, 2),
                                                   self._clv.model_.item(r, 3),
                                                   self._clv.model_.item(r, 4))

            if on.checkState() == Qt.Checked:
                name = rule.text()
                if name in self._ext_rules:
                    obj = self._ext_rules[name]
                else:
                    obj = (If(eval(rule.text()))
                            .then(conclusion=conclusion.text(),
                                  abnormal=abnormal.checkState() == Qt.Checked))
                yield int(id_.text()), obj
