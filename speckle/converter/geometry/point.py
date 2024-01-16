import inspect
import math
from typing import Union
import numpy as np

try:
    from qgis.core import QgsPoint, QgsPointXY, QgsFeature, QgsVectorLayer
except ModuleNotFoundError:
    pass

from specklepy.objects.geometry import Point
from speckle.converter.geometry.utils import (
    apply_pt_offsets_rotation_on_send,
    transform_speckle_pt_on_receive,
    apply_pt_transform_matrix,
)
from speckle.converter.utils import get_scale_factor
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.utils.panel_logging import logToUser


def pointToSpeckle(
    pt: "QgsPoint" or "QgsPointXY", feature: "QgsFeature", layer: "QgsVectorLayer", dataStorage
):
    """Converts a QgsPoint to Speckle"""
    try:
        if isinstance(pt, QgsPointXY):
            pt = QgsPoint(pt)

        x = pt.x()
        y = pt.y()
        z = 0 if math.isnan(pt.z()) else pt.z()  # when unset, z() returns "nan"
        specklePoint = Point()
        specklePoint.x = x
        specklePoint.y = y
        specklePoint.z = z
        specklePoint.units = "m"

        specklePoint.x, specklePoint.y = apply_pt_offsets_rotation_on_send(
            x, y, dataStorage
        )

        col = featureColorfromNativeRenderer(feature, layer)
        specklePoint["displayStyle"] = {}
        specklePoint["displayStyle"]["color"] = col
        return specklePoint
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def pointToNative(pt: Point, dataStorage) -> "QgsPoint":
    """Converts a Speckle Point to QgsPoint"""
    try:
        new_pt = scalePointToNative(pt, pt.units, dataStorage)
        new_pt = apply_pt_transform_matrix(new_pt, dataStorage)
        newPt = transform_speckle_pt_on_receive(new_pt, dataStorage)

        return QgsPoint(newPt.x, newPt.y, newPt.z)
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def pointToNativeWithoutTransforms(pt: Point, dataStorage) -> Union["QgsPoint", None]:
    """Converts a Speckle Point to QgsPoint"""
    try:
        new_pt = scalePointToNative(pt, pt.units, dataStorage)
        new_pt = apply_pt_transform_matrix(new_pt, dataStorage)

        return QgsPoint(new_pt.x, new_pt.y, new_pt.z)
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def scalePointToNative(
    point: Point, units: Union[str, None], dataStorage
) -> Union[Point, None]:
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
