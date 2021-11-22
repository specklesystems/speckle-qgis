import os
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "streamlist_dialog.ui")
)

class StreamListDialog(QtWidgets.QWidget):
    streams_add_button: QtWidgets.QPushButton
    streams_reload_button: QtWidgets.QPushButton
    streams_remove_button: QtWidgets.QPushButton


    def __init__(self, parent=None):
        super(StreamList, self).__init__(parent)
        self.setupUi(self)
