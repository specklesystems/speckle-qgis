import inspect
import os
from typing import Any, List, Tuple, Union
from ui.logger import logToUser
import ui.speckle_qgis_dialog
from qgis.core import Qgis

from speckle.logging import logger
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtWidgets import QCheckBox, QListWidgetItem
from qgis.PyQt.QtCore import pyqtSignal
from specklepy.api.models import Stream
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException
from speckle.utils import logger
from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from gql import gql

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "mapping_send.ui")
)

class MappingSendDialog(QtWidgets.QWidget, FORM_CLASS):

    dialog_button_box: QtWidgets.QDialogButtonBox = None
    layerDropdown: QtWidgets.QComboBox
    transformDropdown: QtWidgets.QComboBox
    addTransform: QtWidgets.QPushButton
    removeTransform: QtWidgets.QPushButton
    transformationsList: QtWidgets.QListWidget

    dataStorage: Any = None

    #Events
    #handleStreamCreate = pyqtSignal(Account, str, str, bool)

    def __init__(self, parent=None):
        super(MappingSendDialog,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        self.setupUi(self)
        self.setMinimumWidth(400)
        self.setWindowTitle("Create custom transformations")

        self.addTransform.setStyleSheet("QPushButton {color: black; padding:3px;padding-left:5px;border: none; } QPushButton:hover { background-color: lightgrey}")
        self.removeTransform.setStyleSheet("QPushButton {color: black; padding:3px;padding-left:5px;border: none; } QPushButton:hover { background-color: lightgrey}")
        
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.addTransform.clicked.connect(self.onAddTransform)
        self.removeTransform.clicked.connect(self.onRemoveTransform)


        return
        self.speckle_client = speckle_client

        self.name_field.textChanged.connect(self.nameCheck)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)
        self.accounts_dropdown.currentIndexChanged.connect(self.onAccountSelected)
        self.populate_accounts_dropdown()
    
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

