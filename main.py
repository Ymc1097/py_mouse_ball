from PyQt5.QtWidgets import QApplication
import sys
from call_mainwindow import Window

if __name__ == '__main__':
    app = QApplication(sys.argv)
    my_window = Window(app)
    my_window.show()
    sys.exit(app.exec_())
