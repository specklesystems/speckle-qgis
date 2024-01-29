import inspect
import os
from typing import Any, List, Tuple, Union
from speckle.converter.layers import getAllLayers
from speckle.converter.layers.utils import getElevationLayer, getLayerGeomType
from specklepy_qt_ui.qt_ui.widget_transforms import MappingSendDialog
from specklepy_qt_ui.qt_ui.logger import displayUserMsg

from speckle.utils.panel_logging import logToUser

from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsIconUtils

from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QListWidgetItem

from specklepy.logging import metrics
from osgeo import gdal
import webbrowser
import specklepy_qt_ui.qt_ui

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(
        os.path.join(
            os.path.dirname(specklepy_qt_ui.qt_ui.__file__), "ui", "transforms.ui"
        )
    )
)


class MappingSendDialogQGIS(MappingSendDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(MappingSendDialog, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        self.setupUi(self)
        self.runAllSetup()

    def runSetup(self):
        self.attr_label.setEnabled(False)
        self.attrDropdown.setEnabled(False)
        self.dialog_button.setText("Apply")

        self.populateTransforms()
        self.populateLayersByTransform()
        self.populateSavedTransforms(self.dataStorage)
        self.populateSavedElevationLayer(self.dataStorage)

    def populateSavedTransforms(
        self, dataStorage
    ):  # , savedTransforms: Union[List, None] = None, getLayer: Union[str, None] = None, getTransform: Union[str, None] = None):
        if dataStorage is not None:
            self.dataStorage = dataStorage  # making sure lists are synced
        self.transformationsList.clear()
        vals = self.dataStorage.savedTransforms
        all_l_names = [l.name() for l in self.dataStorage.all_layers]

        for item in vals:
            layer_name = item.split("  ->  ")[0].split(" ('")[0]
            transform_name = item.split("  ->  ")[1]

            layer = None
            for l in self.dataStorage.all_layers:
                if layer_name == l.name():
                    layer = l
            if layer is None:
                displayUserMsg(
                    f"Layer '{layer_name}' not found in the project.\nTransformation is removed.",
                    level=2,
                )
                self.dataStorage.savedTransforms.remove(item)
            else:
                if transform_name not in self.dataStorage.transformsCatalog:
                    displayUserMsg(
                        f"Saved transformation '{transform_name}' is not valid.\nTransformation is removed.",
                        level=1,
                    )
                    self.dataStorage.savedTransforms.remove(item)
                elif all_l_names.count(layer.name()) > 1:
                    displayUserMsg(
                        f"Layer name '{layer.name()}' is used for more than 1 layer in the project.\nTransformation is removed.",
                        level=1,
                    )
                    self.dataStorage.savedTransforms.remove(item)
                else:
                    listItem = QListWidgetItem(item)
                    icon = QgsIconUtils().iconForLayer(layer)
                    listItem.setIcon(icon)

                    self.transformationsList.addItem(listItem)

    def onAddTransform(self):
        from speckle.utils.project_vars import set_transformations

        root = self.dataStorage.project.layerTreeRoot()
        self.dataStorage.all_layers = getAllLayers(root)

        if (
            len(self.layerDropdown.currentText()) > 1
            and len(self.transformDropdown.currentText()) > 1
        ):
            listItem = (
                str(self.layerDropdown.currentText())
                + "  ->  "
                + str(self.transformDropdown.currentText())
            )
            layer_name = listItem.split("  ->  ")[0].split(" ('")[0]
            transform_name = listItem.split("  ->  ")[1].lower()

            exists = 0
            for record in self.dataStorage.savedTransforms:
                current_layer_name = record.split("  ->  ")[0].split(" ('")[0]
                current_transf_name = record.split("  ->  ")[1].lower()
                if layer_name == current_layer_name:  # in layers
                    exists += 1
                    displayUserMsg(
                        "Selected layer already has a transformation applied", level=1
                    )
                    break

            if exists == 0:
                layer = None
                for l in self.dataStorage.all_layers:
                    if layer_name == l.name():
                        layer = l
                if layer is not None:
                    if (
                        "attribute" in transform_name
                        and self.attrDropdown.currentText() != ""
                    ):
                        listItem = (
                            str(self.layerDropdown.currentText())
                            + " ('"
                            + str(self.attrDropdown.currentText())
                            + "')  ->  "
                            + str(self.transformDropdown.currentText())
                        )

                    self.dataStorage.savedTransforms.append(listItem)
                    self.populateSavedTransforms(self.dataStorage)

                    try:
                        metrics.track(
                            "Connector Action",
                            self.dataStorage.active_account,
                            {
                                "name": "Transformation on Send Add",
                                "Transformation": listItem.split("  ->  ")[1],
                                "connector_version": str(
                                    self.dataStorage.plugin_version
                                ),
                            },
                        )
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])

                    set_transformations(self.dataStorage)

    def onRemoveTransform(self):
        from speckle.utils.project_vars import set_transformations

        if self.transformationsList.currentItem() is not None:
            listItem = self.transformationsList.currentItem().text()
            # print(listItem)

            if listItem in self.dataStorage.savedTransforms:
                self.dataStorage.savedTransforms.remove(listItem)

                try:
                    metrics.track(
                        "Connector Action",
                        self.dataStorage.active_account,
                        {
                            "name": "Transformation on Send Remove",
                            "Transformation": listItem.split("  ->  ")[1],
                            "connector_version": str(self.dataStorage.plugin_version),
                        },
                    )
                except Exception as e:
                    logToUser(e, level=2, func=inspect.stack()[0][3])

            self.populateSavedTransforms(self.dataStorage)
            set_transformations(self.dataStorage)

    def onOkClicked(self):
        try:
            self.saveElevationLayer()
            self.close()
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])
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
            logToUser(e, level=2, func=inspect.stack()[0][3])
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

                        # for satellites
                        if "texture" in transform.lower():
                            listItem = layer.name()
                        # for elevation to mesh
                        elif "mesh" in transform.lower():
                            try:
                                if layer.bandCount() == 1:
                                    listItem = layer.name()
                            except:
                                pass

                if listItem is not None:
                    layers_dropdown.append(listItem)
                    self.layerDropdown.addItem(listItem)
                    icon = QgsIconUtils().iconForLayer(layer)
                    self.layerDropdown.setItemIcon(len(layers_dropdown) - 1, icon)

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])
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

            if layerForAttributes is not None and "attribute" in transform_name:
                self.attr_label.setEnabled(True)
                self.attrDropdown.setEnabled(True)

                if "ignore" not in transform_name:
                    self.attrDropdown.addItem("Random height")

                for field in layerForAttributes.fields():
                    field_type = field.type()
                    if field_type in [2, 6, 10]:
                        self.attrDropdown.addItem(str(field.name()))
            else:
                self.attr_label.setEnabled(False)
                self.attrDropdown.setEnabled(False)

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])
            return

    def populateTransforms(self):
        try:
            self.transformDropdown.clear()
            for item in self.dataStorage.transformsCatalog:
                self.transformDropdown.addItem(item)
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])
            return

    def populateSavedElevationLayer(
        self, dataStorage
    ):  # , savedTransforms: Union[List, None] = None, getLayer: Union[str, None] = None, getTransform: Union[str, None] = None):
        try:
            if dataStorage is not None:
                self.dataStorage = dataStorage  # making sure lists are synced
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
                    elif layer.bandCount() != 1:
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
            logToUser(e, level=2, func=inspect.stack()[0][3])
            return

    def saveElevationLayer(self):
        # print("saveElevationLayer")
        from speckle.utils.project_vars import set_elevationLayer

        root = self.dataStorage.project.layerTreeRoot()
        layer = None

        if self.dataStorage is None:
            return

        layerName = str(self.elevationLayerDropdown.currentText())
        try:
            if self.dataStorage.elevationLayer.name() == layerName:
                return
        except:
            pass

        if len(layerName) < 1:
            layer = None
        else:
            self.dataStorage.all_layers = getAllLayers(root)
            all_l_names = [l.name() for l in self.dataStorage.all_layers]
            # print(all_l_names)

            for l in self.dataStorage.all_layers:
                if layerName == l.name():
                    layer = l
                    try:
                        # print(layerName)
                        if all_l_names.count(layer.name()) > 1:
                            displayUserMsg(
                                f"Layer name '{layer.name()}' is used for more than 1 layer in the project",
                                level=1,
                            )
                            layer = None
                            break
                        else:
                            self.dataStorage.elevationLayer = layer
                            set_elevationLayer(self.dataStorage)
                            logToUser(
                                f"Elevation layer '{layerName}' successfully set",
                                level=0,
                            )
                            break
                    except:
                        displayUserMsg(
                            f"Layer '{layer.name()}' is not found in the project",
                            level=1,
                        )
                        layer = None
                        break

        try:
            metrics.track(
                "Connector Action",
                self.dataStorage.active_account,
                {
                    "name": "Add transformation on Send",
                    "Transformation": "Set Layer as Elevation",
                    "connector_version": str(self.dataStorage.plugin_version),
                },
            )
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])

    def onMoreInfo(self):
        webbrowser.open("https://speckle.guide/user/qgis.html#transformations")
