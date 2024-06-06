import datetime
import math
import os
import threading
import time
from queue import Queue

import numpy as np
from PyQt5.QtCore import pyqtSignal, QThread, QMutex, QTimer
from PyQt5.QtWidgets import QMainWindow, QGridLayout
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar

from mainwindow import Ui_MainWindow
from mouse import Mouse, supported_mouses
from mpl_plot import Mplplot


def rot_mat(theta):
    mat = np.array([[math.cos(theta), -math.sin(theta)],
                    [math.sin(theta), math.cos(theta)]])
    return mat


def set_button(enabled=[], disabled=[]):
    for button in enabled:
        button.setEnabled(True)
    for button in disabled:
        button.setEnabled(False)


class DataQueue:
    def __init__(self, max_length):
        self.data: Queue = Queue(max_length)

    def write_item(self, item):
        if self.data.full():
            self.data.get()
        self.data.put(item)

    def get_item(self):
        return self.data.get()

    def get_data(self):
        return list(self.data.queue)

    def clear(self):
        self.data.queue.clear()

    def is_empty(self):
        return self.data.empty()


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        super(QMainWindow, self).__init__()
        # plot
        self.mut = QMutex()
        self.max_timestamps_plot: int = 1000
        self.canvas_size = None
        self.y_upper = None
        self.y_lower = None
        self.x_upper = None
        self.x_lower = None
        self.y_show = DataQueue(self.max_timestamps_plot)
        self.x_show = DataQueue(self.max_timestamps_plot)

        # record
        self.exp_start_time = None
        self.y_data = []
        self.x_data = []
        self.timestamps = []
        self.feeding_timestamps = []
        self.vs_timestamps = []
        self.mouse1: Mouse = ...
        self.mouse2: Mouse = ...
        self.mouse1x_before = 0
        self.mouse1y_before = 0
        self.mouse2x_before = 0
        self.mouse2y_before = 0
        self.x_pos = None
        self.y_pos = None
        self.theta = None
        self.r = None
        self.calib_factor = None
        self.angle = math.radians(63.5)
        self.angle_comp = math.radians(90 - 63.5)

        self.plot_timer: QTimer = ...
        self.data_timer: QTimer = ...

        # self.set_mouse()
        # self.interval = 0.1 if self.frquency_line.text() == '' else 1 / float(self.frquency_line.text())
        # self.update_data_thread = UpdateDataThread(self.mouse1, self.mouse2, self.interval)
        self.fig_ntb = None
        self.gridlayout = None
        self.trace_fig = None
        self.app = app
        self.setup_ui()

        self.connect_signals()
        self.setting_widgets = [self.swap_button, self.calib_factor_line, self.ball_radius_line, self.frquency_line,
                                self.plot_size_line, self.mouse_type_combo, self.mouse_type_combo_2]
        set_button(
            enabled=[self.test_start_button, self.record_start_button, self.vs_on_button, self.feeding_on_button],
            disabled=[self.record_stop_button, self.test_stop_button, self.vs_off_button, self.feeding_off_button])

    def setup_ui(self):
        self.setupUi(self)
        self.trace_fig = Mplplot()
        self.fig_ntb = NavigationToolbar(self.trace_fig, self)
        self.gridlayout = QGridLayout(self.groupBox)
        self.gridlayout.addWidget(self.trace_fig)
        self.gridlayout.addWidget(self.fig_ntb)
        self.canvas_size = int(self.plot_size_line.text())
        self.y_upper = self.canvas_size
        self.y_lower = - self.canvas_size
        self.x_upper = self.canvas_size
        self.x_lower = - self.canvas_size
        self.mouse_type_combo.addItems([key for key, _ in supported_mouses.items()])
        self.mouse_type_combo_2.addItems([key for key, _ in supported_mouses.items()])
        self.trace_fig.add_line(self.x_data, self.y_data)
        self.trace_fig.axes.set_xlim(-self.canvas_size, self.canvas_size)
        self.trace_fig.axes.set_ylim(-self.canvas_size, self.canvas_size)

    def connect_signals(self):
        self.swap_button.clicked.connect(self.swap_mouse)
        self.mouse_type_combo.currentIndexChanged.connect(self.set_mouse1)
        self.mouse_type_combo_2.currentIndexChanged.connect(self.set_mouse2)
        self.test_start_button.clicked.connect(self.test_start)
        self.test_stop_button.clicked.connect(self.test_stop)
        self.record_start_button.clicked.connect(self.record_start)
        self.record_stop_button.clicked.connect(self.record_stop)
        self.feeding_on_button.clicked.connect(self.feeding_on)
        self.feeding_off_button.clicked.connect(self.feeding_off)
        self.vs_on_button.clicked.connect(self.vs_on)
        self.vs_off_button.clicked.connect(self.vs_off)
        # self.update_data_thread.signal_update.connect(self.update_data_thread_slot)

    def set_mouse1(self):
        mouse_type1 = self.mouse_type_combo.currentText()
        print(f'mouse1: {mouse_type1}')
        self.mouse1 = Mouse(mouse_type1)
        detect_mouse1 = threading.Thread(target=self.mouse1.update, daemon=True)
        detect_mouse1.start()

    def set_mouse2(self):
        mouse_type2 = self.mouse_type_combo_2.currentText()
        print(f'mouse2: {mouse_type2}')
        self.mouse2 = Mouse(mouse_type2)
        detect_mouse2 = threading.Thread(target=self.mouse2.update, daemon=True)
        detect_mouse2.start()

    def swap_mouse(self):
        print('Mouse Swapped')
        self.mouse1, self.mouse2 = self.mouse2, self.mouse1

    def test_start(self):
        set_button(enabled=[self.test_stop_button, self.vs_on_button, self.feeding_on_button],
                   disabled=[self.test_start_button, self.record_start_button, self.record_stop_button,
                             self.vs_off_button, self.feeding_off_button])
        set_button(disabled=self.setting_widgets)

        self.exp_start_time = time.time()
        self.x_pos = 0.
        self.y_pos = 0.
        self.theta = 0.
        self.r = float(self.ball_radius_line.text())
        self.calib_factor = float(self.calib_factor_line.text())

        print('start tracking')
        self.data_timer = QTimer()
        self.data_timer.setTimerType(0)
        interval = 1 / float(self.frquency_line.text()) * 1e3  # ms
        self.data_timer.timeout.connect(self.update_data)
        self.mouse1.clear()
        self.mouse2.clear()
        self.data_timer.start(int(interval))

        self.plot_timer = QTimer()
        self.plot_timer.setTimerType(0)
        self.plot_timer.timeout.connect(self.plot_data)
        self.plot_timer.start(33)

    def test_stop(self):
        set_button(
            enabled=[self.test_start_button, self.record_start_button, self.vs_on_button, self.feeding_on_button],
            disabled=[self.record_stop_button, self.test_stop_button, self.vs_off_button, self.feeding_off_button])
        set_button(enabled=self.setting_widgets)

        print('stop tracking')
        self.plot_timer.stop()
        self.data_timer.stop()
        self.redraw()

    def record_start(self):
        set_button(enabled=[self.record_stop_button],
                   disabled=[self.test_start_button, self.record_start_button, self.test_stop_button])
        set_button(disabled=self.setting_widgets)
        self.exp_start_time = time.time()
        self.update_data_thread.interval = 1 / float(self.frquency_line.text())
        self.x_pos = 0.
        self.y_pos = 0.
        self.theta = 0.
        self.r = float(self.ball_radius_line.text())
        self.calib_factor = float(self.calib_factor_line.text())
        print('start tracking')
        self.update_data_thread.start()

    def record_stop(self):
        print('stop tracking')
        set_button(enabled=[self.test_start_button, self.record_start_button],
                   disabled=[self.record_stop_button, self.test_stop_button])
        set_button(enabled=self.setting_widgets)
        self.update_data_thread.terminate()
        self.save_data()
        self.redraw()

    def feeding_on(self):
        print('Feeding on')
        if self.exp_start_time is not None:
            timestamp = time.time() - self.exp_start_time
            self.feeding_timestamps.append(timestamp)
            print('Time: %.2f s' % timestamp)
        set_button(disabled=[self.feeding_on_button], enabled=[self.feeding_off_button])

    def feeding_off(self):
        print('Feeding off')
        if self.exp_start_time is not None:
            timestamp = time.time() - self.exp_start_time
            self.feeding_timestamps.append(timestamp)
            print('Time: %.2f s' % timestamp)
        set_button(enabled=[self.feeding_on_button], disabled=[self.feeding_off_button])

    def vs_on(self):
        print('Visual stimuli on')
        if self.exp_start_time is not None:
            timestamp = time.time() - self.exp_start_time
            self.vs_timestamps.append(timestamp)
            print('Time: %.2f s' % timestamp)
        set_button(disabled=[self.vs_on_button], enabled=[self.vs_off_button])

    def vs_off(self):
        print('Visual stimuli off')
        if self.exp_start_time is not None:
            timestamp = time.time() - self.exp_start_time
            self.vs_timestamps.append(timestamp)
            print('Time: %.2f s' % timestamp)
        set_button(enabled=[self.vs_on_button], disabled=[self.vs_off_button])

    def redraw(self):
        self.mouse1x_before = 0
        self.mouse1y_before = 0
        self.mouse2x_before = 0
        self.mouse2y_before = 0
        self.exp_start_time = None
        self.x_data.clear()
        self.y_data.clear()
        self.x_show.clear()
        self.y_show.clear()
        self.timestamps.clear()
        self.feeding_timestamps.clear()
        self.vs_timestamps.clear()
        self.trace_fig.line.set_xdata(self.x_data)
        self.trace_fig.line.set_ydata(self.y_data)
        self.trace_fig.axes.set_xlim(-self.canvas_size, self.canvas_size)
        self.trace_fig.axes.set_ylim(-self.canvas_size, self.canvas_size)
        self.trace_fig.draw()
        self.x_display_label.setText('0')
        self.y_display_label.setText('0')
        self.time_display_label.setText('0')

    def update_data(self):
        timestamp = time.time() - self.exp_start_time
        m1x, m1y = self.mouse1.X - self.mouse1x_before, self.mouse1.Y - self.mouse1y_before
        m2x, m2y = self.mouse2.X - self.mouse2x_before, self.mouse2.Y - self.mouse2y_before
        self.mouse1x_before, self.mouse1y_before = self.mouse1.X, self.mouse1.Y
        self.mouse2x_before, self.mouse2y_before = self.mouse2.X, self.mouse2.Y
        vm1x, vm1y, _, vm2y = m1x, m1y, m2x, m2y  # sign ?
        wx = self.calib_factor * vm1y
        wy = -self.calib_factor * vm1x
        wz = -self.calib_factor / self.r * (math.sin(self.angle_comp) * vm1y + vm2y) / math.cos(self.angle_comp)
        self.theta -= wz
        pos_delta = rot_mat(self.theta) @ np.array([[-wy], [wx]])
        x, y = self.x_pos + pos_delta[0].item(), self.y_pos + pos_delta[1].item()
        self.x_pos, self.y_pos = x, y
        self.x_data.append(x)
        self.y_data.append(y)
        self.timestamps.append(timestamp)

        if len(self.timestamps) > 1:
            print(self.timestamps[-1] - self.timestamps[-2])
        # self.x_show, self.y_show = self.x_data[-min(len(self.x_data), self.max_timestamps_plot):], self.y_data[
        #                                                                                            -min(
        #                                                                                                len(self.y_data),
        #                                                                                                self.max_timestamps_plot):]

        self.x_show.write_item(x)
        self.y_show.write_item(y)

    def plot_data(self):
        if not self.x_show.is_empty():
            self.trace_fig.line.set_xdata(self.x_show.get_data())
            self.trace_fig.line.set_ydata(self.y_show.get_data())
            self.x_display_label.setText('%.2f' % self.x_data[-1])
            self.y_display_label.setText('%.2f' % self.y_data[-1])
            self.time_display_label.setText('%.2f' % self.timestamps[-1])
            self.trace_fig.draw()


    def save_data(self):
        data = np.stack([np.array(self.x_data), np.array(self.y_data), np.array(self.timestamps)], axis=1)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        timenow = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        fname = os.path.join(dir_path, f'runs/data_trajectory_{timenow}.npy')
        np.save(fname, data)
        print(f'data saved at {fname}')

        feeding_time = np.array(self.feeding_timestamps).reshape(-1, 1)
        print(feeding_time)
        fname = os.path.join(dir_path, f'runs/data_feeding_time_{timenow}.npy')
        np.save(fname, feeding_time)
        print(f'feeding timestamps saved at {fname}')

        vs_time = np.array(self.vs_timestamps)
        fname = os.path.join(dir_path, f'runs/data_visual_stimuli_time_{timenow}.npy')
        np.save(fname, vs_time)
        print(f'visual stimuli timestamps saved at {fname}')

# class UpdateDataThread(QThread):
#     _signal_update = pyqtSignal(object)
#
#     def __init__(self, mouse1, mouse2, interval, parent=None):
#         super(UpdateDataThread, self).__init__(parent)
#         self.mut = QMutex()
#         self.mouse1: Mouse = mouse1
#         self.mouse2: Mouse = mouse2
#         self.interval = interval
#
#     def run(self):
#         self.mouse1.clear()
#         self.mouse2.clear()
#         while True:
#             mouse1x_before, mouse1y_before = self.mouse1.X, self.mouse1.Y
#             mouse2x_before, mouse2y_before = self.mouse2.X, self.mouse2.Y
#             time.sleep(self.interval * 0.9)
#             m1x, m1y = self.mouse1.X - mouse1x_before, self.mouse1.Y - mouse1y_before
#             m2x, m2y = self.mouse2.X - mouse2x_before, self.mouse2.Y - mouse2y_before
#             self._signal_update.emit((m1x, m1y, m2x, m2y, time.time()))
#
#     @property
#     def signal_update(self):
#         return self._signal_update
