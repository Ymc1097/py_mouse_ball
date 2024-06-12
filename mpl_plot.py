import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtWidgets
from matplotlib.lines import Line2D
from matplotlib.figure import Figure


class Mplplot(FigureCanvas):
    def __init__(self, parent=None, width=3, height=3):
        self.line = None
        self.fig = Figure(figsize=(width, height))
        super(Mplplot, self).__init__(self.fig)
        self.setParent(parent)
        self.axes = self.fig.add_subplot(111)
        self.axes.grid(True)
        self.axes.set_xlabel('Side Stepping', size=12)
        self.axes.set_ylabel('Forward Walking', size=12)

        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def add_line(self, x_data, y_data):
        self.line = Line2D(x_data, y_data)
        self.axes.add_line(self.line)
