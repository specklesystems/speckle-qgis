import inspect
import os
from typing import Any, List, Tuple, Union
from ui.logger import logToUser
import ui.speckle_qgis_dialog
from qgis.core import Qgis

from speckle.logging import logger
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtWidgets import QCheckBox, QListWidgetItem, QHBoxLayout, QWidget, QLabel
from qgis.PyQt.QtCore import pyqtSignal
from specklepy.api.models import Stream
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException
from speckle.utils import logger
from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from gql import gql


#from qgis.PyQt import QtCore, QtWidgets #, QtWebEngineWidgets
from PyQt5 import *
from PyQt5.QtCore import QUrl

from speckle.notifications.utils import addDashboardTable


try:
    import plotly.express as px
    from PyQt5.QtWebKitWidgets import QWebView
    import pandas as pd
    #from PyQtWebEngine import * 
except: 
    import os; import sys; import subprocess; pythonExec = os.path.dirname(sys.executable) + "\\python3"
    #result = subprocess.run([pythonExec, "-m", "pip", "install", "pyqtgraph"], capture_output=True, text=True, shell=True, timeout=1000); print(result)
    result = subprocess.run([pythonExec, "-m", "pip", "install", "plotly"], capture_output=True, text=True, shell=True, timeout=1000); print(result)
    result = subprocess.run([pythonExec, "-m", "pip", "install", "PyQtWebEngine"], capture_output=True, text=True, shell=True, timeout=1000); print(result)
    result = subprocess.run([pythonExec, "-m", "pip", "install", "pandas"], capture_output=True, text=True, shell=True, timeout=1000); print(result)

    import plotly.express as px

import os 


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "addContext.ui")
)

class ContextVisualsDialog(QtWidgets.QWidget, FORM_CLASS):

    dialog_button_box: QtWidgets.QDialogButtonBox = None
    layerDropdown: QtWidgets.QComboBox
    transformDropdown: QtWidgets.QComboBox
    addTransform: QtWidgets.QPushButton
    removeTransform: QtWidgets.QPushButton
    transformationsList: QtWidgets.QListWidget

    dataStorage: Any = None
    
    chart: QWidget
    browser = None
    existing_web: int = 0

    #Events
    #handleStreamCreate = pyqtSignal(Account, str, str, bool)

    def __init__(self, parent=None):
        super(ContextVisualsDialog,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        self.setupUi(self)
        self.setMinimumWidth(900)
        self.setWindowTitle("Title")

        self.addTransform.setStyleSheet("QPushButton {color: black; padding:3px;padding-left:5px;border: none; } QPushButton:hover { background-color: lightgrey}")
        self.removeTransform.setStyleSheet("QPushButton {color: black; padding:3px;padding-left:5px;border: none; } QPushButton:hover { background-color: lightgrey}")
        
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.addTransform.clicked.connect(self.onAddTransform)
        self.removeTransform.clicked.connect(self.onRemoveTransform)

        return

    def createChart(self):

        # https://stackoverflow.com/questions/60522103/how-to-have-plotly-graph-as-pyqt5-widget 
        

        if self.existing_web == 0:
            self.browser = QWebView(self)
        
        #self.browser.setHtml(fig.to_html(include_plotlyjs='cdn'))
        self.browser.setUrl(QUrl("https://speckle.xyz/streams/e2effcfa27/commits/f76cedd9a6"))
        
        self.chart.layout = QHBoxLayout(self.chart)
        self.chart.layout.setContentsMargins(0,0,0,0)
        self.browser.setMaximumHeight(400)

        if self.existing_web == 0:
            self.chart.layout.addWidget(self.browser)
            self.existing_web = 1

        return 
    
    def runSetup(self):
        
        self.populateLayers()
        self.populateTransforms()
        self.populateSavedTransforms()

    def populateSavedTransforms(self): #, savedTransforms: Union[List, None] = None, getLayer: Union[str, None] = None, getTransform: Union[str, None] = None):

        self.transformationsList.clear()
        if self.dataStorage.savedTransforms is not None and isinstance(self.dataStorage.savedTransforms, List):
            for item in self.dataStorage.savedTransforms:
                self.transformationsList.addItem(QListWidgetItem(item))

    def onAddTransform(self):
        if len(self.layerDropdown.currentText())>1 and len(self.transformDropdown.currentText())>1:
            listItem = str(self.layerDropdown.currentText()) + "  ->  " + str(self.transformDropdown.currentText())
            
            if listItem not in self.dataStorage.savedTransforms:
                self.dataStorage.savedTransforms.append(listItem)
                self.populateSavedTransforms()
    
    def onRemoveTransform(self):

        if self.transformationsList.currentItem() is not None:
            #if len(self.layerDropdown.currentText())>1 and len(self.transformDropdown.currentText())>1:
            listItem = self.transformationsList.currentItem().text()
            print(listItem)
            
            if listItem in self.dataStorage.savedTransforms: 
                self.dataStorage.savedTransforms.remove(listItem)

            self.populateSavedTransforms()

    def onOkClicked(self):
        try:
            self.close()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return
    
    def populateLayers(self):
        try:
            self.layerDropdown.clear()
            for layer in self.dataStorage.all_layers:
                listItem = layer.name()
                self.layerDropdown.addItem(listItem)    
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return
    
    def populateTransforms(self):
        try:
            self.transformDropdown.clear()
            for item in self.dataStorage.transformsCatalog:
                self.transformDropdown.addItem(item)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

    def nameCheck(self):
        return
        try:
            if len(self.name_field.text()) == 0 or len(self.name_field.text()) >= 3:
                self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
            else: 
                self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 
            return
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

