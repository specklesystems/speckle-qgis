import math

from qgis.core import (
    QgsPoint,
    QgsPointXY
)

from specklepy.objects.geometry import Point

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
    return QgsPoint(pt.x, pt.y, pt.z)

