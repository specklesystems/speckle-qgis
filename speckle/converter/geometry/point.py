import math

from qgis.core import (
    QgsPoint,
    QgsPointXY
)

from specklepy.objects.geometry import Point
from speckle.converter.layers.utils import get_scale_factor

def pointToSpeckle(pt: QgsPoint or QgsPointXY):
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
    return specklePoint


def pointToNative(pt: Point) -> QgsPoint:
    """Converts a Speckle Point to QgsPoint"""
    pt = scalePointToNative(pt, pt.units)
    return QgsPoint(pt.x, pt.y, pt.z)

def scalePointToNative(pt: Point, units: str) -> Point:
    """Scale point coordinates to meters"""
    scaleFactor = get_scale_factor(units)
    pt.x = pt.x * scaleFactor
    pt.y = pt.y * scaleFactor
    pt.z = 0 if math.isnan(pt.z) else pt.z * scaleFactor
    return pt
