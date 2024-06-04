import datetime
import math
import os
import threading
import time

import numpy as np
from PyQt5.QtCore import pyqtSignal, QThread, QMutex
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


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        super(QMainWindow, self).__init__()
        self.angle = math.radians(63.5)
        self.angle_comp = math.radians(90-63.5)
        self.mut = QMutex()
        self.exp_start_time = None
        self.max_timestamps_plot: int = 1000
        self.canvas_size = None
        self.y_upper = None
        self.y_lower = None
        self.x_upper = None
        self.x_lower = None
        self.y_data = []
        self.x_data = []
        self.timestamps = []
        self.fig_ntb = None
        self.gridlayout = None
        self.trace_fig = None
        self.app = app
        self.setup_ui()
        self.mouse2 = None
        self.mouse1 = None
        self.x_pos = None
        self.y_pos = None
        self.theta = None
        self.r = None
        self.calib_factor = None

        # self.set_mouse()
        self.interval = 0.1 if self.frquency_line.text() == '' else 1 / float(self.frquency_line.text())
        self.update_data_thread = UpdateDataThread(self.mouse1, self.mouse2, self.interval)
        self.connect_signals()
        self.setting_widgets = [self.swap_button, self.calib_factor_line, self.ball_radius_line, self.frquency_line,
                                self.plot_size_line, self.mouse_type_combo, self.mouse_type_combo_2]
        set_button(enabled=[self.test_start_button, self.record_start_button],
                   disabled=[self.record_stop_button, self.test_stop_button])

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
        self.update_data_thread.signal_update.connect(self.update_data_thread_slot)

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
        self.update_data_thread = UpdateDataThread(self.mouse1, self.mouse2, 1 / float(self.frquency_line.text()))
        self.update_data_thread.signal_update.connect(self.update_data_thread_slot)
        set_button(enabled=[self.test_stop_button],
                   disabled=[self.test_start_button, self.record_start_button, self.record_stop_button])
        set_button(disabled=self.setting_widgets)

        self.exp_start_time = time.time()
        self.x_pos = 0.
        self.y_pos = 0.
        self.theta = 0.
        self.r = float(self.ball_radius_line.text())
        self.calib_factor = float(self.calib_factor_line.text())
        print('start tracking')
        self.update_data_thread.start()

    def test_stop(self):
        print('stop tracking')
        set_button(enabled=[self.test_start_button, self.record_start_button],
                   disabled=[self.record_stop_button, self.test_stop_button])
        set_button(enabled=self.setting_widgets)
        self.update_data_thread.terminate()
        self.redraw()

    def record_start(self):
        self.update_data_thread = UpdateDataThread(self.mouse1, self.mouse2, 1 / float(self.frquency_line.text()))
        self.update_data_thread.signal_update.connect(self.update_data_thread_slot)
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

    def redraw(self):
        self.x_data.clear()
        self.y_data.clear()
        self.timestamps.clear()
        self.trace_fig.line.set_xdata(self.x_data)
        self.trace_fig.line.set_ydata(self.y_data)
        self.trace_fig.axes.set_xlim(-self.canvas_size, self.canvas_size)
        self.trace_fig.axes.set_ylim(-self.canvas_size, self.canvas_size)
        self.trace_fig.draw()
        self.x_display_label.setText('0')
        self.y_display_label.setText('0')
        self.time_display_label.setText('0')

    def update_data_thread_slot(self, data):
        m1x, m1y, m2x, m2y, timestamp = data
        vm1x, vm1y, vm2x, vm2y = m1x, m1y, m2x, m2y  # sign ?
        wx = self.calib_factor * vm1y
        wy = -self.calib_factor * vm1x
        wz = -self.calib_factor / self.r * (math.sin(self.angle_comp) * vm1y + vm2y) / math.cos(self.angle_comp)
        self.theta -= wz
        pos_delta = rot_mat(self.theta) @ np.array([[-wy], [wx]])
        x, y = self.x_pos + pos_delta[0].item(), self.y_pos + pos_delta[1].item()
        self.x_pos, self.y_pos = x, y
        self.x_data.append(x)
        self.y_data.append(y)
        timestamp -= self.exp_start_time
        self.timestamps.append(timestamp)
        x_show, y_show = self.x_data[-min(len(self.x_data), self.max_timestamps_plot):], self.y_data[
                                                                                         -min(len(self.y_data),
                                                                                              self.max_timestamps_plot):]
        self.trace_fig.line.set_xdata(x_show)
        self.trace_fig.line.set_ydata(y_show)
        if x < self.x_lower or x > self.x_upper or y < self.y_lower or y > self.y_upper:
            self.trace_fig.axes.set_xlim(x - self.canvas_size, x + self.canvas_size)
            self.trace_fig.axes.set_ylim(y - self.canvas_size, y + self.canvas_size)
            self.x_lower, self.x_upper = x - self.canvas_size, x + self.canvas_size
            self.y_lower, self.y_upper = y - self.canvas_size, y + self.canvas_size
        self.x_display_label.setText('%.2f' % x)
        self.y_display_label.setText('%.2f' % y)
        self.time_display_label.setText('%.2f' % timestamp)
        self.trace_fig.draw()

    def save_data(self):
        data = np.stack([np.array(self.x_data), np.array(self.y_data), np.array(self.timestamps)], axis=1)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(dir_path, f'runs/data_{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}.npy')
        np.save(fname, data)
        print(f'data saved at {fname}')


class UpdateDataThread(QThread):
    _signal_update = pyqtSignal(object)

    def __init__(self, mouse1, mouse2, interval, parent=None):
        super(UpdateDataThread, self).__init__(parent)
        self.mut = QMutex()
        self.mouse1: Mouse = mouse1
        self.mouse2: Mouse = mouse2
        self.interval = interval

    def run(self):
        self.mouse1.clear()
        self.mouse2.clear()
        while True:
            mouse1x_before, mouse1y_before = self.mouse1.X, self.mouse1.Y
            mouse2x_before, mouse2y_before = self.mouse2.X, self.mouse2.Y
            time.sleep(self.interval * 0.9)
            m1x, m1y = self.mouse1.X - mouse1x_before, self.mouse1.Y - mouse1y_before
            m2x, m2y = self.mouse2.X - mouse2x_before, self.mouse2.Y - mouse2y_before
            self._signal_update.emit((m1x, m1y, m2x, m2y, time.time()))

    @property
    def signal_update(self):
        return self._signal_update
