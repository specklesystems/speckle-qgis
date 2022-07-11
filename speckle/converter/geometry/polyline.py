from math import asin, cos, sin, atan
import math
from specklepy.objects.geometry import Point, Line, Polyline, Curve, Arc, Circle, Polycurve
from speckle.converter.geometry.point import pointToNative, pointToSpeckle, scalePointToNative

from qgis.core import (
    QgsLineString, 
    QgsCircularString, QgsMultiLineString, 
    QgsCircle, QgsFeature, QgsVectorLayer
)

from qgis._core import Qgis

from speckle.logging import logger
from speckle.converter.layers.utils import get_scale_factor
from typing import List, Union
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
#from PyQt5.QtGui import QColor


def polylineFromVerticesToSpeckle(vertices, closed, feature: QgsFeature, layer: QgsVectorLayer):
    """Returns a Speckle Polyline given a list of QgsPoint instances and a boolean indicating if it's closed or not."""
    specklePts = [pointToSpeckle(pt, feature, layer) for pt in vertices] #breaks unexplainably
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
    
    col = featureColorfromNativeRenderer(feature, layer)
    polyline['displayStyle'] = {}
    polyline['displayStyle']['color'] = col
    return polyline

def polylineToSpeckle(poly: Union[QgsLineString, QgsCircularString], feature: QgsFeature, layer: QgsVectorLayer):
    """Converts a QgsLineString to Speckle"""
    try: closed = poly.isClosed()
    except: closed = False

    polyline = polylineFromVerticesToSpeckle(poly.vertices(), closed, feature, layer)
    #col = featureColorfromNativeRenderer(QgsFeature(), QgsVectorLayer())
    #polyline['displayStyle'] = {}
    #polyline['displayStyle']['color'] = col
    return polyline

def arcToSpeckle(poly: QgsCircularString, feature: QgsFeature, layer: QgsVectorLayer):
    """Converts a QgsCircularString to Speckle"""
    arc = Arc()
    vert_list = [pt for pt in poly.vertices()] 
    arc.startPoint = pointToSpeckle(vert_list[0], feature, layer)
    arc.midPoint = pointToSpeckle(vert_list[1], feature, layer)
    arc.endPoint = pointToSpeckle(vert_list[2], feature, layer)
    
    col = featureColorfromNativeRenderer(feature, layer)
    arc['displayStyle'] = {}
    arc['displayStyle']['color'] = col
    return arc
    


def lineToNative(line: Line) -> QgsLineString:
    """Converts a Speckle Line to QgsLineString"""
    line = QgsLineString(pointToNative(line.start), pointToNative(line.end))
    return line

def polylineToNative(poly: Polyline) -> QgsLineString:
    """Converts a Speckle Polyline to QgsLineString"""
    if poly.closed is False: 
        polyline = QgsLineString([pointToNative(pt) for pt in poly.as_points()])
        return polyline
    else:
        ptList = poly.as_points()
        ptList.append(poly.as_points()[0])
        polyline = QgsLineString([pointToNative(pt) for pt in ptList])
        return polyline

def curveToNative(poly: Curve) -> QgsLineString:
    """Converts a Speckle Curve to QgsLineString"""
    display = poly.displayValue
    curve = polylineToNative(display) 
    return curve

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

def polycurveToNative(poly: Polycurve) -> QgsLineString:
    points = []
    curve = QgsMultiLineString()
    try:
        for segm in poly.segments: # Line, Polyline, Curve, Arc, Circle
            if isinstance(segm,Line):  converted = lineToNative(segm) # QgsLineString
            elif isinstance(segm,Polyline):  converted = polylineToNative(segm) # QgsLineString
            elif isinstance(segm,Curve):  converted = curveToNative(segm) # QgsLineString
            elif isinstance(segm,Circle):  converted = circleToNative(segm) # QgsLineString
            elif isinstance(segm,Arc):  converted = arcToQgisPoints(segm) # QgsLineString
            else: # either return a part of the curve, of skip this segment and try next
                logger.logToUser(f"Part of the polycurve cannot be converted", Qgis.Warning)
                return curve
            if converted is not None: curve.addGeometry(converted)
            else:
                logger.logToUser(f"Part of the polycurve cannot be converted", Qgis.Warning)
                return curve
    except: curve = None
    return curve

def arcToQgisPoints(poly: Arc):
    points = []
    angle1 = atan( abs ((poly.startPoint.y - poly.plane.origin.y) / (poly.startPoint.x - poly.plane.origin.x) )) # between 0 and pi/2
    if poly.plane.origin.x < poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = 2*math.pi - angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = math.pi + angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y < poly.startPoint.y: angle1 = math.pi - angle1

    try: 
        pointsNum = math.floor( abs(poly.endAngle - poly.startAngle)) * 12
        if pointsNum <4: pointsNum = 4
        points.append(pointToNative(poly.startPoint))

        for i in range(1, pointsNum + 1): 
            k = i/pointsNum # to reset values from 1/10 to 1
            angle = angle1 + k * ( poly.endAngle - poly.startAngle) * poly.plane.normal.z
            pt = Point( x = poly.plane.origin.x + poly.radius * cos(angle), y = poly.plane.origin.y + poly.radius * sin(angle), z = 0) 
            points.append(pointToNative(pt))
        points.append(pointToNative(poly.endPoint))

        curve = QgsLineString(points)
        return curve
    except: return None
