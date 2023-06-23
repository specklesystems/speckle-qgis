from specklepy_qt_ui.qt_ui.dockwidget_main import SpeckleQGISDialog as SpeckleQGISDialog_UI
import specklepy_qt_ui.qt_ui

from speckle.ui_widgets.widget_transforms import MappingSendDialogQGIS 

from PyQt5 import QtWidgets, uic
import os
from specklepy.logging.exceptions import (SpeckleException, GraphQLException)
from specklepy.logging import metrics


from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QCheckBox, QListWidgetItem, QHBoxLayout, QWidget 
from PyQt5.QtCore import pyqtSignal


from specklepy_qt_ui.qt_ui.widget_transforms import MappingSendDialog
from specklepy_qt_ui.qt_ui.LogWidget import LogWidget
from specklepy_qt_ui.qt_ui.logger import logToUser
from specklepy_qt_ui.qt_ui.DataStorage import DataStorage

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(specklepy_qt_ui.qt_ui.__file__), os.path.join("ui", "dockwidget_main.ui") )
)

class SpeckleQGISDialog(SpeckleQGISDialog_UI, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(SpeckleQGISDialog_UI, self).__init__(parent)
        
        self.setupUi(self)
        self.runAllSetup()

    def createMappingDialog(self):

        if self.mappingSendDialog is None:
            self.mappingSendDialog = MappingSendDialogQGIS(None)
            self.mappingSendDialog.dataStorage = self.dataStorage

        self.mappingSendDialog.runSetup()
