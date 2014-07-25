# encoding: utf-8
from functools import lru_cache
import logging
import os
import webbrowser
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import QWebView
from jinja2 import Environment, PackageLoader
from stats import windowed
from ..widgets import FilesWidget, SummaryWidget, FigureWidget, RulesWidget, \
    FAT32SettingsWidget, NTFSSettingsWidget
from ..misc import AsyncTaskMixin, denamedtuplize, namedtuplize, info_box
import pandas as pd
from drive.fs.fat32 import FAT32

class BaseSubWindow(QMainWindow, AsyncTaskMixin):

    signal_partition_parsed = Signal(object)

    USE_QT_WEBKIT = False

    def __init__(self,
                 parent,
                 partition, partition_address):
        super().__init__(parent=parent)

        self.setup_mixin(parent)

        self.partition = partition
        self.partition_address = partition_address

        self.summary_widget = SummaryWidget(self, self.partition.type)
        self.files_widget = FilesWidget(self)
        self.rules_widget = RulesWidget(self)

        self.figures_widget = QTabWidget(self)
        self.figures_widget.setTabsClosable(True)

        def close_tab(id_):
            self.figures_widget.removeTab(id_)
        self.figures_widget.tabCloseRequested.connect(close_tab)

        if self.partition.type == FAT32.type:
            self.settings = self.settings_widget = FAT32SettingsWidget(self)
        else:
            self.settings = self.settings_widget = NTFSSettingsWidget(self)

        self.setup_layout()

        self.setWindowIcon(QFileIconProvider().icon(QFileIconProvider.Drive))
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.template_path = os.path.join(os.getcwd(),
                                          'gui',
                                          'sub_windows', 'templates')
        self.timeline_base_url = QUrl.fromLocalFile(self.template_path)

        jinja_env = Environment(loader=PackageLoader('gui.sub_windows'))
        self.timeline_template = jinja_env.get_template('timeline.html')

        self.original_title = '正在分析%s' % partition_address
        self.setWindowTitle(self.original_title)

        self.logger = logging.getLogger(__name__)

        self.raw_entries = None
        self.entries = None

        self.abnormal_files = set()

        self.reload()

    def reload(self):
        self.raw_entries = None
        self.entries = None

        self.abnormal_files = set()

        def _slot(entries):
            self.raw_entries = entries

            self.entries = self.settings.filter(self.raw_entries)
            self.entries = self.settings.sort(self.entries)

            self.summary_widget.summarize(self.entries)

            self.entries = self.deduce_abnormal_files(self.entries)

            self.entries = self.deduce_authentic_time(self.entries)

            self.entries = self.settings.sort(self.entries)

            self.show_files(self.entries)

            self.signal_partition_parsed.disconnect(_slot)

        def _target():
            return self.apply_rules(self.partition.get_entries())

        self.signal_partition_parsed.connect(_slot)
        self.do_async_task(_target,
                           signal_after=self.signal_partition_parsed,
                           title_before='正在读取分区...')

    def deduce_abnormal_files(self, entries):
        raise NotImplementedError

    def setup_related_buttons(self):
        raise NotImplementedError

    def setup_layout(self):
        buttons_layout = self.setup_related_buttons()

        def new_group_box(widget, title):
            _ = QVBoxLayout()
            _.addWidget(widget)

            group_box = QGroupBox(title)
            group_box.setLayout(_)

            return group_box

        summary_group_box = new_group_box(self.summary_widget, '分区概要')
        files_group_box = new_group_box(self.files_widget, '分区文件列表')
        settings_group_box = new_group_box(self.settings_widget, '设置')
        rules_group_box = new_group_box(self.rules_widget, '规则列表')

        layout = QGridLayout(self)
        _1 = QVBoxLayout(self)
        _1.addLayout(buttons_layout)
        _1.addWidget(summary_group_box)
        _1.addWidget(settings_group_box)

        _2 = QVBoxLayout(self)
        _2.addWidget(files_group_box)
        _2.addWidget(rules_group_box)

        _3 = QVBoxLayout(self)
        _3.addWidget(self.figures_widget)

        layout.addLayout(_1, 0, 0, 1, 1)
        layout.addLayout(_2, 0, 1, 1, 1)
        layout.addLayout(_3, 0, 2, 1, 3)

        _ = QWidget(self)
        _.setLayout(layout)
        self.setCentralWidget(_)

    def show_files(self, entries):
        self.files_widget.clear()

        for _, row in entries.iterrows():
            self.files_widget.append(self.gen_file_row_data(row))

    def gen_file_row_data(self, row):
        raise NotImplementedError

    def apply_rules(self, entries):
        return self._apply_rules(namedtuplize(entries),
                                 tuple(self.rules_widget.rules()))

    @staticmethod
    @lru_cache(maxsize=64)
    def _apply_rules(nt, rules):
        entries = denamedtuplize(nt)

        objects = []
        for _, o in entries.iterrows():
            objects.append(o)

        for r_id, rule in enumerate(rules):
            _result, positives = rule.apply_to(entries)

            for i, (r, o) in enumerate(zip(_result, objects)):
                if 'conclusions' not in o:
                    o['conclusions'] = r.conclusions
                else:
                    o['conclusions'].extend(r.conclusions)

                if rule.abnormal:
                    o['abnormal'] = i in positives

                    if o['abnormal']:
                        src = '%s号规则' % r_id
                        if 'abnormal_src' in o:
                            o['abnormal_src'].append(src)
                        else:
                            o['abnormal_src'] = [src]

        for o in objects:
            if 'conclusions' in o:
                o['conclusions'] = tuple(o['conclusions'])
            if 'abnormal_src' in o:
                o['abnormal_src'] = tuple(o['abnormal_src'])

        return pd.DataFrame(objects)

    @staticmethod
    def deduce_authentic_time(entries):
        entries = entries.sort_index(by='first_cluster')
        entries_list = list(map(lambda _: _[1], entries.iterrows()))

        visited_files = set()

        first_entry, last_entry = entries.iloc[0], entries.iloc[-1]

        for o in entries_list:
            if o.abnormal == True:
                if o.first_cluster < first_entry.first_cluster:
                    if o.id not in visited_files:
                        o['deduced_time'] = '%s之前' % first_entry.create_time

                        visited_files.add(o.id)

        for entry2, entry1 in windowed(list(reversed(entries_list)), size=2):
            for o in entries_list:
                if o.abnormal == True:
                    if (entry1.first_cluster
                     <= o.first_cluster
                     < entry2.first_cluster):
                        if o.id not in visited_files:
                            o['deduced_time'] = '%s与%s之间' % (
                                entry1.create_time,
                                entry2.create_time
                            )

                            visited_files.add(o.id)

        for o in entries_list:
            if o.abnormal == True:
                if last_entry.first_cluster <= o.first_cluster:
                    if o.id not in visited_files:
                        o['deduced_time'] = '%s之后' % last_entry.create_time

                        visited_files.add(o.id)

        return pd.DataFrame(entries_list)

    def add_figure(self, figure, label='绘图结果'):
        self.figures_widget.addTab(FigureWidget(self, figure),
                                   label)

    def _show_timeline(self, start_time_attr, display_abnormal_source=True):
        conclusions = set()
        for _, row in self.entries.iterrows():
            for c in row.conclusions:
                conclusions.add(c)

        conclusions = list(conclusions)
        conclusions.append('无可用结论')

        groups, c_id = [], {}
        for i, c in enumerate(conclusions):
            groups.append({'id': i, 'content': c})
            c_id[c] = i

        def _gen_item(item, group_id=len(conclusions) - 1):
            content = '#%s' % item.id
            if display_abnormal_source:
                if not isinstance(item.abnormal_src, float):
                    content += '<br />%s' % ', '.join(item.abnormal_src)

            _ = {'start': item[start_time_attr].timestamp() * 1000,
                 'content': content,
                 'group': group_id}

            if item.abnormal == True:
                _['className'] = 'red'

            return _

        items = []
        for i, (_t, item) in enumerate(self.entries.iterrows()):
            if item.conclusions:
                _ = {}
                for c in item.conclusions:
                    _ = _gen_item(item, c_id[c])
            else:
                _ = _gen_item(item)

            items.append(_)

        html = self.timeline_template.render(
            groups=groups,
            items=items,
            start=self.summary_widget.start_time.timestamp() * 1000,
            end=self.summary_widget.end_time.timestamp() * 1000
        )

        if self.USE_QT_WEBKIT:
            view = QWebView(self)
            view.setHtml(html, self.timeline_base_url)
            self.figures_widget.addTab(view, '时间线')
        else:
            info_box(self, '将会打开外部浏览器查看时间线')

            path = os.path.join(self.template_path, 'r.html')
            print(html, file=open(path, 'w', encoding='utf-8'))
            webbrowser.open(QUrl.fromLocalFile(path).toString())
