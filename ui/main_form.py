import os

from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "main_form.ui"))


class SpeckleQGIS_MainForm(QtWidgets.QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SpeckleQGIS_MainForm, self).__init__(parent)
        self.setupUi(self)

    def closeEvent(self, event):
        event.accept()
