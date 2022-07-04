from specklepy.objects.geometry import Line, Polyline, Curve, Arc, Circle
from speckle.converter.geometry.point import pointToNative, pointToSpeckle, scalePointToNative

from qgis.core import (
    QgsLineString, 
    QgsCircularString,
    QgsCircle,
)

from speckle.converter.layers.utils import get_scale_factor


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
    # first check if it's circular
    try:
        vert_list = [pt for pt in poly.vertices()] 
        leng = poly.length()
        dist = ( vert_list[0].distance(vert_list[1]) + vert_list[2].distance(vert_list[1]))
        if vert_list and leng and len(vert_list) == 3 and leng!= dist:
            return arcToSpeckle(poly)
    except:
        return polylineFromVerticesToSpeckle(poly.vertices(), False)
    return polylineFromVerticesToSpeckle(poly.vertices(), False)

def arcToSpeckle(poly: QgsCircularString):
    """Converts a QgsCircularString to Speckle"""
    arc = Arc()
    vert_list = [pt for pt in poly.vertices()] 
    arc.startPoint = pointToSpeckle(vert_list[0])
    arc.midPoint = pointToSpeckle(vert_list[1])
    arc.endPoint = pointToSpeckle(vert_list[2])

    return arc
    

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

def curveToNative(poly: Curve) -> QgsLineString:
    """Converts a Speckle Curve to QgsLineString"""
    display = poly.displayValue
    return polylineToNative(display) 

def arcToNative(poly: Arc) -> QgsCircularString:
    """Converts a Speckle Arc to QgsCircularString"""
    arc = QgsCircularString(pointToNative(poly.startPoint), pointToNative(poly.midPoint), pointToNative(poly.endPoint))
    return arc

def circleToNative(poly: Circle) -> QgsLineString:
    """Converts a Speckle Circle to QgsLineString"""
    scaleFactor = get_scale_factor(poly.units)
    circ = QgsCircle(pointToNative(poly.plane.origin), poly.radius * scaleFactor)
    circ = circ.toLineString() # QgsCircle is not supported to be added as a feature 
    return circ

