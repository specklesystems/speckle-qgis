"""
Contains all Layer related classes and methods.
"""

import enum
import inspect
import hashlib
import math
from typing import List, Tuple, Union
from specklepy.objects import Base
from specklepy.objects.geometry import (
    Mesh,
    Point,
    Line,
    Curve,
    Circle,
    Ellipse,
    Polycurve,
    Arc,
    Polyline,
)
import os
import time
from datetime import datetime

from plugin_utils.helpers import (
    findFeatColors,
    findOrCreatePath,
    jsonFromList,
    removeSpecialCharacters,
)

# from qgis._core import Qgis, QgsVectorLayer, QgsWkbTypes
try:
    from qgis.core import (
        Qgis,
        QgsProject,
        QgsRasterLayer,
        QgsPoint,
        QgsVectorLayer,
        QgsProject,
        QgsWkbTypes,
        QgsLayerTree,
        QgsLayerTreeGroup,
        QgsLayerTreeNode,
        QgsLayerTreeLayer,
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsFeature,
        QgsFields,
        QgsSingleSymbolRenderer,
        QgsCategorizedSymbolRenderer,
        QgsRendererCategory,
        QgsSymbol,
        QgsUnitTypes,
        QgsVectorFileWriter,
    )
    from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
        gdal,
        osr,
    )
    from PyQt5.QtGui import QColor
except ModuleNotFoundError:
    pass

from specklepy.objects.GIS.geometry import GisPolygonElement, GisNonGeometryElement
from speckle.converter.geometry.point import (
    pointToNative,
    pointToNativeWithoutTransforms,
)
from specklepy.objects.GIS.CRS import CRS
from specklepy.objects.GIS.layers import VectorLayer, RasterLayer, Layer
from specklepy.objects.other import Collection

from speckle.converter.layers import (
    getAllLayers,
)
from speckle.converter.features.feature_conversions import (
    featureToSpeckle,
    rasterFeatureToSpeckle,
    featureToNative,
    nonGeomFeatureToNative,
    cadFeatureToNative,
    bimFeatureToNative,
)
from speckle.converter.layers.utils import (
    collectionsFromJson,
    colorFromSpeckle,
    colorFromSpeckle,
    generate_qgis_app_id,
    generate_qgis_raster_app_id,
    getDisplayValueList,
    getElevationLayer,
    getLayerGeomType,
    getLayerAttributes,
    isAppliedLayerTransformByKeywords,
    tryCreateGroup,
    tryCreateGroupTree,
    trySaveCRS,
    validateAttributeName,
)
from speckle.converter.geometry.mesh import writeMeshToShp

from speckle.converter.layers.symbology import (
    vectorRendererToNative,
    rasterRendererToNative,
    rendererToSpeckle,
)


import numpy as np

from speckle.utils.panel_logging import logToUser

from plugin_utils.helpers import SYMBOL, UNSUPPORTED_PROVIDERS

GEOM_LINE_TYPES = [
    "Objects.Geometry.Line",
    "Objects.Geometry.Polyline",
    "Objects.Geometry.Curve",
    "Objects.Geometry.Arc",
    "Objects.Geometry.Circle",
    "Objects.Geometry.Ellipse",
    "Objects.Geometry.Polycurve",
]


def convertSelectedLayersToSpeckle(
    baseCollection: Collection,
    layers: List[Union["QgsVectorLayer", "QgsRasterLayer"]],
    tree_structure: List[str],
    projectCRS: "QgsCoordinateReferenceSystem",
    plugin,
) -> List[Union[VectorLayer, RasterLayer]]:
    """Converts the current selected layers to Speckle"""
    dataStorage = plugin.dataStorage
    result = []
    try:
        project: QgsProject = plugin.project

        ## Generate dictionnary from the list of layers to send
        jsonTree = {}
        for i, layer in enumerate(layers):
            structure = tree_structure[i]

            if structure.startswith(SYMBOL):
                structure = structure[len(SYMBOL) :]

            levels = structure.split(SYMBOL)
            while "" in levels:
                levels.remove("")

            jsonTree = jsonFromList(jsonTree, levels)

        for i, layer in enumerate(layers):
            data_provider_type = (
                layer.providerType()
            )  # == ogr, memory, gdal, delimitedtext
            if data_provider_type in UNSUPPORTED_PROVIDERS:
                logToUser(
                    f"Layer '{layer.name()}' has unsupported provider type '{data_provider_type}' and cannot be sent",
                    level=2,
                    plugin=plugin.dockwidget,
                )
                return None

            logToUser(
                f"Converting layer '{layer.name()}'...",
                level=0,
                plugin=plugin.dockwidget,
            )
            try:
                for item in plugin.dataStorage.savedTransforms:
                    layer_name = item.split("  ->  ")[0].split(" ('")[0]
                    transform_name = item.split("  ->  ")[1]
                    if layer_name == layer.name():
                        logToUser(
                            f"Applying transformation to layer '{layer_name}': '{transform_name}'",
                            level=0,
                            plugin=plugin.dockwidget,
                        )
            except Exception as e:
                print(e)

            if plugin.dataStorage.savedTransforms is not None:
                for item in plugin.dataStorage.savedTransforms:
                    layer_name = item.split("  ->  ")[0].split(" ('")[0]
                    transform_name = item.split("  ->  ")[1].lower()

                    # check all the conditions for transform
                    if (
                        isinstance(layer, QgsVectorLayer)
                        and layer.name() == layer_name
                        and "extrude" in transform_name
                        and "polygon" in transform_name
                    ):
                        if plugin.dataStorage.project.crs().isGeographic():
                            logToUser(
                                "Extrusion cannot be applied when the project CRS is set to Geographic type",
                                level=2,
                                plugin=plugin.dockwidget,
                            )
                            return None

                        attribute = None
                        if " ('" in item:
                            attribute = item.split(" ('")[1].split("') ")[0]
                        if (
                            attribute is None
                            or str(attribute) not in layer.fields().names()
                        ) and "ignore" in transform_name:
                            logToUser(
                                "Attribute for extrusion not found",
                                level=2,
                                plugin=plugin.dockwidget,
                            )
                            return None

                    elif (
                        isinstance(layer, QgsRasterLayer)
                        and layer.name() == layer_name
                        and "elevation" in transform_name
                    ):
                        if plugin.dataStorage.project.crs().isGeographic():
                            logToUser(
                                "Raster layer transformation cannot be applied when the project CRS is set to Geographic type",
                                level=2,
                                plugin=plugin.dockwidget,
                            )
                            return None

            converted = layerToSpeckle(layer, projectCRS, plugin)
            # print(converted)
            if converted is not None:
                structure = tree_structure[i]
                if structure.startswith(SYMBOL):
                    structure = structure[len(SYMBOL) :]
                levels = structure.split(SYMBOL)
                while "" in levels:
                    levels.remove("")

                baseCollection = collectionsFromJson(
                    jsonTree, levels, converted, baseCollection
                )
            else:
                logToUser(
                    f"Layer '{layer.name()}' conversion failed",
                    level=2,
                    plugin=plugin.dockwidget,
                )

        return baseCollection
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return baseCollection


def layerToSpeckle(
    selectedLayer: Union["QgsVectorLayer", "QgsRasterLayer"],
    projectCRS: "QgsCoordinateReferenceSystem",
    plugin,
) -> Union[
    VectorLayer, RasterLayer
]:  # now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    try:
        # print("___layerToSpeckle")
        dataStorage = plugin.dataStorage
        dataStorage.latestActionFeaturesReport = []
        project: QgsProject = plugin.project
        layerName = selectedLayer.name()

        crs = selectedLayer.crs()

        offset_x = plugin.dataStorage.crs_offset_x
        offset_y = plugin.dataStorage.crs_offset_y
        rotation = plugin.dataStorage.crs_rotation

        units_proj = plugin.dataStorage.currentUnits
        units_layer_native = str(QgsUnitTypes.encodeUnit(crs.mapUnits()))

        units_layer = units_layer_native
        if crs.isGeographic():
            units_layer = "m"  ## specklepy.logging.exceptions.SpeckleException: SpeckleException: Could not understand what unit degrees is referring to. Please enter a valid unit (eg ['mm', 'cm', 'm', 'in', 'ft', 'yd', 'mi']).

        if "unknown" in units_layer:
            units_layer = "m"  # if no-geometry layer
        layerObjs = []

        # Convert CRS to speckle, use the projectCRS
        speckleReprojectedCrs = CRS(
            authority_id=projectCRS.authid(),
            name=str(projectCRS.description()),
            wkt=projectCRS.toWkt(),
            units=units_proj,
            offset_x=offset_x,
            offset_y=offset_y,
            rotation=rotation,
        )
        layerCRS = CRS(
            authority_id=crs.authid(),
            name=str(crs.description()),
            wkt=crs.toWkt(),
            units=units_layer,
            units_native=units_layer_native,
            offset_x=offset_x,
            offset_y=offset_y,
            rotation=rotation,
        )

        renderer = selectedLayer.renderer()
        layerRenderer = rendererToSpeckle(renderer)

        if isinstance(selectedLayer, QgsVectorLayer):
            fieldnames = []  # [str(field.name()) for field in selectedLayer.fields()]
            attributes = Base()
            for field in selectedLayer.fields():
                fieldnames.append(str(field.name()))
                corrected = validateAttributeName(str(field.name()), [])
                attribute_type = field.type()
                r"""
                all_types = [
                    (1, "bool"), 
                    (2, "int"),
                    (6, "decimal"),
                    (8, "map"),
                    (9, "int_list"),
                    (10, "string"),
                    (11, "string_list"),
                    (12, "binary"),
                    (14, "date"),
                    (15, "time"),
                    (16, "date_time") 
                ]
                for att_type in all_types:
                    if attribute_type == att_type[0]:
                        attribute_type = att_type[1]
                """
                attributes[corrected] = attribute_type

            extrusionApplied = isAppliedLayerTransformByKeywords(
                selectedLayer, ["extrude", "polygon"], [], plugin.dataStorage
            )

            if extrusionApplied is True:
                if not layerName.endswith("_as_Mesh"):
                    layerName += "_as_Mesh"

            geomType = getLayerGeomType(selectedLayer)
            features = selectedLayer.getFeatures()

            elevationLayer = getElevationLayer(plugin.dataStorage)
            projectingApplied = isAppliedLayerTransformByKeywords(
                selectedLayer,
                ["extrude", "polygon", "project", "elevation"],
                [],
                plugin.dataStorage,
            )
            if projectingApplied is True and elevationLayer is None:
                logToUser(
                    f"Elevation layer is not found. Layer '{selectedLayer.name()}' will not be projected on a 3d elevation.",
                    level=1,
                    plugin=plugin.dockwidget,
                )

            # write features
            all_errors_count = 0
            for i, f in enumerate(features):
                dataStorage.latestActionFeaturesReport.append(
                    {"feature_id": str(i + 1), "obj_type": "", "errors": ""}
                )
                b = featureToSpeckle(
                    fieldnames,
                    f,
                    geomType,
                    selectedLayer,
                    plugin.dataStorage,
                )
                # if b is None: continue

                if (
                    extrusionApplied is True
                    and isinstance(b, GisPolygonElement)
                    and isinstance(b.geometry, list)
                ):
                    # b.attributes["Speckle_ID"] = str(i+1) # not needed
                    for g in b.geometry:
                        if g is not None and g != "None":
                            # remove native polygon props, if extruded:
                            g.boundary = None
                            g.voids = None

                if isinstance(b, Base):
                    b.applicationId = generate_qgis_app_id(selectedLayer, f)

                layerObjs.append(b)
                if (
                    dataStorage.latestActionFeaturesReport[
                        len(dataStorage.latestActionFeaturesReport) - 1
                    ]["errors"]
                    != ""
                ):
                    all_errors_count += 1

            # Convert layer to speckle
            layerBase = VectorLayer(
                units=units_proj,
                applicationId=hashlib.md5(
                    selectedLayer.id().encode("utf-8")
                ).hexdigest(),
                name=layerName,
                crs=speckleReprojectedCrs,
                elements=layerObjs,
                attributes=attributes,
                geomType=geomType,
            )
            if all_errors_count == 0:
                dataStorage.latestActionReport.append(
                    {
                        "feature_id": layerName,
                        "obj_type": layerBase.speckle_type,
                        "errors": "",
                    }
                )
            else:
                dataStorage.latestActionReport.append(
                    {
                        "feature_id": layerName,
                        "obj_type": layerBase.speckle_type,
                        "errors": f"{all_errors_count} features failed",
                    }
                )
            for item in dataStorage.latestActionFeaturesReport:
                dataStorage.latestActionReport.append(item)

            layerBase.renderer = layerRenderer
            # layerBase.applicationId = selectedLayer.id()

            return layerBase

        elif isinstance(selectedLayer, QgsRasterLayer):
            # write feature attributes
            b = rasterFeatureToSpeckle(selectedLayer, projectCRS, project, plugin)
            b.applicationId = generate_qgis_raster_app_id(selectedLayer)
            if b is None:
                dataStorage.latestActionReport.append(
                    {
                        "feature_id": layerName,
                        "obj_type": "Raster Layer",
                        "errors": "Layer failed to send",
                    }
                )
                return None
            layerObjs.append(b)
            # Convert layer to speckle
            layerBase = RasterLayer(
                units=units_proj,
                applicationId=hashlib.md5(
                    selectedLayer.id().encode("utf-8")
                ).hexdigest(),
                name=layerName,
                crs=speckleReprojectedCrs,
                rasterCrs=layerCRS,
                elements=layerObjs,
            )
            dataStorage.latestActionReport.append(
                {
                    "feature_id": layerName,
                    "obj_type": layerBase.speckle_type,
                    "errors": "",
                }
            )

            layerBase.renderer = layerRenderer
            # layerBase.applicationId = selectedLayer.id()
            return layerBase
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        dataStorage.latestActionReport.append(
            {
                "feature_id": layerName,
                "obj_type": "",
                "errors": f"Layer conversion failed: {e}",
            }
        )
        return None


def layerToNative(
    layer: Union[Layer, VectorLayer, RasterLayer],
    streamBranch: str,
    nameBase: str,
    plugin,
) -> Union["QgsVectorLayer", "QgsRasterLayer", None]:
    try:
        project: QgsProject = plugin.project
        # plugin.dataStorage.currentCRS = project.crs()

        if isinstance(layer.collectionType, str) and layer.collectionType.endswith(
            "VectorLayer"
        ):
            vectorLayerToNative(layer, streamBranch, nameBase, plugin)
            return
        elif isinstance(layer.collectionType, str) and layer.collectionType.endswith(
            "RasterLayer"
        ):
            rasterLayerToNative(layer, streamBranch, nameBase, plugin)
            return
        # if collectionType exists but not defined
        elif isinstance(layer.type, str) and layer.type.endswith(
            "VectorLayer"
        ):  # older commits
            vectorLayerToNative(layer, streamBranch, nameBase, plugin)
            return
        elif isinstance(layer.type, str) and layer.type.endswith(
            "RasterLayer"
        ):  # older commits
            rasterLayerToNative(layer, streamBranch, nameBase, plugin)
            return
    except:
        try:
            if isinstance(layer.type, str) and layer.type.endswith(
                "VectorLayer"
            ):  # older commits
                vectorLayerToNative(layer, streamBranch, nameBase, plugin)
                return
            elif isinstance(layer.type, str) and layer.type.endswith(
                "RasterLayer"
            ):  # older commits
                rasterLayerToNative(layer, streamBranch, nameBase, plugin)
                return

            return
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def nonGeometryLayerToNative(
    geomList: List[Base], nameBase: str, val_id: str, streamBranch: str, plugin
):
    # print("01_____NON-GEOMETRY layer to native")

    try:
        layerName = removeSpecialCharacters(nameBase)
        newFields = getLayerAttributes(geomList)

        if plugin.dataStorage.latestHostApp.endswith("excel"):
            plugin.dockwidget.signal_6.emit(
                {
                    "plugin": plugin,
                    "layerName": layerName,
                    "val_id": val_id,
                    "streamBranch": streamBranch,
                    "newFields": newFields,
                    "geomList": geomList,
                }
            )
        else:
            plugin.dockwidget.signal_5.emit(
                {
                    "plugin": plugin,
                    "layerName": layerName,
                    "layer_id": val_id,
                    "streamBranch": streamBranch,
                    "newFields": newFields,
                    "geomList": geomList,
                }
            )

        return

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def addExcelMainThread(obj: Tuple):
    # print("___addExcelMainThread")
    try:
        finalName = ""
        plugin = obj["plugin"]
        layerName = obj["layerName"]
        streamBranch = obj["streamBranch"]
        val_id = obj["val_id"]
        newFields = obj["newFields"]
        geomList = obj["geomList"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        dataStorage = plugin.dataStorage
        project: QgsProject = plugin.dataStorage.project

        geomType = "None"
        geom_print = "Table"

        shortName = layerName.split(SYMBOL)[len(layerName.split(SYMBOL)) - 1][:50]
        try:
            layerName = layerName.split(shortName)[0] + shortName + ("_" + geom_print)
        except:
            layerName = layerName + ("_" + geom_print)
        finalName = shortName + ("_" + geom_print)

        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)

        dataStorage.latestActionLayers.append(finalName)

        ###########################################

        # get features and attributes
        fets = []
        report_features = []
        all_feature_errors_count = 0
        # print("before newFields")
        # print(newFields)
        for f in geomList:
            # print(f)
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )

            new_feat = nonGeomFeatureToNative(f, newFields, plugin.dataStorage)
            if new_feat is not None and new_feat != "":
                fets.append(new_feat)
            else:
                logToUser(
                    f"Table feature skipped due to invalid data",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                report_features[len(report_features) - 1].update(
                    {"errors": "Table feature skipped due to invalid data"}
                )
                all_feature_errors_count += 1

        if newFields is None:
            newFields = QgsFields()

        # print("04")
        vl = None
        vl = QgsVectorLayer(
            geomType + "?crs=" + "WGS84", finalName, "memory"
        )  # do something to distinguish: stream_id_latest_name
        project.addMapLayer(vl, False)
        pr = vl.dataProvider()
        vl.startEditing()

        # add Layer attribute fields
        pr.addAttributes(newFields.toList())
        vl.updateFields()

        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()

        # print("07")
        layerGroup.addLayer(vl)

        # report
        all_feature_errors_count = 0
        for item in report_features:
            if item["errors"] != "":
                all_feature_errors_count += 1

        # print("11")
        obj_type = "Vector Layer"
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{val_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{val_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )

        # print("12")
        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report
        obj_type = "Vector Layer"
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{val_id} {finalName}",
                "obj_type": obj_type,
                "errors": f"{e}",
            }
        )
        dataStorage.latestConversionTime = datetime.now()


def addNonGeometryMainThread(obj: Tuple):
    # print("___addCadMainThread")
    try:
        finalName = ""
        plugin = obj["plugin"]
        layerName = obj["layerName"]
        layer_id = obj["layer_id"]
        streamBranch = obj["streamBranch"]
        newFields = obj["newFields"]
        geomList = obj["geomList"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        project: QgsProject = plugin.dataStorage.project
        dataStorage = plugin.dataStorage

        geomType = "None"
        geom_print = "Table"

        shortName = layerName.split(SYMBOL)[len(layerName.split(SYMBOL)) - 1][:50]
        try:
            layerName = layerName.split(shortName)[0] + shortName + ("_" + geom_print)
        except:
            layerName = layerName + ("_" + geom_print)
        finalName = shortName + ("_" + geom_print)

        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)

        dataStorage.latestActionLayers.append(finalName)

        ###########################################
        dummy = None
        root = project.layerTreeRoot()
        plugin.dataStorage.all_layers = getAllLayers(root)
        if plugin.dataStorage.all_layers is not None:
            if len(plugin.dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer(
                    "Point?crs=EPSG:4326", "", "memory"
                )  # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        crs = project.crs()  # QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
        plugin.dataStorage.currentUnits = str(QgsUnitTypes.encodeUnit(crs.mapUnits()))
        if (
            plugin.dataStorage.currentUnits is None
            or plugin.dataStorage.currentUnits == "degrees"
        ):
            plugin.dataStorage.currentUnits = "m"
        # authid = trySaveCRS(crs, streamBranch)

        if crs.isGeographic is True:
            logToUser(
                f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly",
                level=1,
                func=inspect.stack()[0][3],
            )

        vl = QgsVectorLayer(
            geomType + "?crs=" + crs.authid(), finalName, "memory"
        )  # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        project.addMapLayer(vl, False)

        pr = vl.dataProvider()
        vl.startEditing()

        # create list of Features (fets) and list of Layer fields (fields)
        attrs = QgsFields()
        fets = []
        fetIds = []
        fetColors = []

        report_features = []
        all_feature_errors_count = 0
        for f in geomList[:]:
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )

            new_feat = nonGeomFeatureToNative(f, newFields, plugin.dataStorage)
            # update attrs for the next feature (if more fields were added from previous feature)

            # print("________cad feature to add")
            if new_feat is not None and new_feat != "":
                fets.append(new_feat)
                for a in newFields.toList():
                    attrs.append(a)

                pr.addAttributes(
                    newFields
                )  # add new attributes from the current object
                fetIds.append(f.id)
                fetColors = findFeatColors(fetColors, f)
            else:
                logToUser(
                    f"Table feature skipped due to invalid data",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                report_features[len(report_features) - 1].update(
                    {"errors": "Table feature skipped due to invalid data"}
                )
                all_feature_errors_count += 1

        # add Layer attribute fields
        pr.addAttributes(newFields)
        vl.updateFields()

        # pr = vl.dataProvider()
        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()

        layerGroup.addLayer(vl)

        # report
        obj_type = (
            geom_print + " Vector Layer"
            if "Mesh" not in geom_print
            else "Multipolygon Vector Layer"
        )
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )
        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report
        obj_type = geom_print + "Vector Layer"
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer_id} {finalName}",
                "obj_type": obj_type,
                "errors": f"{e}",
            }
        )
        dataStorage.latestConversionTime = datetime.now()


def geometryLayerToNative(
    layerContentList: List[Base],
    layerName: str,
    val_id: str,
    streamBranch: str,
    plugin,
    matrix=None,
):
    # print("01_____GEOMETRY layer to native")
    try:
        # print(layerContentList)
        geom_meshes = []

        geom_points = []
        geom_polylines = []

        layer_points = None
        layer_polylines = None
        # geom_meshes = []
        val = None

        # filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
        for geom in layerContentList:
            # print(geom)
            if isinstance(geom, Point):
                geom_points.append(geom)
                continue
            elif (
                isinstance(geom, Line)
                or isinstance(geom, Polyline)
                or isinstance(geom, Curve)
                or isinstance(geom, Arc)
                or isinstance(geom, Circle)
                or isinstance(geom, Ellipse)
                or isinstance(geom, Polycurve)
            ):
                geom_polylines.append(geom)
                continue
            try:
                if (
                    geom.speckle_type.endswith(".ModelCurve")
                    and geom["baseCurve"].speckle_type in GEOM_LINE_TYPES
                ):
                    geom_polylines.append(geom["baseCurve"])
                    continue
                elif geom["baseLine"].speckle_type in GEOM_LINE_TYPES:
                    geom_polylines.append(geom["baseLine"])
                    # don't skip the rest if baseLine is found
            except:
                pass  # check for the Meshes

            # ________________get list of display values for Meshes___________________________
            val = getDisplayValueList(geom)
            # print(val) # List of Meshes

            if isinstance(val, List) and len(val) > 0 and isinstance(val[0], Mesh):
                # print("__________GET ACTUAL ELEMENT BEFORE DISPLAY VALUE")
                # print(val[0]) # Mesh

                if isinstance(geom, List):
                    geom_meshes.extend(geom)
                else:
                    geom_meshes.append(geom)
            # print("__GEOM MESHES")
            # print(geom_meshes)

        if len(geom_meshes) > 0:
            bimVectorLayerToNative(
                geom_meshes, layerName, val_id, "Mesh", streamBranch, plugin, matrix
            )
        if len(geom_points) > 0:
            cadVectorLayerToNative(
                geom_points, layerName, val_id, "Points", streamBranch, plugin, matrix
            )
        if len(geom_polylines) > 0:
            cadVectorLayerToNative(
                geom_polylines,
                layerName,
                val_id,
                "Polylines",
                streamBranch,
                plugin,
                matrix,
            )

        return True

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def bimVectorLayerToNative(
    geomList: List[Base],
    layerName_old: str,
    val_id: str,
    geomType: str,
    streamBranch: str,
    plugin,
    matrix: list = None,
):
    # print("02_________BIM vector layer to native_____")
    try:
        # project: QgsProject = plugin.project
        # print(layerName_old)

        layerName = layerName_old  # [:50]
        layerName = removeSpecialCharacters(layerName)
        # print(layerName)

        # get Project CRS, use it by default for the new received layer
        vl = None
        # layerName = layerName + "_" + geomType
        # print(layerName)

        if "mesh" in geomType.lower():
            geomType = "MultiPolygonZ"

        newFields = getLayerAttributes(geomList)
        # print("___________Layer fields_____________")
        # print(newFields.toList())

        plugin.dockwidget.signal_2.emit(
            {
                "plugin": plugin,
                "geomType": geomType,
                "layerName": layerName,
                "layer_id": val_id,
                "streamBranch": streamBranch,
                "newFields": newFields,
                "geomList": geomList,
                "matrix": matrix,
            }
        )

        return
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def addBimMainThread(obj: Tuple):
    try:
        finalName = ""
        plugin = obj["plugin"]
        geomType = obj["geomType"]
        layerName = obj["layerName"]
        layer_id = obj["layer_id"]
        streamBranch = obj["streamBranch"]
        newFields = obj["newFields"]
        geomList = obj["geomList"]
        matrix = obj["matrix"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        dataStorage = plugin.dataStorage
        dataStorage.matrix = matrix
        report_features = []

        project: QgsProject = dataStorage.project

        geom_print = geomType
        if "MultiPolygonZ" in geom_print:
            geom_print = "Mesh"
        elif "LineStringZ" in geom_print:
            geom_print = "Polyline"
        elif "PointZ" in geom_print:
            geom_print = "Point"

        shortName = layerName.split(SYMBOL)[len(layerName.split(SYMBOL)) - 1][:50]
        # print(f"Final short name: {shortName}")
        try:
            layerName = (
                layerName.split(shortName)[0] + shortName + ("_as_" + geom_print)
            )
        except:
            layerName = layerName + ("_as_" + geom_print)
        finalName = shortName + ("_as_" + geom_print)
        dataStorage.latestActionLayers.append(finalName)

        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)

        # newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'
        newName_shp = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{finalName[:30]}'

        ###########################################
        dummy = None
        root = project.layerTreeRoot()
        dataStorage.all_layers = getAllLayers(root)
        if dataStorage.all_layers is not None:
            if len(dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer(
                    "Point?crs=EPSG:4326", "", "memory"
                )  # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        crs = project.crs()  # QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
        dataStorage.currentUnits = str(QgsUnitTypes.encodeUnit(crs.mapUnits()))
        if dataStorage.currentUnits is None or dataStorage.currentUnits == "degrees":
            dataStorage.currentUnits = "m"

        if crs.isGeographic is True:
            logToUser(
                f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly",
                level=1,
                func=inspect.stack()[0][3],
            )

        p = (
            os.path.expandvars(r"%LOCALAPPDATA%")
            + "\\Temp\\Speckle_QGIS_temp\\"
            + datetime.now().strftime("%Y-%m-%d_%H-%M")
        )
        findOrCreatePath(p)
        path = p
        # logToUser(f"BIM layers can only be received in an existing saved project. Layer {layerName} will be ignored", level = 1, func = inspect.stack()[0][3])

        path_bim = (
            path
            + "/Layers_Speckle/BIM_layers/"
            + streamBranch
            + "/"
            + layerName[:30]
            + "/"
        )  # arcpy.env.workspace + "\\" #

        findOrCreatePath(path_bim)
        # print(path_bim)

        shp = writeMeshToShp(geomList, path_bim + newName_shp, dataStorage)
        dataStorage.matrix = None
        if shp is None:
            return
        # print("____ meshes saved___")
        # print(shp)

        vl_shp = QgsVectorLayer(
            shp + ".shp", finalName, "ogr"
        )  # do something to distinguish: stream_id_latest_name
        vl = QgsVectorLayer(
            geomType + "?crs=" + crs.authid(), finalName, "memory"
        )  # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        project.addMapLayer(vl, False)

        pr = vl.dataProvider()
        vl.startEditing()

        # add Layer attribute fields
        pr.addAttributes(newFields)
        vl.updateFields()

        # create list of Features (fets) and list of Layer fields (fields)
        # attrs = QgsFields()
        fets = []
        fetIds = []
        fetColors = []

        report_features = []
        all_feature_errors_count = 0
        for i, f in enumerate(geomList[:]):
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )

            try:
                exist_feat: None = None
                for n, shape in enumerate(vl_shp.getFeatures()):
                    if shape["speckle_id"] == f.id:
                        exist_feat = vl_shp.getFeature(n)
                        break
                if exist_feat is None:
                    logToUser(
                        f"Feature skipped due to invalid geometry",
                        level=2,
                        func=inspect.stack()[0][3],
                    )
                    report_features[len(report_features) - 1].update(
                        {"errors": "Feature skipped due to invalid geometry"}
                    )
                    continue

                new_feat = bimFeatureToNative(
                    exist_feat, f, vl.fields(), crs, path_bim, dataStorage
                )
                if new_feat is not None and new_feat != "":
                    fetColors = findFeatColors(fetColors, f)
                    fets.append(new_feat)
                    vl.addFeature(new_feat)
                    fetIds.append(f.id)
                else:
                    logToUser(
                        f"Feature skipped due to invalid geometry",
                        level=2,
                        func=inspect.stack()[0][3],
                    )
                    report_features[len(report_features) - 1].update(
                        {"errors": "Feature skipped due to invalid geometry"}
                    )

            except Exception as e:
                logToUser(e, level=2, func=inspect.stack()[0][3])
                report_features[len(report_features) - 1].update({"errors": f"{e}"})

        vl.updateExtents()
        vl.commitChanges()

        layerGroup.addLayer(vl)

        try:
            ################################### RENDERER 3D ###########################################
            # rend3d = QgsVectorLayer3DRenderer() # https://qgis.org/pyqgis/3.16/3d/QgsVectorLayer3DRenderer.html?highlight=layer3drenderer#module-QgsVectorLayer3DRenderer

            plugin_dir = os.path.dirname(__file__)
            renderer3d = os.path.join(plugin_dir, "renderer3d.qml")
            # print(renderer3d)

            vl.loadNamedStyle(renderer3d)
            vl.triggerRepaint()
        except:
            pass

        try:
            ################################### RENDERER ###########################################
            # only set up renderer if the layer is just created
            attribute = "Speckle_ID"
            categories = []
            for i in range(len(fets)):
                material = fetColors[i]
                color = colorFromSpeckle(material)

                symbol = QgsSymbol.defaultSymbol(
                    QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType))
                )
                symbol.setColor(color)
                categories.append(
                    QgsRendererCategory(fetIds[i], symbol, fetIds[i], True)
                )
            # create empty category for all other values
            symbol2 = symbol.clone()
            symbol2.setColor(QColor.fromRgb(245, 245, 245))
            cat = QgsRendererCategory()
            cat.setSymbol(symbol2)
            cat.setLabel("Other")
            categories.append(cat)
            rendererNew = QgsCategorizedSymbolRenderer(attribute, categories)
        except Exception as e:
            print(e)

        try:
            vl.setRenderer(rendererNew)
        except:
            pass

        try:
            project.removeMapLayer(dummy)
        except:
            pass

        # report
        obj_type = (
            geom_print + " Vector Layer"
            if "Mesh" not in geom_print
            else "Multipolygon Vector Layer"
        )
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )
        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report
        obj_type = geom_print + "Vector Layer"
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer_id} {finalName}",
                "obj_type": obj_type,
                "errors": f"{e}",
            }
        )
        dataStorage.latestConversionTime = datetime.now()


def cadVectorLayerToNative(
    geomList: List[Base],
    layerName: str,
    val_id: str,
    geomType: str,
    streamBranch: str,
    plugin,
    matrix=None,
) -> "QgsVectorLayer":
    # print("___________cadVectorLayerToNative")
    try:
        project: QgsProject = plugin.project

        # get Project CRS, use it by default for the new received layer
        vl = None

        layerName = removeSpecialCharacters(layerName)

        # layerName = layerName + "_" + geomType
        # print(layerName)

        newName = (
            f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{layerName}'
        )

        if geomType == "Points":
            geomType = "PointZ"
        elif geomType == "Polylines":
            geomType = "LineStringZ"

        newFields = getLayerAttributes(geomList)
        # print(newFields.toList())
        # print(geomList)

        plugin.dockwidget.signal_3.emit(
            {
                "plugin": plugin,
                "geomType": geomType,
                "layerName": layerName,
                "layer_id": val_id,
                "streamBranch": streamBranch,
                "newFields": newFields,
                "geomList": geomList,
                "matrix": matrix,
            }
        )

        return
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def addCadMainThread(obj: Tuple):
    # print("___addCadMainThread")
    try:
        finalName = ""
        plugin = obj["plugin"]
        geomType = obj["geomType"]
        layerName = obj["layerName"]
        layer_id = obj["layer_id"]
        streamBranch = obj["streamBranch"]
        newFields = obj["newFields"]
        geomList = obj["geomList"]
        matrix = obj["matrix"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        project: QgsProject = plugin.dataStorage.project
        dataStorage = plugin.dataStorage
        dataStorage.matrix = matrix

        geom_print = geomType
        if "MultiPolygonZ" in geom_print:
            geom_print = "Mesh"
        elif "LineStringZ" in geom_print:
            geom_print = "Polyline"
        elif "PointZ" in geom_print:
            geom_print = "Point"

        shortName = layerName.split(SYMBOL)[len(layerName.split(SYMBOL)) - 1][:50]

        try:
            layerName = (
                layerName.split(shortName)[0] + shortName + ("_as_" + geom_print)
            )
        except:
            layerName = layerName + ("_as_" + geom_print)
        finalName = shortName + ("_as_" + geom_print)

        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)

        dataStorage.latestActionLayers.append(finalName)

        ###########################################
        dummy = None
        root = project.layerTreeRoot()
        plugin.dataStorage.all_layers = getAllLayers(root)
        if plugin.dataStorage.all_layers is not None:
            if len(plugin.dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer(
                    "Point?crs=EPSG:4326", "", "memory"
                )  # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        crs = project.crs()  # QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
        plugin.dataStorage.currentUnits = str(QgsUnitTypes.encodeUnit(crs.mapUnits()))
        if (
            plugin.dataStorage.currentUnits is None
            or plugin.dataStorage.currentUnits == "degrees"
        ):
            plugin.dataStorage.currentUnits = "m"
        # authid = trySaveCRS(crs, streamBranch)

        if crs.isGeographic is True:
            logToUser(
                f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly",
                level=1,
                func=inspect.stack()[0][3],
            )

        vl = QgsVectorLayer(
            geomType + "?crs=" + crs.authid(), finalName, "memory"
        )  # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        project.addMapLayer(vl, False)

        pr = vl.dataProvider()
        vl.startEditing()

        # create list of Features (fets) and list of Layer fields (fields)
        attrs = QgsFields()
        fets = []
        fetIds = []
        fetColors = []

        report_features = []
        all_feature_errors_count = 0
        for f in geomList[:]:
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )

            new_feat = cadFeatureToNative(f, newFields, plugin.dataStorage)
            # update attrs for the next feature (if more fields were added from previous feature)

            # print("________cad feature to add")
            if new_feat is not None and new_feat != "":
                fets.append(new_feat)
                for a in newFields.toList():
                    attrs.append(a)

                pr.addAttributes(
                    newFields
                )  # add new attributes from the current object
                fetIds.append(f.id)
                fetColors = findFeatColors(fetColors, f)
            else:
                logToUser(
                    f"Feature skipped due to invalid geometry",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                report_features[len(report_features) - 1].update(
                    {"errors": "Feature skipped due to invalid geometry"}
                )
                all_feature_errors_count += 1

        dataStorage.matrix = None

        # add Layer attribute fields
        pr.addAttributes(newFields)
        vl.updateFields()

        # pr = vl.dataProvider()
        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()

        layerGroup.addLayer(vl)

        ################################### RENDERER ###########################################
        # only set up renderer if the layer is just created
        attribute = "Speckle_ID"
        categories = []
        for i in range(len(fets)):
            rgb = fetColors[i]
            if rgb:
                r = (rgb & 0xFF0000) >> 16
                g = (rgb & 0xFF00) >> 8
                b = rgb & 0xFF
                color = QColor.fromRgb(r, g, b)
            else:
                color = QColor.fromRgb(0, 0, 0)

            symbol = QgsSymbol.defaultSymbol(
                QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType))
            )
            symbol.setColor(color)
            categories.append(QgsRendererCategory(fetIds[i], symbol, fetIds[i], True))
        # create empty category for all other values
        symbol2 = symbol.clone()
        symbol2.setColor(QColor.fromRgb(0, 0, 0))
        cat = QgsRendererCategory()
        cat.setSymbol(symbol2)
        cat.setLabel("Other")
        categories.append(cat)
        rendererNew = QgsCategorizedSymbolRenderer(attribute, categories)

        try:
            vl.setRenderer(rendererNew)
        except:
            pass

        try:
            ################################### RENDERER 3D ###########################################
            # rend3d = QgsVectorLayer3DRenderer() # https://qgis.org/pyqgis/3.16/3d/QgsVectorLayer3DRenderer.html?highlight=layer3drenderer#module-QgsVectorLayer3DRenderer

            plugin_dir = os.path.dirname(__file__)
            renderer3d = os.path.join(plugin_dir, "renderer3d.qml")
            # print(renderer3d)

            vl.loadNamedStyle(renderer3d)
            vl.triggerRepaint()
        except:
            pass

        try:
            project.removeMapLayer(dummy)
        except:
            pass

        # report
        obj_type = (
            geom_print + " Vector Layer"
            if "Mesh" not in geom_print
            else "Multipolygon Vector Layer"
        )
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )
        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report
        obj_type = geom_print + "Vector Layer"
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer_id} {finalName}",
                "obj_type": obj_type,
                "errors": f"{e}",
            }
        )
        dataStorage.latestConversionTime = datetime.now()


def vectorLayerToNative(
    layer: Layer or VectorLayer, streamBranch: str, nameBase: str, plugin
):
    try:
        # print("vectorLayerToNative")
        project: QgsProject = plugin.project
        layerName = removeSpecialCharacters(nameBase + SYMBOL + layer.name)
        # print(layerName)

        newName = layerName  # f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'
        # print(newName)

        # particularly if the layer comes from ArcGIS
        geomType = (
            layer.geomType
        )  # for ArcGIS: Polygon, Point, Polyline, Multipoint, MultiPatch
        if geomType == "Point":
            geomType = "Point"
        elif geomType == "Polygon":
            geomType = "MultiPolygon"
        elif geomType == "Polyline":
            geomType = "MultiLineString"
        elif geomType.lower() == "multipoint":
            geomType = "MultiPoint"
        elif geomType == "MultiPatch":
            geomType = "Polygon"

        fets = []
        # print("before newFields")

        newFields = QgsFields()
        objectEmit = {
            "plugin": plugin,
            "geomType": geomType,
            "newName": newName,
            "streamBranch": streamBranch,
            "wkt": layer.crs.wkt,
            "layer": layer,
            "newFields": newFields,
            "fets": fets,
        }
        plugin.dockwidget.signal_1.emit(objectEmit)

        return

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def addVectorMainThread(obj: Tuple):
    # print("___addVectorMainThread")
    try:
        finalName = ""
        plugin = obj["plugin"]
        geomType = obj["geomType"]
        newName = obj["newName"]
        streamBranch = obj["streamBranch"]
        wkt = obj["wkt"]
        layer = obj["layer"]
        newFields = obj["newFields"]
        fets = obj["fets"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        dataStorage = plugin.dataStorage

        plugin.dataStorage.currentUnits = layer.crs.units
        if (
            plugin.dataStorage.currentUnits is None
            or plugin.dataStorage.currentUnits == "degrees"
        ):
            plugin.dataStorage.currentUnits = "m"
        try:
            dataStorage.current_layer_crs_offset_x = layer.crs.offset_x
            dataStorage.current_layer_crs_offset_y = layer.crs.offset_y
            dataStorage.current_layer_crs_rotation = layer.crs.rotation
        except AttributeError as e:
            print(e)

        project: QgsProject = plugin.dataStorage.project

        # print(layer.name)

        shortName = newName.split(SYMBOL)[len(newName.split(SYMBOL)) - 1][:50]
        try:
            layerName = newName.split(shortName)[0] + shortName  # + ("_" + geom_print)
        except:
            layerName = newName
        finalName = shortName  # + ("_" + geom_print)
        # print(f"Final layer name: {finalName}")
        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)

        dataStorage.latestActionLayers.append(finalName)
        ###########################################

        # get features and attributes
        fets = []
        report_features = []
        all_feature_errors_count = 0
        # print("before newFields")
        newFields = getLayerAttributes(layer.elements)
        for f in layer.elements:
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )

            new_feat = featureToNative(f, newFields, plugin.dataStorage)
            if new_feat is not None and new_feat != "":
                fets.append(new_feat)
            else:
                logToUser(
                    f"'{geomType}' feature skipped due to invalid data",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                report_features[len(report_features) - 1].update(
                    {"errors": f"'{geomType}' feature skipped due to invalid data"}
                )
                all_feature_errors_count += 1

        if newFields is None:
            newFields = QgsFields()

        # add dummy layer to secure correct CRS
        # print("before dummy layer")
        dummy = None
        root = project.layerTreeRoot()
        plugin.dataStorage.all_layers = getAllLayers(root)
        if plugin.dataStorage.all_layers is not None:
            if len(plugin.dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer(
                    "Point?crs=EPSG:4326", "", "memory"
                )  # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        crs = QgsCoordinateReferenceSystem.fromWkt(wkt)
        srsid = trySaveCRS(crs, streamBranch)
        crs_new = QgsCoordinateReferenceSystem.fromSrsId(srsid)
        authid = crs_new.authid()
        # print(authid)

        #################################################
        # print("03")
        r"""
        if "polygon" in geomType.lower(): # not newName.endswith("_Mesh") and  and "Speckle_ID" in newFields.names():
            # reproject all QGIS polygon geometry to EPSG 4326 until the CRS issue is found 
            for i, f in enumerate(fets):
                #reproject
                xform = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem(4326), project)
                geometry = fets[i].geometry()
                geometry.transform(xform)
                fets[i].setGeometry(geometry)
            crs = QgsCoordinateReferenceSystem(4326)
            authid = "EPSG:4326"
        #################################################
        """

        # print("05")
        # layerGroup = tryCreateGroup(project, streamBranch)

        vl = QgsVectorLayer(
            geomType + "?crs=" + authid, finalName, "memory"
        )  # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        project.addMapLayer(vl, False)

        pr = vl.dataProvider()
        vl.startEditing()

        # add Layer attribute fields
        pr.addAttributes(newFields.toList())
        vl.updateFields()

        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()

        #################################################

        if (
            "polygon" in geomType.lower()
        ):  # and "Speckle_ID" in newFields.names(): #not newName.endswith("_Mesh") and
            p = (
                os.path.expandvars(r"%LOCALAPPDATA%")
                + "\\Temp\\Speckle_QGIS_temp\\"
                + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            )
            findOrCreatePath(p)
            file_name = os.path.join(p, newName)

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.fileEncoding = "utf-8"

            options.driverName = "GeoJSON"
            options.overrideGeometryType = QgsWkbTypes.parseType("MultiPolygonZ")
            options.forceMulti = True
            options.includeZ = True
            writer = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer=vl,
                fileName=file_name,
                transformContext=project.transformContext(),
                options=options,
            )
            del writer

            # geojson writer fix
            try:
                with open(file_name + ".geojson", "r") as file:
                    lines = file.readlines()
                    polygonType = False
                    for i, line in enumerate(lines):
                        if '"type": "Polygon"' in line:
                            polygonType = True
                            break

                    if polygonType is True:
                        new_lines = []
                        for i, line in enumerate(lines):
                            # print(line)
                            if '"type": "Polygon"' in line:
                                line = line.replace(
                                    '"type": "Polygon"', '"type": "MultiPolygonZ"'
                                )
                            if (
                                " ] ] ] " in line
                                and '"coordinates": [ [ [ [ ' not in line
                            ):
                                line = line.replace(" ] ] ] ", " ] ] ] ] ")
                            if (
                                '"coordinates": [ [ [ ' in line
                                and '"coordinates": [ [ [ [ ' not in line
                            ):
                                line = line.replace(
                                    '"coordinates": [ [ [ ', '"coordinates": [ [ [ [ '
                                )
                            new_lines.append(line)
                        with open(file_name + ".geojson", "w") as file:
                            file.writelines(new_lines)
                file.close()
            except Exception as e:
                logToUser(e, level=2, func=inspect.stack()[0][3])
                return

            if not newName.endswith("_Mesh"):
                finalName += "_Mesh"

            project.removeMapLayer(vl)
            vl = QgsVectorLayer(file_name + ".geojson", finalName, "ogr")
            vl.setCrs(crs)
            project.addMapLayer(vl, False)

        #################################################

        layerGroup.addLayer(vl)

        rendererNew = vectorRendererToNative(layer, newFields)
        if rendererNew is None:
            symbol = QgsSymbol.defaultSymbol(
                QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType))
            )
            rendererNew = QgsSingleSymbolRenderer(symbol)

        # time.sleep(3)
        try:
            vl.setRenderer(rendererNew)
        except:
            pass

        # print("08")
        try:
            ################################### RENDERER 3D ###########################################
            # rend3d = QgsVectorLayer3DRenderer() # https://qgis.org/pyqgis/3.16/3d/QgsVectorLayer3DRenderer.html?highlight=layer3drenderer#module-QgsVectorLayer3DRenderer

            plugin_dir = os.path.dirname(__file__)
            renderer3d = os.path.join(plugin_dir, "renderer3d.qml")

            vl.loadNamedStyle(renderer3d)
            vl.triggerRepaint()
        except:
            pass

        try:
            project.removeMapLayer(dummy)
        except:
            pass

        # report
        all_feature_errors_count = 0
        for item in report_features:
            if item["errors"] != "":
                all_feature_errors_count += 1

        obj_type = "Vector Layer"
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer.id} {finalName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer.id} {finalName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )

        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report
        obj_type = "Vector Layer"
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer.id} {finalName}",
                "obj_type": obj_type,
                "errors": f"{e}",
            }
        )
        dataStorage.latestConversionTime = datetime.now()


def rasterLayerToNative(layer: RasterLayer, streamBranch: str, nameBase: str, plugin):
    try:
        # project = plugin.project
        # layerName = removeSpecialCharacters(layer.name) + "_Speckle"
        layerName = removeSpecialCharacters(nameBase + SYMBOL + layer.name)

        newName = layerName  # f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'

        plugin.dockwidget.signal_4.emit(
            {
                "plugin": plugin,
                "layerName": layerName,
                "newName": newName,
                "streamBranch": streamBranch,
                "layer": layer,
            }
        )

        return
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def addRasterMainThread(obj: Tuple):
    try:
        finalName = ""
        plugin = obj["plugin"]
        layerName = obj["layerName"]
        newName = obj["newName"]
        streamBranch = obj["streamBranch"]
        layer = obj["layer"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        project: QgsProject = plugin.dataStorage.project
        dataStorage = plugin.dataStorage

        plugin.dataStorage.currentUnits = layer.crs.units
        if (
            plugin.dataStorage.currentUnits is None
            or plugin.dataStorage.currentUnits == "degrees"
        ):
            plugin.dataStorage.currentUnits = "m"

        try:
            plugin.dataStorage.current_layer_crs_offset_x = layer.crs.offset_x
            plugin.dataStorage.current_layer_crs_offset_y = layer.crs.offset_y
            plugin.dataStorage.current_layer_crs_rotation = layer.crs.rotation
        except AttributeError as e:
            print(e)

        shortName = newName.split(SYMBOL)[len(newName.split(SYMBOL)) - 1][:50]
        # print(f"Final short name: {shortName}")
        try:
            layerName = newName.split(shortName)[0] + shortName + "_Speckle"
        except:
            layerName = newName + "_Speckle"
        finalName = shortName + "_Speckle"

        # report on receive:
        dataStorage.latestActionLayers.append(finalName)
        ###########################################
        dummy = None
        root = project.layerTreeRoot()
        dataStorage.all_layers = getAllLayers(root)
        if dataStorage.all_layers is not None:
            if len(dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer(
                    "Point?crs=EPSG:4326", "", "memory"
                )  # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        ######################## testing, only for receiving layers #################
        source_folder = project.absolutePath()

        feat = layer.elements[0]

        vl = None
        crs = QgsCoordinateReferenceSystem.fromWkt(
            layer.crs.wkt
        )  # moved up, because CRS of existing layer needs to be rewritten
        # try, in case of older version "rasterCrs" will not exist
        try:
            if layer.rasterCrs.wkt is None or layer.rasterCrs.wkt == "":
                raise Exception
            crsRasterWkt = str(layer.rasterCrs.wkt)
            crsRaster = QgsCoordinateReferenceSystem.fromWkt(
                layer.rasterCrs.wkt
            )  # moved up, because CRS of existing layer needs to be rewritten
        except:
            crsRasterWkt = str(layer.crs.wkt)
            crsRaster = crs
            logToUser(
                f"Raster layer '{layer.name}' might have been sent from the older version of plugin. Try sending it again for more accurate results.",
                level=1,
                plugin=plugin.dockwidget,
            )

        srsid = trySaveCRS(crsRaster, streamBranch)
        crs_new = QgsCoordinateReferenceSystem.fromSrsId(srsid)
        authid = crs_new.authid()

        try:
            bandNames = feat.band_names
        except:
            bandNames = feat["Band names"]
        bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

        if source_folder == "":
            p = (
                os.path.expandvars(r"%LOCALAPPDATA%")
                + "\\Temp\\Speckle_QGIS_temp\\"
                + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            )
            findOrCreatePath(p)
            source_folder = p
            logToUser(
                f'Project directory not found. Raster layers will be saved to "{p}".',
                level=1,
                plugin=plugin.dockwidget,
            )

        path_fn = source_folder + "/Layers_Speckle/raster_layers/" + streamBranch + "/"
        if not os.path.exists(path_fn):
            os.makedirs(path_fn)

        fn = path_fn + layerName + ".tif"  # arcpy.env.workspace + "\\" #
        # fn = source_folder + '/' + newName.replace("/","_") + '.tif' #'_received_raster.tif'
        driver = gdal.GetDriverByName("GTiff")
        # create raster dataset
        try:
            ds = driver.Create(
                fn,
                xsize=feat.x_size,
                ysize=feat.y_size,
                bands=feat.band_count,
                eType=gdal.GDT_Float32,
            )
        except:
            ds = driver.Create(
                fn,
                xsize=feat["X pixels"],
                ysize=feat["Y pixels"],
                bands=feat["Band count"],
                eType=gdal.GDT_Float32,
            )

        # Write data to raster band
        # No data issue: https://gis.stackexchange.com/questions/389587/qgis-set-raster-no-data-value

        try:
            b_count = int(feat.band_count)  # from 2.14
        except:
            b_count = feat["Band count"]

        for i in range(b_count):
            rasterband = np.array(bandValues[i])
            try:
                rasterband = np.reshape(rasterband, (feat.y_size, feat.x_size))
            except Exception as e:
                rasterband = np.reshape(
                    rasterband, (feat["Y pixels"], feat["X pixels"])
                )

            band = ds.GetRasterBand(
                i + 1
            )  # https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html

            # get noDataVal or use default
            try:
                try:
                    noDataVal = feat.noDataValue[i]
                except:
                    noDataVal = feat["NoDataVal"][i]  # if value available
                try:
                    band.SetNoDataValue(float(noDataVal))
                except:
                    band.SetNoDataValue(noDataVal)
            except:
                pass

            band.WriteArray(rasterband)  # or "rasterband.T"

        # create GDAL transformation in format [top-left x coord, cell width, 0, top-left y coord, 0, cell height]
        pt = None
        ptSpeckle = None
        try:
            try:
                pt = QgsPoint(feat.x_origin, feat.y_origin, 0)
                ptSpeckle = Point(
                    x=feat.x_origin, y=feat.y_origin, z=0, units=feat.units
                )
            except:
                pt = QgsPoint(feat["X_min"], feat["Y_min"], 0)
                ptSpeckle = Point(
                    x=feat["X_min"], y=feat["Y_min"], z=0, units=feat.units
                )
        except:
            try:
                displayVal = feat.displayValue
            except:
                displayVal = feat["displayValue"]
            if displayVal is not None:
                if isinstance(displayVal[0], Point):
                    pt = pointToNativeWithoutTransforms(
                        displayVal[0], plugin.dataStorage
                    )
                    ptSpeckle = displayVal[0]
                if isinstance(displayVal[0], Mesh):
                    pt = QgsPoint(displayVal[0].vertices[0], displayVal[0].vertices[1])
                    ptSpeckle = Point(
                        x=displayVal[0].vertices[0],
                        y=displayVal[0].vertices[1],
                        z=displayVal[0].vertices[2],
                        units=displayVal[0].units,
                    )
        if pt is None or ptSpeckle is None:
            logToUser(
                "Raster layer doesn't have the origin point",
                level=2,
                plugin=plugin.dockwidget,
            )
            return

        try:  # if the CRS has offset props
            dataStorage.current_layer_crs_offset_x = layer.crs.offset_x
            dataStorage.current_layer_crs_offset_y = layer.crs.offset_y
            dataStorage.current_layer_crs_rotation = layer.crs.rotation

            pt = pointToNative(
                ptSpeckle, plugin.dataStorage
            )  # already transforms the offsets
            dataStorage.current_layer_crs_offset_x = (
                dataStorage.current_layer_crs_offset_y
            ) = dataStorage.current_layer_crs_rotation = None

        except AttributeError as e:
            print(e)
        xform = QgsCoordinateTransform(crs, crsRaster, project)
        pt.transform(xform)
        try:
            ds.SetGeoTransform(
                [pt.x(), feat.x_resolution, 0, pt.y(), 0, feat.y_resolution]
            )
        except:
            ds.SetGeoTransform(
                [pt.x(), feat["X resolution"], 0, pt.y(), 0, feat["Y resolution"]]
            )

        # create a spatial reference object
        ds.SetProjection(crsRasterWkt)
        # close the rater datasource by setting it equal to None
        ds = None

        raster_layer = QgsRasterLayer(fn, finalName, "gdal")
        project.addMapLayer(raster_layer, False)

        # layerGroup = tryCreateGroup(project, streamBranch)
        groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)
        layerGroup.addLayer(raster_layer)

        dataProvider = raster_layer.dataProvider()
        rendererNew = rasterRendererToNative(layer, dataProvider)

        try:
            raster_layer.setRenderer(rendererNew)
        except:
            pass

        try:
            project.removeMapLayer(dummy)
        except:
            pass

        # report on receive:
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer.id} {finalName}",
                "obj_type": "Raster Layer",
                "errors": "",
            }
        )
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report on receive:
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer.id} {finalName}",
                "obj_type": "Raster Layer",
                "errors": f"Receiving layer {layer.name} failed",
            }
        )
        dataStorage.latestConversionTime = datetime.now()
