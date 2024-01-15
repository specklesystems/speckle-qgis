import inspect
import math
import numpy as np

from qgis.core import QgsPoint, QgsPointXY, QgsFeature, QgsVectorLayer

from specklepy.objects.geometry import Point
from speckle.converter.layers.utils import get_scale_factor
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.utils.panel_logging import logToUser


def applyOffsetsRotation(x: float, y: float, dataStorage):  # on Send
    try:
        offset_x = dataStorage.crs_offset_x
        offset_y = dataStorage.crs_offset_y
        rotation = dataStorage.crs_rotation
        if offset_x is not None and isinstance(offset_x, float):
            x -= offset_x
        if offset_y is not None and isinstance(offset_y, float):
            y -= offset_y
        if (
            rotation is not None
            and isinstance(rotation, float)
            and -360 < rotation < 360
        ):
            a = rotation * math.pi / 180
            x2 = x * math.cos(a) + y * math.sin(a)
            y2 = -x * math.sin(a) + y * math.cos(a)
            x = x2
            y = y2
        return x, y
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None


def pointToSpeckle(
    pt: QgsPoint or QgsPointXY, feature: QgsFeature, layer: QgsVectorLayer, dataStorage
):
    """Converts a QgsPoint to Speckle"""
    try:
        if isinstance(pt, QgsPointXY):
            pt = QgsPoint(pt)
        # when unset, z() returns "nan"
        x = pt.x()
        y = pt.y()
        z = 0 if math.isnan(pt.z()) else pt.z()
        specklePoint = Point()
        specklePoint.x = x
        specklePoint.y = y
        specklePoint.z = z
        specklePoint.units = "m"

        specklePoint.x, specklePoint.y = applyOffsetsRotation(x, y, dataStorage)

        col = featureColorfromNativeRenderer(feature, layer)
        specklePoint["displayStyle"] = {}
        specklePoint["displayStyle"]["color"] = col
        return specklePoint
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def transformSpecklePt(pt_original: Point, dataStorage) -> Point:  # on Receive
    offset_x = dataStorage.crs_offset_x
    offset_y = dataStorage.crs_offset_y
    rotation = dataStorage.crs_rotation

    pt = Point(
        x=pt_original.x, y=pt_original.y, z=pt_original.z, units=pt_original.units
    )

    gisLayer = None
    try:
        gisLayer = dataStorage.latestHostApp.lower().endswith("gis")
        # print(gisLayer)
        applyTransforms = False if (gisLayer and gisLayer is True) else True
    except Exception as e:
        print(e)
        applyTransforms = True

    # for non-GIS layers
    if applyTransforms is True:
        # print("transform non-gis layer")
        if (
            rotation is not None
            and isinstance(rotation, float)
            and -360 < rotation < 360
        ):
            a = rotation * math.pi / 180
            x2 = pt.x
            y2 = pt.y

            # if a > 0: # turn counterclockwise on receive
            x2 = pt.x * math.cos(a) - pt.y * math.sin(a)
            y2 = pt.x * math.sin(a) + pt.y * math.cos(a)
            # elif a < 0: # turn clockwise on receive
            #    x2 =  pt.x*math.cos(a) + pt.y*math.sin(a)
            #    y2 = -1*pt.x*math.sin(a) + pt.y*math.cos(a)

            pt.x = x2
            pt.y = y2
        if (
            offset_x is not None
            and isinstance(offset_x, float)
            and offset_y is not None
            and isinstance(offset_y, float)
        ):
            pt.x += offset_x
            pt.y += offset_y

    # for GIS layers
    if gisLayer is True:
        # print("transform GIS layer")
        try:
            offset_x = dataStorage.current_layer_crs_offset_x
            offset_y = dataStorage.current_layer_crs_offset_y
            rotation = dataStorage.current_layer_crs_rotation

            if (
                rotation is not None
                and isinstance(rotation, float)
                and -360 < rotation < 360
            ):
                a = rotation * math.pi / 180
                x2 = pt.x
                y2 = pt.y

                # if a > 0: # turn counterclockwise on receive
                x2 = pt.x * math.cos(a) - pt.y * math.sin(a)
                y2 = pt.x * math.sin(a) + pt.y * math.cos(a)
                # elif a < 0: # turn clockwise on receive
                #    x2 =  pt.x*math.cos(a) + pt.y*math.sin(a)
                #    y2 = -1*pt.x*math.sin(a) + pt.y*math.cos(a)

                pt.x = x2
                pt.y = y2
            if (
                offset_x is not None
                and isinstance(offset_x, float)
                and offset_y is not None
                and isinstance(offset_y, float)
            ):
                pt.x += offset_x
                pt.y += offset_y
        except Exception as e:
            print(e)

    # print(pt)
    return pt


def pointToNativeWithoutTransforms(pt: Point, dataStorage) -> QgsPoint:
    """Converts a Speckle Point to QgsPoint"""
    try:
        pt = scalePointToNative(pt, pt.units, dataStorage)
        pt = applyTransformMatrix(pt, dataStorage)
        newPt = pt  # transformSpecklePt(pt, dataStorage)

        return QgsPoint(newPt.x, newPt.y, newPt.z)
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def pointToNative(pt: Point, dataStorage) -> QgsPoint:
    """Converts a Speckle Point to QgsPoint"""
    try:
        pt = scalePointToNative(pt, pt.units, dataStorage)
        pt = applyTransformMatrix(pt, dataStorage)
        newPt = transformSpecklePt(pt, dataStorage)

        return QgsPoint(newPt.x, newPt.y, newPt.z)
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def applyTransformMatrix(pt: Point, dataStorage):
    try:
        if dataStorage.matrix is not None:
            # print(f"__PT: {(pt.x, pt.y, pt.z)}")
            # print(dataStorage.matrix)
            b = np.matrix([pt.x, pt.y, pt.z, 1])
            res = b * dataStorage.matrix
            # print(res)
            x, y, z = res.item(0), res.item(1), res.item(2)
            # print(f"__PT: {(x, y, z)}")
            return Point(x=x, y=y, z=z, units=pt.units)
    except Exception as e:
        print(e)
    return pt


def scalePointToNative(point: Point, units: str, dataStorage) -> Point:
    """Scale point coordinates to meters"""
    try:
        scaleFactor = get_scale_factor(units, dataStorage)  # to meters
        pt = Point(units="m")
        pt.x = point.x * scaleFactor
        pt.y = point.y * scaleFactor
        pt.z = 0 if math.isnan(point.z) else point.z * scaleFactor
        return pt
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None
