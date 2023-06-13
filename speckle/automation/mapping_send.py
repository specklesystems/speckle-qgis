import inspect
import os
from typing import Any, List, Tuple, Union
from speckle.converter.layers import getAllLayers
from speckle.converter.layers.utils import getElevationLayer, getLayerGeomType
from pyqt_ui.logger import displayUserMsg, logToUser
import pyqt_ui.speckle_qgis_dialog
from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsRasterLayer, QgsIconUtils 

from speckle.logging import logger
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QCheckBox, QListWidgetItem
from qgis.PyQt.QtCore import pyqtSignal
from specklepy.api.models import Stream
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException
from speckle.utils import logger
from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from gql import gql
from specklepy.logging import metrics
from osgeo import gdal 
import webbrowser

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "mapping_send.ui")
)

class MappingSendDialog(QtWidgets.QWidget, FORM_CLASS):

    dialog_button_box: QtWidgets.QPushButton = None
    more_info: QtWidgets.QPushButton = None
    layerDropdown: QtWidgets.QComboBox
    transformDropdown: QtWidgets.QComboBox
    addTransform: QtWidgets.QPushButton
    removeTransform: QtWidgets.QPushButton
    transformationsList: QtWidgets.QListWidget
    elevationLayerDropdown: QtWidgets.QComboBox
    
    attrDropdown: QtWidgets.QComboBox

    dataStorage: Any = None

    #Events
    #handleStreamCreate = pyqtSignal(Account, str, str, bool)

    def __init__(self, parent=None):
        super(MappingSendDialog,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        self.setupUi(self)
        self.setMinimumWidth(600)
        #self.dialog_button_box.setMaximumWidth(30)
        #self.more_info.setMaximumWidth(30)
        #self.setWindowTitle("Add custom transformations")

        self.addTransform.setStyleSheet("QPushButton {color: black; padding:3px;padding-left:5px;border: none; } QPushButton:hover { background-color: lightgrey}")
        self.removeTransform.setStyleSheet("QPushButton {color: black; padding:3px;padding-left:5px;border: none; } QPushButton:hover { background-color: lightgrey}")
        
        #self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.addTransform.clicked.connect(self.onAddTransform)
        self.removeTransform.clicked.connect(self.onRemoveTransform)
        self.transformDropdown.currentIndexChanged.connect(self.populateLayersByTransform)
        self.transformDropdown.currentIndexChanged.connect(self.populateAttributesByLayer)
        self.layerDropdown.currentIndexChanged.connect(self.populateAttributesByLayer)
        self.dialog_button_box.clicked.connect(self.saveElevationLayer)
        self.dialog_button_box.clicked.connect(self.onOkClicked)
        self.more_info.clicked.connect(self.onMoreInfo)


        return
        self.speckle_client = speckle_client

        self.name_field.textChanged.connect(self.nameCheck)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)
        
        self.populate_accounts_dropdown()
    
    def runSetup(self):
        
        #get_transformations(self.dataStorage)
        self.attr_label.setEnabled(False)
        self.attrDropdown.setEnabled(False)

        self.populateTransforms()
        #self.populateLayers()
        self.populateLayersByTransform()
        self.populateSavedTransforms()
        self.populateSavedElevationLayer()

    def populateSavedTransforms(self, dataStorage = None): #, savedTransforms: Union[List, None] = None, getLayer: Union[str, None] = None, getTransform: Union[str, None] = None):

        if dataStorage is not None: 
            self.dataStorage = dataStorage # making sure lists are synced 
        self.transformationsList.clear()
        vals = self.dataStorage.savedTransforms  
        all_l_names = [l.name() for l in self.dataStorage.all_layers]

        for item in vals:
            layer_name = item.split("  ->  ")[0].split(" (\'")[0]
            transform_name = item.split("  ->  ")[1]

            layer = None
            for l in self.dataStorage.all_layers: 
                if layer_name == l.name():
                    layer = l
            if layer is None: 
                displayUserMsg(f"Layer \'{layer_name}\' not found in the project.\nTransformation is removed.", level=2) 
                self.dataStorage.savedTransforms.remove(item)
            else:
                if transform_name not in self.dataStorage.transformsCatalog:
                    displayUserMsg(f"Saved transformation \'{transform_name}\' is not valid.\n. Transformation is removed.", level=1) 
                    self.dataStorage.savedTransforms.remove(item)
                elif all_l_names.count(layer.name()) > 1:
                    displayUserMsg(f"Layer name \'{layer.name()}\' is used for more than 1 layer in the project", level=1) 
                    self.dataStorage.savedTransforms.remove(item)
                else: 
                    listItem = QListWidgetItem(item)
                    icon = QgsIconUtils().iconForLayer(layer)
                    listItem.setIcon(icon)

                    self.transformationsList.addItem(listItem) 

        #if self.dataStorage.savedTransforms is not None and isinstance(self.dataStorage.savedTransforms, List):
        #    for item in self.dataStorage.savedTransforms:
        #        self.transformationsList.addItem(QListWidgetItem(item))

    def onAddTransform(self):
        
        from pyqt_ui.project_vars import set_transformations
        root = self.dataStorage.project.layerTreeRoot()
        self.dataStorage.all_layers = getAllLayers(root)

        if len(self.layerDropdown.currentText())>1 and len(self.transformDropdown.currentText())>1:
            listItem = str(self.layerDropdown.currentText()) + "  ->  " + str(self.transformDropdown.currentText())
            layer_name = listItem.split("  ->  ")[0].split(" (\'")[0]
            transform_name = listItem.split("  ->  ")[1].lower()
            
            exists = 0
            for record in self.dataStorage.savedTransforms: 
                current_layer_name = record.split("  ->  ")[0].split(" (\'")[0]
                current_transf_name = record.split("  ->  ")[1].lower()
                if layer_name == current_layer_name: # in layers
                    exists +=1
                    displayUserMsg("Selected layer already has a transformation applied", level=1) 
                    break
                if ("elevation" in transform_name and "mesh" in transform_name and "texture" not in transform_name) and transform_name == current_transf_name: # in transforms
                    exists +=1
                    displayUserMsg(f"Layer '{current_layer_name}' is already assigned as a 3d elevation", level=1) 
                    break 
            if exists == 0:
                layer = None
                for l in self.dataStorage.all_layers: 
                    if layer_name == l.name():
                        layer = l
                if layer is not None:

                    if "attribute" in transform_name and self.attrDropdown.currentText() != '':
                        listItem = str(self.layerDropdown.currentText()) + " (\'" +  str(self.attrDropdown.currentText()) + "\')  ->  " + str(self.transformDropdown.currentText())
            
                    self.dataStorage.savedTransforms.append(listItem)
                    self.populateSavedTransforms()
                    
                    try:
                        metrics.track("Connector Action", self.dataStorage.active_account, {"name": "Add transformation on Send", "Transformation": listItem.split("  ->  ")[1], "connector_version": str(self.dataStorage.plugin_version)})
                    except Exception as e:
                        logToUser(e, level = 2, func = inspect.stack()[0][3] )
                    
                    set_transformations(self.dataStorage)

    def onRemoveTransform(self):

        from pyqt_ui.project_vars import set_transformations
        if self.transformationsList.currentItem() is not None:
            #if len(self.layerDropdown.currentText())>1 and len(self.transformDropdown.currentText())>1:
            listItem = self.transformationsList.currentItem().text()
            print(listItem)
            
            if listItem in self.dataStorage.savedTransforms: 
                self.dataStorage.savedTransforms.remove(listItem)

            self.populateSavedTransforms()
            set_transformations(self.dataStorage)

    def onOkClicked(self):
        try:
            self.close()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return
    
    def populateLayers(self):
        try:
            self.layerDropdown.clear()
            root = self.dataStorage.project.layerTreeRoot()
            self.dataStorage.all_layers = getAllLayers(root)
            for i, layer in enumerate(self.dataStorage.all_layers):
                listItem = layer.name()
                self.layerDropdown.addItem(listItem)  
                icon = QgsIconUtils().iconForLayer(layer)
                self.layerDropdown.setItemIcon(i, icon)  

        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return
    
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
                        # avoiding tiling layers 
                        ds = gdal.Open(layer.source(), gdal.GA_ReadOnly)
                        if ds is None:
                            continue
                    
                        listItem = layer.name()
                
                if listItem is not None:
                    layers_dropdown.append(listItem)
                    self.layerDropdown.addItem(listItem)  
                    icon = QgsIconUtils().iconForLayer(layer)
                    self.layerDropdown.setItemIcon(len(layers_dropdown)-1, icon)  

        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return
    
    def populateAttributesByLayer(self):
        try:
            self.attrDropdown.clear()
            root = self.dataStorage.project.layerTreeRoot()
            self.dataStorage.all_layers = getAllLayers(root)

            layer_name = str(self.layerDropdown.currentText())
            transform_name = self.transformDropdown.currentText()
            layerForAttributes = None 
            for i, layer in enumerate(self.dataStorage.all_layers):

                if layer_name == layer.name():
                    if isinstance(layer, QgsVectorLayer):
                        geom_type = getLayerGeomType(layer)
                        if "polygon" in geom_type.lower():
                            layerForAttributes = layer
                            break 
                
            if layerForAttributes is not None and 'attribute' in transform_name:
                self.attr_label.setEnabled(True)
                self.attrDropdown.setEnabled(True)

                if 'ignore' not in transform_name:
                    self.attrDropdown.addItem('Random height')  

                for field in layerForAttributes.fields():
                    field_type = field.type()
                    if field_type in [2,6,10]:
                        self.attrDropdown.addItem(str(field.name()))  
            else: 
                self.attr_label.setEnabled(False)
                self.attrDropdown.setEnabled(False)

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


    def populateSavedElevationLayer(self, dataStorage = None): #, savedTransforms: Union[List, None] = None, getLayer: Union[str, None] = None, getTransform: Union[str, None] = None):

        try:
            if dataStorage is not None: 
                self.dataStorage = dataStorage # making sure lists are synced 
            elevationLayer = getElevationLayer(self.dataStorage)

            self.elevationLayerDropdown.clear()
            root = self.dataStorage.project.layerTreeRoot()
            self.dataStorage.all_layers = getAllLayers(root)

            self.elevationLayerDropdown.addItem("")  

            setAsindex = 0
            countRaster = 1
            for i, layer in enumerate(self.dataStorage.all_layers):
                if isinstance(layer, QgsRasterLayer):
                    # avoiding tiling layers 
                    ds = gdal.Open(layer.source(), gdal.GA_ReadOnly)
                    if ds is None:
                        continue

                    listItem = layer.name()
                    self.elevationLayerDropdown.addItem(listItem)  
                    icon = QgsIconUtils().iconForLayer(layer)
                    self.elevationLayerDropdown.setItemIcon(countRaster, icon)  
                    
                    if elevationLayer is not None: 
                        if listItem == elevationLayer.name():
                            setAsindex = countRaster
                    countRaster += 1
            self.elevationLayerDropdown.setCurrentIndex(setAsindex) 
            
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return
    
    def saveElevationLayer(self):
        from pyqt_ui.project_vars import set_elevationLayer
        root = self.dataStorage.project.layerTreeRoot()
        layer = None

        if self.dataStorage is None: return 

        layerName = str(self.elevationLayerDropdown.currentText()) 
        if len(layerName) < 1: 
            layer = None 
        else:
            self.dataStorage.all_layers = getAllLayers(root)
            all_l_names = [l.name() for l in self.dataStorage.all_layers]

            for l in self.dataStorage.all_layers: 
                if layerName == l.name():
                    layer = l
                    try:
                        if all_l_names.count(layer.name()) > 1:
                            displayUserMsg(f"Layer name \'{layer.name()}\' is used for more than 1 layer in the project", level=1) 
                            layer = None
                            break 
                    except: 
                        displayUserMsg(f"Layer \'{layer.name()}\' is not found in the project", level=1) 
                        layer = None
                        break 
            
        self.dataStorage.elevationLayer = layer 
        set_elevationLayer(self.dataStorage)
            
        try:
            metrics.track("Connector Action", self.dataStorage.active_account, {"name": "Add transformation on Send", "Transformation": "Set Layer as Elevation", "connector_version": str(self.dataStorage.plugin_version)})
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3] )
            
    def onMoreInfo(self):
        webbrowser.open("https://github.com/specklesystems/speckle-qgis/tree/main/speckle/automation/Automation.md")
        