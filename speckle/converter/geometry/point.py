import math

from qgis.core import (
    QgsPoint,
    QgsPointXY, QgsFeature, QgsVectorLayer
)

from specklepy.objects.geometry import Point
from speckle.converter.layers.utils import get_scale_factor
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
#from PyQt5.QtGui import QColor

def pointToSpeckle(pt: QgsPoint or QgsPointXY, feature: QgsFeature, layer: QgsVectorLayer):
    """Converts a QgsPoint to Speckle"""
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

    col = featureColorfromNativeRenderer(feature, layer)
    specklePoint['displayStyle'] = {}
    specklePoint['displayStyle']['color'] = col
    return specklePoint


def pointToNative(pt: Point) -> QgsPoint:
    """Converts a Speckle Point to QgsPoint"""
    pt = scalePointToNative(pt, pt.units)
    return QgsPoint(pt.x, pt.y, pt.z)

def scalePointToNative(point: Point, units: str) -> Point:
    """Scale point coordinates to meters"""
    scaleFactor = get_scale_factor(units)
    pt = Point(units = "m")
    pt.x = point.x * scaleFactor
    pt.y = point.y * scaleFactor
    pt.z = 0 if math.isnan(point.z) else point.z * scaleFactor
    return pt
