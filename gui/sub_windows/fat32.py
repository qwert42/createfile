# encoding: utf-8
from PySide.QtCore import *
from PySide.QtGui import *
from stats.speedup.alg import u_tau, u_rho
import matplotlib.pyplot as plt
import time

from ._base import BaseSubWindow
from drive.fs.fat32 import first_clusters_of_fat32, \
    last_clusters_of_fat32
from drive.fs.fat32.plot import plot_fat32
from stats import plot_windowed_metrics, calc_windowed_metrics
from stats.validate import validate_clusters, validate_metrics
from ..misc import filter_empty_cluster_list, new_tool_button, DataRole


class FAT32SubWindow(BaseSubWindow):

    signal_plot_prepared = Signal(object)

    def __init__(self, parent, partition, partition_address):
        super().__init__(parent, partition, partition_address)

        self.rules_widget.inflate_with_fat32_rules()

        self.signal_plot_prepared.connect(lambda ret: self.add_figure(*ret))
        self.signal_time_deduced.connect(lambda e: self.show_files(e))

    def plot_partition(self):
        figure = plot_fat32(filter_empty_cluster_list(self.entries),
                            log_info=False,
                            logger=self.logger,
                            plot_first_cluster=self.settings.plot_first_cluster,
                            plot_average_cluster=self.settings.plot_avg_cluster,
                            show=False)

        self.add_figure(figure, label='时簇图')

    @staticmethod
    def _validate_points_by_first_clusters(entries,
                                           value_domain,
                                           rect_size,
                                           threshold):

        return validate_clusters([entries.id.tolist()],
                                 [list(zip(first_clusters_of_fat32(entries),
                                           last_clusters_of_fat32(entries)))],
                                 [value_domain],
                                 [rect_size],
                                 [threshold])

    def validate_first_clusters_with_settings(self):
        return self._validate_points_by_first_clusters(
            filter_empty_cluster_list(self.entries),
            (self.settings.cluster_plot_value_domain_min,
             self.settings.cluster_plot_value_domain_max),
            (self.settings.cluster_plot_rect_size_width,
             self.settings.cluster_plot_rect_size_height),
            self.settings.cluster_plot_threshold
        )

    def deduce_abnormal_files(self, entries):
        if not self.settings.enable_metrics_abnormality_detection:
            return entries

        extract_ids = lambda s: entries.iloc[s[0][0]].id.tolist()

        _, a_fc, _ = self.validate_first_clusters_with_settings()

        a_fc_id_set = extract_ids(a_fc) if a_fc[0][0] else []

        for _, o in entries.iterrows():
            if o.id in a_fc_id_set:
                o.abnormal_src.append('簇号分布异常')
                o.conclusions.append('簇号分布异常')
                entries.loc[_, 'abnormal'] = True

        return entries

    def plot_first_clusters_metrics(self):
        figure = plt.figure()
        def target():
            n, a, l = self.validate_first_clusters_with_settings()

            return plot_windowed_metrics(
                n, a, l,
                ['首簇号'],
                [self.settings.cluster_plot_format],
                [self.settings.cluster_plot_plot_normal_points],
                [self.settings.cluster_plot_plot_abnormal_points],
                figure=figure
            ), '簇号参数图'

        self.do_async_task(target,
                           signal_after=self.signal_plot_prepared,
                           title_before='正在准备簇号参数图...')

    @staticmethod
    def _validate_points_by_metrics(method,
                                    entries,
                                    attr1_expr,
                                    attr2_expr,
                                    value_domain,
                                    rect_size,
                                    threshold):
        func = {'tau': u_tau, 'rho': u_rho}[method]
        ids, values = calc_windowed_metrics(
            [func],
            entries,
            attr1=lambda _: eval(attr1_expr),
            attr2=lambda _: eval(attr2_expr),
            echo=False
        )

        return validate_metrics(ids, values,
                                [value_domain],
                                [rect_size],
                                [threshold])

    def validate_metrics_with_settings(self, method):
        def s(attr=''):
            return getattr(self.settings,
                           '%s_%s' % (method, attr))

        return self._validate_points_by_metrics(
            method,
            filter_empty_cluster_list(self.entries),
            s('attr1'),
            s('attr2'),
            (s('value_domain_min'),
             s('value_domain_max')),
            (s('rect_size_width'),
             s('rect_size_height')),
            s('threshold')
        )

    def plot_statistical_metrics(self, method):
        figure = plt.figure()
        def target():
            def s(attr=''):
                return getattr(self.settings,
                               '%s_%s' % (method, attr))

            n, a, l = self.validate_metrics_with_settings(method)

            return plot_windowed_metrics(
                n, a, l,
                [method],
                [s('format')],
                [s('plot_normal_points')],
                [s('plot_abnormal_points')],
                figure=figure
            ), '%s参数图' % method

        self.do_async_task(target,
                           signal_after=self.signal_plot_prepared,
                           title_before='正在准备%s参数图...' % method)

    def plot_metrics(self):
        if self.settings.tau:
            self.plot_statistical_metrics('tau')
        if self.settings.rho:
            self.plot_statistical_metrics('rho')
        if self.settings.cluster_plot:
            self.plot_first_clusters_metrics()

    def plot_timeline(self):
        self._show_timeline('create_time',
                            True)

    signal_time_deduced = Signal(object)
    def do_authentic_time_deduction(self):
        ids = set()
        for i in range(self.files_widget.model().rowCount()):
            idx = self.files_widget.model().createIndex(i, 1)
            selected = self.files_widget.model().data(idx, role=DataRole)
            if selected:
                idx = self.files_widget.model().createIndex(i, 3)
                ids.add(self.files_widget.model().data(idx, role=DataRole))

        if not ids:
            ids = set(self.entries[self.entries.abnormal == True].id.tolist())

        def target():
            _1 = time.time()
            entries = self.deduce_authentic_time(self.entries,
                                                 ids)
            _2 = time.time()
            print('deducing cost %s' % (_2 - _1))

            return entries

        self.do_async_task(target,
                           signal_after=self.signal_time_deduced,
                           title_before='正在推测正确时间...')

    def setup_related_buttons(self):
        btn_plot_partition = new_tool_button('时 簇 图', ':/plot.png')
        btn_plot_partition.clicked.connect(self.plot_partition)

        btn_plot_metrics = new_tool_button('参 数 图', ':/plot.png')
        btn_plot_metrics.clicked.connect(self.plot_metrics)

        btn_plot_timeline = new_tool_button('时 间 线', ':/timeline.png')
        btn_plot_timeline.clicked.connect(self.plot_timeline)

        btn_deduce_authentic_time = new_tool_button('时间推测',
                                                    ':/timeline.png')
        btn_deduce_authentic_time.clicked.connect(
            self.do_authentic_time_deduction
        )

        group_box = QGroupBox('FAT32分析工具集')

        _ = QHBoxLayout()
        _.addWidget(btn_plot_partition)
        _.addWidget(btn_plot_metrics)
        _.addWidget(btn_plot_timeline)
        _.addWidget(btn_deduce_authentic_time)

        group_box.setLayout(_)

        _ = QVBoxLayout()
        _.addWidget(group_box)

        return _

    def gen_file_row_data(self, row, count):
        last_cluster = 0
        if len(row.cluster_list) > 0:
            if len(row.cluster_list[-1]) > 0:
                last_cluster = row.cluster_list[-1][-1]

        return [count, False, row.abnormal,
                row.id,
                row.is_deleted,
                row.full_path, row.first_cluster, last_cluster,
                row.create_time, row.modify_time, row.access_date,
                row.conclusions,
                row.abnormal_src if 'abnormal_src' in row else [],
                row.deduced_time if 'deduced_time' in row else '']

    def deduce_authentic_time(self, entries, ids):
        return self._deduce_authentic_time(entries, 'create_time', ids)
