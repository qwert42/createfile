# encoding: utf-8
from .. import Rule
from . import register
from datetime import timedelta
from drive.fs.ntfs import NTFS


@register
class SNEq1Rule(Rule):

    name = 'SN = 1的MFT项$SI创建时间逻辑规则'
    type = NTFS.type
    conclusion = '$SI创建时间异常'
    abnormal = True

    def __init__(self):
        super().__init__(None)

    @staticmethod
    def _approx_ct_gt(_1, _2):
        return _1.si_create_time - _2.si_create_time > timedelta(seconds=2)

    def do_apply(self, entries):
        entries = entries[entries.sn == 1].sort(columns=['id'])
        self._pending_return_values(entries)

        for i, (_, o) in enumerate(entries.iterrows()):
            if i == entries.shape[0] - 1:
                continue

            this, next_ = o, entries.iloc[i + 1]
            if this.si_create_time > next_.si_create_time:
                self.mark_as_positive(i)
                self.mark_as_positive(i + 1)
