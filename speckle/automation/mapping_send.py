import inspect
import os
from typing import Any, List, Tuple, Union
from speckle.converter.layers import getAllLayers
from speckle.converter.layers.utils import getLayerGeomType
from ui.logger import logToUser
import ui.speckle_qgis_dialog
from qgis.core import Qgis, QgsIconUtils, QgsVectorLayer, QgsRasterLayer

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
        self.setMinimumWidth(500)
        self.setWindowTitle("Create custom mappings")

        self.addTransform.setStyleSheet("QPushButton {color: black; padding:3px;padding-left:5px;border: none; } QPushButton:hover { background-color: lightgrey}")
        self.removeTransform.setStyleSheet("QPushButton {color: black; padding:3px;padding-left:5px;border: none; } QPushButton:hover { background-color: lightgrey}")
        
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.addTransform.clicked.connect(self.onAddTransform)
        self.removeTransform.clicked.connect(self.onRemoveTransform)
        self.transformDropdown.currentIndexChanged.connect(self.populateLayersByTransform)


        return
        self.speckle_client = speckle_client

        self.name_field.textChanged.connect(self.nameCheck)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)
        self.accounts_dropdown.currentIndexChanged.connect(self.onAccountSelected)
        self.populate_accounts_dropdown()
    
    def runSetup(self):
        
        self.populateTransforms()
        self.populateLayersByTransform()
        self.populateSavedTransforms()

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

###########################################################

    def populateSavedTransforms(self): #, savedTransforms: Union[List, None] = None, getLayer: Union[str, None] = None, getTransform: Union[str, None] = None):

        self.transformationsList.clear()
        vals = self.dataStorage.savedTransforms  
        all_l_names = [l.name() for l in self.dataStorage.all_layers]

        for item in vals:
            layer_name = item.split("  ->  ")[0]
            transform_name = item.split("  ->  ")[1]

            layer = None
            for l in self.dataStorage.all_layers: 
                if layer_name == l.name():
                    layer = l
            if layer is None: 
                self.dataStorage.savedTransforms.remove(item)
            else:
                if transform_name not in self.dataStorage.transformsCatalog: 
                    self.dataStorage.savedTransforms.remove(item)
                elif all_l_names.count(layer.name()) > 1:
                    self.dataStorage.savedTransforms.remove(item)
                else: 
                    listItem = QListWidgetItem(item)
                    icon = QgsIconUtils().iconForLayer(layer)
                    listItem.setIcon(icon)

                    self.transformationsList.addItem(listItem) 

    def populateLayersByTransform(self):
        try:
            self.layerDropdown.clear()
            root = self.dataStorage.project.layerTreeRoot()
            self.dataStorage.all_layers = getAllLayers(root)

            transform = str(self.transformDropdown.currentText())
            layers_dropdown = []

            for i, layer in enumerate(self.dataStorage.all_layers):

                listItem = None
                if "extrude" in transform.lower():
                    
                    if isinstance(layer, QgsVectorLayer):
                        geom_type = getLayerGeomType(layer)
                        if "polygon" in geom_type.lower():
                            listItem = layer.name()
                        
                elif "elevation" in transform.lower():
                    if isinstance(layer, QgsRasterLayer):
                        listItem = layer.name()
                
                if listItem is not None:
                    layers_dropdown.append(listItem)
                    self.layerDropdown.addItem(listItem)  
                    icon = QgsIconUtils().iconForLayer(layer)
                    self.layerDropdown.setItemIcon(len(layers_dropdown)-1, icon)  

        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return
    
