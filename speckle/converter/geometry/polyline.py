from specklepy.objects.geometry import Line, Polyline
from speckle.converter.geometry.point import pointToNative, pointToSpeckle

from qgis.core import (
    QgsLineString,
)


def polylineFromVerticesToSpeckle(vertices, closed):
    """Returns a Speckle Polyline given a list of QgsPoint instances and a boolean indicating if it's closed or not."""
    specklePts = [pointToSpeckle(pt) for pt in vertices] #breaks unexplainably
    #specklePts = []
    #for pt in vertices:
    #    p = pointToSpeckle(pt)
    #    specklePts.append(p)
    # TODO: Replace with `from_points` function when fix is pushed.
    polyline = Polyline()
    polyline.value = []
    polyline.closed = closed
    polyline.units = specklePts[0].units
    for i, point in enumerate(specklePts):
        if closed and i == len(specklePts) - 1:
            continue
        polyline.value.extend([point.x, point.y, point.z])
    #print(polyline)
    #print(polyline.value)
    return polyline


def polylineToSpeckle(poly: QgsLineString):
    """Converts a QgsLineString to Speckle"""
    return polylineFromVerticesToSpeckle(poly.vertices(), False)


def lineToNative(line: Line) -> QgsLineString:
    """Converts a Speckle Line to QgsLineString"""

    return QgsLineString(pointToNative(line.start), pointToNative(line.end))


def polylineToNative(poly: Polyline) -> QgsLineString:
    """Converts a Speckle Polyline to QgsLineString"""
    if poly.closed is False: 
        return QgsLineString([pointToNative(pt) for pt in poly.as_points()])
    else:
        ptList = poly.as_points()
        ptList.append(poly.as_points()[0])
        return QgsLineString([pointToNative(pt) for pt in ptList])

def curveToNative(poly: Polyline) -> QgsLineString:
    """Converts a Speckle Polyline to QgsLineString"""

    return QgsLineString([pointToNative(pt) for pt in poly.as_points()])
