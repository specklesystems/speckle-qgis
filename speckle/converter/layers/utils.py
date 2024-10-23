import copy
import hashlib
import inspect
import time
from plugin_utils.helpers import SYMBOL
from typing import Any, Dict, List, Tuple, Union
from specklepy.objects import Base
from specklepy.objects.other import Collection
from specklepy.objects.geometry import (
    Point,
    Line,
    Polyline,
    Circle,
    Arc,
    Polycurve,
    Mesh,
)

from speckle.converter.geometry import transform


try:
    from qgis._core import (
        Qgis,
        QgsPointXY,
        QgsProject,
        QgsCoordinateReferenceSystem,
        QgsLayerTreeLayer,
        QgsVectorLayer,
        QgsRasterLayer,
        QgsWkbTypes,
        QgsFeature,
        QgsField,
        QgsFields,
        QgsLayerTreeGroup,
    )
    from PyQt5.QtGui import QColor
    from PyQt5.QtCore import QVariant, QDate, QDateTime
    from osgeo import gdal, ogr, osr
except ModuleNotFoundError:
    pass


import math
import numpy as np


from speckle.utils.panel_logging import logToUser

ATTRS_REMOVE = [
    "speckleTyp",
    "speckle_id",
    "geometry",
    "applicationId",
    "bbox",
    "displayStyle",
    "id",
    "renderMaterial",
    "displayMesh",
    "displayValue",
]


def generate_qgis_app_id(
    layer: Union["QgsRasterLayer", "QgsVectorLayer"],
    f: "QgsFeature",
):
    """Generate unique ID for Vector feature."""
    try:

        try:
            geoms = str(f.geometry())
        except Exception as e:
            geoms = ""

        if layer is not None:
            layer_id = layer.id()
            return f"{layer_id}_{f.id() + 1}"
            layer_geom_type = str(layer.wkbType())
            fieldnames = [str(field.name()) for field in layer.fields()]
            props = [str(f[prop]) for prop in fieldnames]
        else:
            return f"no_layer_{f.id()}"
            layer_id = ""
            layer_geom_type = ""
            fieldnames = []
            props = [attr for attr in f.attributes()]

        id_data: str = layer_id + layer_geom_type + str(fieldnames) + str(props) + geoms
        return hashlib.md5(id_data.encode("utf-8")).hexdigest()

    except Exception as e:
        logToUser(
            f"Application ID not generated for feature in layer {layer.name() if layer is not None else ''}: {e}",
            level=1,
        )
        return ""


def generate_qgis_raster_app_id(rasterLayer):
    """Generate unique ID for Raster layer."""
    try:
        id_data = str(get_raster_stats(rasterLayer))
        file_ds = gdal.Open(rasterLayer.source(), gdal.GA_ReadOnly)
        for i in range(rasterLayer.bandCount()):
            band = file_ds.GetRasterBand(i + 1)
            id_data += str(band.ReadAsArray())
        return hashlib.md5(id_data.encode("utf-8")).hexdigest()

    except Exception as e:
        logToUser(
            f"Application ID not generated for layer {rasterLayer.name()}: {e}",
            level=1,
        )
        return ""


def getLayerGeomType(
    layer: "QgsVectorLayer",
) -> str:  # https://qgis.org/pyqgis/3.0/core/Wkb/QgsWkbTypes.html
    # print(layer.wkbType())
    try:
        if layer.wkbType() == 1:
            return "Point"
        elif layer.wkbType() == 2001:
            return "PointM"
        elif layer.wkbType() == 1001:
            return "PointZ"
        elif layer.wkbType() == 3001:
            return "PointZM"

        elif layer.wkbType() == 2:
            return "LineString"
        elif layer.wkbType() == 2002:
            return "LineStringM"
        elif layer.wkbType() == 1002:
            return "LineStringZ"
        elif layer.wkbType() == 3002:
            return "LineStringZM"

        elif layer.wkbType() == 3:
            return "Polygon"
        elif layer.wkbType() == 2003:
            return "PolygonM"
        elif layer.wkbType() == 1003:
            return "PolygonZ"
        elif layer.wkbType() == 3003:
            return "PolygonZM"

        elif layer.wkbType() == 4:
            return "MultiPoint"
        elif layer.wkbType() == 2004:
            return "MultiPointM"
        elif layer.wkbType() == 1004:
            return "MultiPointZ"
        elif layer.wkbType() == 3004:
            return "MultiPointZM"

        elif layer.wkbType() == 5:
            return "MultiLineString"
        elif layer.wkbType() == 2005:
            return "MultiLineStringM"
        elif layer.wkbType() == 1005:
            return "MultiLineStringZ"
        elif layer.wkbType() == 3005:
            return "MultiLineStringZM"

        elif layer.wkbType() == 6:
            return "MultiPolygon"
        elif layer.wkbType() == 2006:
            return "MultiPolygonM"
        elif layer.wkbType() == 1006:
            return "MultiPolygonZ"
        elif layer.wkbType() == 3006:
            return "MultiPolygonZM"

        elif layer.wkbType() == 7:
            return "GeometryCollection"
        elif layer.wkbType() == 2007:
            return "GeometryCollectionM"
        elif layer.wkbType() == 1007:
            return "GeometryCollectionZ"
        elif layer.wkbType() == 3007:
            return "GeometryCollectionZM"

        elif layer.wkbType() == 8:
            return "LineString"  # "CircularString"
        elif layer.wkbType() == 2008:
            return "LineStringM"  # ""CircularStringM"
        elif layer.wkbType() == 1008:
            return "LineStringZ"  # ""CircularStringZ"
        elif layer.wkbType() == 3008:
            return "LineStringZM"  # ""CircularStringZM"

        elif layer.wkbType() == 9:
            return "CompoundCurve"
        elif layer.wkbType() == 2009:
            return "CompoundCurveM"
        elif layer.wkbType() == 1009:
            return "CompoundCurveZ"
        elif layer.wkbType() == 3009:
            return "CompoundCurveZM"

        elif layer.wkbType() == 10:
            return "Polygon"  # "CurvePolygon"
        elif layer.wkbType() == 2010:
            return "PolygonM"  # "CurvePolygonM"
        elif layer.wkbType() == 1010:
            return "PolygonZ"  # "CurvePolygonZ"
        elif layer.wkbType() == 3010:
            return "PolygonZM"  # "CurvePolygonZM"

        elif layer.wkbType() == 11:
            return "MultiCurve"
        elif layer.wkbType() == 2011:
            return "MultiCurveM"
        elif layer.wkbType() == 1011:
            return "MultiCurveZ"
        elif layer.wkbType() == 3011:
            return "MultiCurveZM"

        elif layer.wkbType() == 12:
            return "MultiSurface"
        elif layer.wkbType() == 2012:
            return "MultiSurfaceM"
        elif layer.wkbType() == 1012:
            return "MultiSurfaceZ"
        elif layer.wkbType() == 3012:
            return "MultiSurfaceZM"

        elif layer.wkbType() == 17:
            return "Triangle"
        elif layer.wkbType() == 2017:
            return "TriangleM"
        elif layer.wkbType() == 1017:
            return "TriangleZ"
        elif layer.wkbType() == 3017:
            return "TriangleZM"

        return "None"
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        raise TypeError(
            f"Geometry type of layer '{layer.name()}' is not identified: {e}"
        )


def getVariantFromValue(value: Any) -> Union["QVariant.Type", None]:
    try:
        # TODO add Base object
        pairs = {
            str: QVariant.String,  # 10
            float: QVariant.Double,  # 6
            int: QVariant.LongLong,  # 4
            bool: QVariant.Bool,
            QDate: QVariant.Date,  # 14
            QDateTime: QVariant.DateTime,  # 16
        }
        t = type(value)
        res = None
        try:
            res = pairs[t]
        except:
            pass

        if isinstance(value, str) and "PyQt5.QtCore.QDate(" in value:
            res = QVariant.Date  # 14
        elif isinstance(value, str) and "PyQt5.QtCore.QDateTime(" in value:
            res = QVariant.DateTime  # 16

        return res
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def colorFromSpeckle(rgb):
    try:
        color = QColor.fromRgb(245, 245, 245)
        if isinstance(rgb, int):
            r = (rgb & 0xFF0000) >> 16
            g = (rgb & 0xFF00) >> 8
            b = rgb & 0xFF
            color = QColor.fromRgb(r, g, b)
        return color
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return QColor.fromRgb(245, 245, 245)


def getLayerAttributes(features: List[Base]) -> "QgsFields":
    try:
        # print("___________getLayerAttributes")
        fields = QgsFields()
        all_props = []
        for feature in features:
            # print(feature)
            if feature is None:
                continue
            # get object properties to add as attributes
            try:
                dynamicProps = (
                    feature.attributes.get_dynamic_member_names()
                )  # for 2.14 onwards
            except:
                dynamicProps = feature.get_dynamic_member_names()
            # attrsToRemove = ['speckleTyp','geometry','applicationId','bbox','displayStyle', 'id', 'renderMaterial', 'geometry', 'displayMesh', 'displayValue']
            for att in ATTRS_REMOVE:
                try:
                    dynamicProps.remove(att)
                except:
                    pass

            dynamicProps.sort()
            # print(dynamicProps)

            # add field names and variands
            for name in dynamicProps:
                try:
                    value = feature.attributes[name]
                except:
                    value = feature[name]

                variant = getVariantFromValue(value)
                if not variant:
                    variant = None  # LongLong #4

                # go thought the dictionary object
                if value and isinstance(
                    value, list
                ):  # and isinstance(value[0], dict) :
                    for i, val_item in enumerate(value):
                        newF, newVals = traverseDict(
                            {}, {}, name + "_" + str(i), val_item, 1
                        )

                        for i, (k, v) in enumerate(newF.items()):
                            if k not in all_props:
                                all_props.append(k)
                            if k not in fields.names():
                                fields.append(QgsField(k, v))  # fields.update({k: v})
                            else:  # check if the field was empty previously:
                                index = fields.indexFromName(k)
                                oldVariant = fields.field(index).type()
                                # replace if new one is NOT Float (too large integers)
                                # if oldVariant != "FLOAT" and v == "FLOAT":
                                #    fields.append(QgsField(k, v)) # fields.update({k: v})
                                # replace if new one is NOT LongLong or IS String
                                if (
                                    oldVariant != QVariant.String
                                    and v == QVariant.String
                                ):
                                    fields.append(
                                        QgsField(k, v)
                                    )  # fields.update({k: v})

                # add a field if not existing yet
                else:  # if str, Base, etc
                    # print(f"atrribute '{value}' is a Base/str/etc")
                    newF, newVals = traverseDict({}, {}, name, value, 1)
                    # print(newF)
                    # print(newVals)

                    for i, (k, v) in enumerate(newF.items()):
                        if k not in all_props:
                            all_props.append(k)
                        # print(all_props)

                        if k not in fields.names():
                            fields.append(
                                QgsField(k, v)
                            )  # fields.update({k: v}) #if variant is known
                        else:  # check if the field was empty previously:
                            index = fields.indexFromName(k)
                            oldVariant = fields.field(index).type()
                            # replace if new one is NOT Float (too large integers)
                            # if oldVariant != "FLOAT" and v == "FLOAT":
                            #    fields.append(QgsField(k, v)) # fields.update({k: v})
                            # replace if new one is NOT LongLong or IS String
                            if oldVariant != QVariant.String and v == QVariant.String:
                                fields.append(QgsField(k, v))  # fields.update({k: v})

        # replace all empty ones with String
        all_props.append("Speckle_ID")
        for name in all_props:
            all_field_names = fields.names()
            if name not in all_field_names:
                fields.append(QgsField(name, QVariant.String))

        return fields
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def traverseDict(
    newF: dict[Any, Any],
    newVals: dict[Any, Any],
    nam: str,
    val: Any,
    iteration: int = 0,
):
    try:
        # print("___traverseDict")
        if iteration <= 1 and isinstance(val, dict):
            for i, (k, v) in enumerate(val.items()):
                newF, newVals = traverseDict(
                    newF, newVals, nam + "_" + k, v, iteration + 1
                )
        elif iteration <= 1 and isinstance(val, Base):
            # print(f"a Base: '{val}'")
            # time.sleep(0.3)
            dynamicProps = val.get_dynamic_member_names()
            if "Revit" in val.speckle_type:
                dynamicProps = val.get_member_names()
            # print(dynamicProps)
            for att in ATTRS_REMOVE:
                try:
                    dynamicProps.remove(att)
                except:
                    pass
            dynamicProps.sort()
            # print(dynamicProps)

            item_dict = {}
            for prop in dynamicProps:
                try:
                    item_dict.update({prop: val[prop]})
                except:
                    try:
                        # if prop == "id": item_dict.update({prop: val.id})
                        if prop == "speckle_type":
                            item_dict.update({prop: val.speckle_type})
                    except:
                        pass
            # print(newF)
            # print(item_dict)
            for i, (k, v) in enumerate(item_dict.items()):
                newF, newVals = traverseDict(
                    newF, newVals, nam + "_" + k, v, iteration + 1
                )
            # print(f"___FINAL newF: '{newF}'")
        else:
            var = getVariantFromValue(val)
            if var is None:
                var = QVariant.String  # LongLong #4
                val = str(val)
            # else:
            newF.update({nam: var})
            newVals.update({nam: val})
        return newF, newVals
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def validateAttributeName(name: str, fieldnames: List[str]) -> str:
    try:
        new_list = [x for x in fieldnames if x != name]

        corrected = name.replace("/", "_").replace(".", "_")
        if corrected == "id":
            corrected = "applicationId"

        for i, x in enumerate(corrected):
            if corrected[0] != "_" and corrected not in new_list:
                break
            else:
                corrected = corrected[1:]

        if len(corrected) <= 1 and len(name) > 1:
            corrected = "0" + name  # if the loop removed the property name completely

        return corrected
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def trySaveCRS(crs, streamBranch: str = ""):
    try:
        authid = crs.authid()
        wkt = crs.toWkt()
        if authid == "":
            crs_id = crs.saveAsUserCrs("SpeckleCRS_" + streamBranch)
            return crs_id
        else:
            return crs.srsid()
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def reprojectPt(x, y, wkt_in, proj_in, wkt_out, proj_out):
    srs_in = osr.SpatialReference()
    srs_in.ImportFromWkt(wkt_in)
    srs_out = osr.SpatialReference()
    srs_out.ImportFromWkt(wkt_out)
    if proj_in != proj_out:
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y)
        point.AssignSpatialReference(srs_in)
        point.TransformTo(srs_out)
        newX = point.GetX()
        newY = point.GetY()
    else:
        newX = x
        newY = y
    return newX, newY


def getClosestIndex(x):
    if x < 0:
        val = math.ceil(x)
        return val
    else:
        val = int(x)
        return val


def getArrayIndicesFromXY(settings, x, y):
    """Get cell x&y incices (and remainders) on a given layer, from absolute XY coordinates."""
    resX, resY, minX, minY, sizeX, sizeY, wkt, proj = settings
    index2 = (x - minX) / resX
    index1 = (y - minY) / resY
    if index2 == -0.0:
        index2 = 0
    if index1 == -0.0:
        index1 = 0

    if not 0 <= getClosestIndex(index2) < sizeX:  # try deviating +- 1
        index2 = (x - minX) / resX - 1
        if not 0 <= getClosestIndex(index2) < sizeX:
            index2 = (x - minX) / resX + 1
    if not 0 <= getClosestIndex(index1) < sizeY:
        index1 = (y - minY) / resY - 1
        if not 0 <= getClosestIndex(index1) < sizeY:
            index1 = (y - minY) / resY + 1

    ind1 = getClosestIndex(index1)
    ind2 = getClosestIndex(index2)

    if not 0 <= ind2 < sizeX or not 0 <= ind1 < sizeY:
        return None, None, None, None
    else:
        remainder1 = index1 - ind1
        remainder2 = index2 - ind2
        return ind1, ind2, remainder1, remainder2


def getXYofArrayPoint(rasterResXY, minX, minY, indexX, indexY):
    x = minX + rasterResXY[0] * indexX
    y = minY + rasterResXY[1] * indexY
    return x, y


def isAppliedLayerTransformByKeywords(
    layer, keywordsYes: List[str], keywordsNo: List[str], dataStorage
):
    correctTransform = False
    if dataStorage.savedTransforms is not None:
        all_saved_transforms = [
            item.split("  ->  ")[1] for item in dataStorage.savedTransforms
        ]
        all_saved_transform_layers = [
            item.split("  ->  ")[0].split(" ('")[0]
            for item in dataStorage.savedTransforms
        ]

        for item in dataStorage.savedTransforms:
            layer_name_recorded = item.split("  ->  ")[0].split(" ('")[0]
            transform_name_recorded = item.split("  ->  ")[1]

            if layer_name_recorded == layer.name():
                if len(keywordsYes) > 0 or len(keywordsNo) > 0:
                    correctTransform = True
                for word in keywordsYes:
                    if word in transform_name_recorded.lower():
                        pass
                    else:
                        correctTransform = False
                        break
                for word in keywordsNo:
                    if word not in transform_name_recorded.lower():
                        pass
                    else:
                        correctTransform = False
                        break

            # if correctTransform is True and layer_name_recorded == layer.name():
            #    # find a layer for meshing, if mesh transformation exists
            #    for l in dataStorage.all_layers:
            #        if layer_name_recorded == l.name():
            #            return l
    return correctTransform


def getElevationLayer(dataStorage):
    elevationLayer = dataStorage.elevationLayer
    if elevationLayer is None:
        return None
    try:
        # check if layer was not deleted
        name = elevationLayer.name()
        return elevationLayer
    except:
        return None


def get_raster_stats(rasterLayer):
    try:
        file_ds = gdal.Open(rasterLayer.source(), gdal.GA_ReadOnly)
        xres, yres = (
            float(file_ds.GetGeoTransform()[1]),
            float(file_ds.GetGeoTransform()[5]),
        )
        originX, originY = (file_ds.GetGeoTransform()[0], file_ds.GetGeoTransform()[3])
        band = file_ds.GetRasterBand(1)
        rasterWkt = file_ds.GetProjection()
        rasterProj = (
            QgsCoordinateReferenceSystem.fromWkt(rasterWkt)
            .toProj()
            .replace(" +type=crs", "")
        )
        sizeX, sizeY = (band.ReadAsArray().shape[1], band.ReadAsArray().shape[0])

        return xres, yres, originX, originY, sizeX, sizeY, rasterWkt, rasterProj
    except Exception as e:
        return None, None, None, None, None, None, None, None


def getRasterArrays(elevationLayer):
    const = float(-1 * math.pow(10, 30))

    try:
        elevationSource = gdal.Open(elevationLayer.source(), gdal.GA_ReadOnly)

        all_arrays = []
        all_mins = []
        all_maxs = []
        all_na = []

        for b in range(elevationLayer.bandCount()):
            band = elevationSource.GetRasterBand(b + 1)
            val_NA = band.GetNoDataValue()

            array_band = band.ReadAsArray()
            fakeArray = np.where(
                (array_band < const)
                | (array_band > -1 * const)
                | (array_band == val_NA)
                | (np.isinf(array_band)),
                np.nan,
                array_band,
            )

            val_Min = np.nanmin(fakeArray)
            val_Max = np.nanmax(fakeArray)

            all_arrays.append(fakeArray)
            all_mins.append(val_Min)
            all_maxs.append(val_Max)
            all_na.append(val_NA)

        return (all_arrays, all_mins, all_maxs, all_na)
    except:
        return (None, None, None, None)


def moveVertically(poly, height):
    if isinstance(poly, Polycurve):
        for segm in poly.segments:
            segm = moveVerticallySegment(segm, height)
    else:
        poly = moveVerticallySegment(poly, height)

    return poly


def moveVerticallySegment(poly, height):
    if isinstance(poly, Arc) or isinstance(poly, Circle):  # or isinstance(segm, Curve):
        if poly.plane is not None:
            poly.plane.normal.z += height
            poly.plane.origin.z += height
        poly.startPoint.z += height
        try:
            poly.endPoint.z += height
        except:
            pass
    elif isinstance(poly, Line):
        poly.start.z += height
        poly.end.z += height
    elif isinstance(poly, Polyline):
        for i in range(len(poly.value)):
            if (i + 1) % 3 == 0:
                poly.value[i] += float(height)

    return poly


def tryCreateGroupTree(root, fullGroupName, plugin=None):
    # CREATE A GROUP "received blabla" with sublayers
    # print("_________CREATE GROUP TREE: " + fullGroupName)

    # receive_layer_tree: dict = plugin.receive_layer_tree
    receive_layer_list = fullGroupName.split(SYMBOL)
    path_list = []
    for x in receive_layer_list:
        if len(x) > 0:
            path_list.append(x)
    group_to_create_name = path_list[0]

    layerGroup = QgsLayerTreeGroup(group_to_create_name)
    if root.findGroup(group_to_create_name) is not None:
        layerGroup = root.findGroup(group_to_create_name)  # -> QgsLayerTreeNode
    else:
        layerGroup = root.insertGroup(
            0, group_to_create_name
        )  # root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    path_list.pop(0)

    if len(path_list) > 0:
        layerGroup = tryCreateGroupTree(layerGroup, SYMBOL.join(path_list), plugin)

    return layerGroup


def tryCreateGroup(project, groupName, plugin=None):
    # CREATE A GROUP "received blabla" with sublayers
    # print("_________CREATE GROUP: " + groupName)
    newGroupName = f"{groupName}"
    root = project.layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName)  # -> QgsLayerTreeNode
    else:
        layerGroup = root.insertGroup(0, newGroupName)  # root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    if plugin is not None:
        plugin.current_layer_group = layerGroup

    return layerGroup


def findUpdateJsonItemPath(tree: Dict, full_path_str: str):
    try:
        new_tree = copy.deepcopy(tree)

        path_list_original = full_path_str.split(SYMBOL)
        path_list = []
        for x in path_list_original:
            if len(x) > 0:
                path_list.append(x)
        attr_found = False

        for i, item in enumerate(new_tree.items()):
            attr, val_dict = item

            if attr == path_list[0]:
                attr_found = True
                path_list.pop(0)
                if len(path_list) > 0:  # if the path is not finished:
                    all_names = val_dict.keys()
                    if (
                        len(path_list) == 1 and path_list[0] in all_names
                    ):  # already in a tree
                        return new_tree
                    else:
                        branch = findUpdateJsonItemPath(
                            val_dict, SYMBOL.join(path_list)
                        )
                        new_tree.update({attr: branch})

        if (
            attr_found is False and len(path_list) > 0
        ):  # create a new branch at the top level
            if len(path_list) == 1:
                new_tree.update({path_list[0]: {}})
                return new_tree
            else:
                branch = findUpdateJsonItemPath(
                    {path_list[0]: {}}, SYMBOL.join(path_list)
                )
                new_tree.update(branch)
        return new_tree
    except Exception as e:
        print(e)
        return tree


def collectionsFromJson(
    jsonObj: dict, levels: list, layerConverted, baseCollection: Collection
):
    if jsonObj == {} or len(levels) == 0:
        # print("RETURN")
        baseCollection.elements.append(layerConverted)
        return baseCollection

    lastLevel = baseCollection
    for i, l in enumerate(levels):
        sub_collection_found = 0
        for item in lastLevel.elements:
            # print("___ITEM")
            # print(l)
            if item.name == l:
                # print("___ITEM FOUND")
                # print(l)
                lastLevel = item
                sub_collection_found = 1
                break
        if sub_collection_found == 0:
            # print("___ SUB COLLECTION NOT FOUND")
            subCollection = Collection(units="m", name=l, elements=[])
            lastLevel.elements.append(subCollection)
            lastLevel = lastLevel.elements[
                len(lastLevel.elements) - 1
            ]  # reassign last element

        if i == len(levels) - 1:  # if last level
            lastLevel.elements.append(layerConverted)

    return baseCollection


def getDisplayValueList(geom: Any) -> List:
    try:
        # print("___getDisplayValueList")
        val = []
        # get list of display values for Meshes
        if isinstance(geom, Mesh):
            val = [geom]
        elif isinstance(geom, List) and len(geom) > 0:
            if isinstance(geom[0], Mesh):
                val = geom
            else:
                print("not an individual geometry")
        else:
            try:
                val = geom.displayValue  # list
            except Exception as e:
                print(e)
                try:
                    val = geom["@displayValue"]  # list
                except Exception as e:
                    print(e)
                    try:
                        val = geom.displayMesh
                    except:
                        pass
        return val
    except Exception as e:
        print(e)
        return []
