from math import asin, cos, sin, atan
import math
import numpy as np
from specklepy.objects.geometry import Point, Line, Polyline, Curve, Arc, Circle, Polycurve, Plane, Vector
from speckle.converter.geometry.point import pointToNative, pointToSpeckle

from qgis.core import (
    QgsLineString, QgsPointXY,
    QgsCircularString, 
    QgsCircle, QgsFeature, QgsVectorLayer,
    QgsCompoundCurve, QgsVertexIterator, QgsGeometry, QgsCurvePolygon
)

from qgis._core import Qgis

from speckle.logging import logger
from speckle.converter.layers.utils import get_scale_factor
from typing import List, Tuple, Union
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
#from PyQt5.QtGui import QColor


def polylineFromVerticesToSpeckle(vertices: Union[List[Point], QgsVertexIterator], closed: bool, feature: QgsFeature, layer: QgsVectorLayer):
    """Returns a Speckle Polyline given a list of QgsPoint instances and a boolean indicating if it's closed or not."""
    if isinstance(vertices, list): 
        if len(vertices) > 0 and isinstance(vertices[0], Point):
            specklePts = vertices
        else: specklePts = [pointToSpeckle(pt, feature, layer) for pt in vertices] #breaks unexplainably
    elif isinstance(vertices, QgsVertexIterator):
        specklePts = [pointToSpeckle(pt, feature, layer) for pt in vertices]
    else: return None
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

def unknownLineToSpeckle(poly: QgsCompoundCurve, closed: bool, feature: QgsFeature, layer: QgsVectorLayer):
    
    if poly.wkbType() == 10: # CurvePolygon
        actualGeom = poly.constGet()
        actualGeom = actualGeom.segmentize()
        return polylineToSpeckle(actualGeom, feature, layer)

        parts = poly.asGeometryCollection()
        pts = []
        for p in parts:
            if isinstance(p, QgsCompoundCurve):
                p = compoudCurveToSpeckle(p, feature, layer)
                if p is not None: pts.extend(p.as_points()) 
            elif isinstance(p, QgsCircularString):
                p = arcToSpeckle(poly, feature, layer)
                if p is not None: pts.extend(speckleArcCircleToPoints(p)) 
            else:
                try: p = polylineFromVerticesToSpeckle(pts.vertices(), True, feature, layer)
                except: p = None
                if p is not None: pts.extend(p.as_points()) 
        return polylineFromVerticesToSpeckle(pts, True, feature, layer)

    elif isinstance(poly, QgsCompoundCurve): return compoudCurveToSpeckle(poly, feature, layer)
    elif isinstance(poly, QgsCircularString): return arcToSpeckle(poly, feature, layer)
    #elif isinstance(poly, QgsCurvePolygon): 
    #    poly = poly.segmentize() 
    #    return polylineFromVerticesToSpeckle(poly.vertices(), feature, layer)
    else: return polylineFromVerticesToSpeckle(poly.vertices(), closed, feature, layer) # initial method

def compoudCurveToSpeckle(poly: QgsCompoundCurve, feature: QgsFeature, layer: QgsVectorLayer):

    poly = poly.curveToLine()
    return polylineToSpeckle(poly, feature, layer)

    polycurve = Polycurve()
    polycurve.segments = []
    polycurve.closed = False

    if "CircularString" in str(poly): 
        all_pts = [pt for pt in poly.vertices()]
        num_segm = (len(all_pts) - 1) / 2
        startPt = all_pts[0]
        if num_segm.is_integer(): # make sure the logic is [startPt, mid-end, mid-end etc]
            for i in range(int(num_segm)):
                segm = QgsCircularString(startPt, all_pts[1:][i*2], all_pts[1:][i*2 + 1] )
                newArc = arcToSpeckle(segm, feature, layer)
                if newArc is not None: polycurve.segments.append(newArc)
                #vert.extend(speckleArcCircleToPoints(newArc))
                startPt = all_pts[1:][i*2 + 1]
    #polycurve = polylineFromVerticesToSpeckle(vert, False, feature, layer)
    
    col = featureColorfromNativeRenderer(feature, layer)
    polycurve['displayStyle'] = {}
    polycurve['displayStyle']['color'] = col

    return polycurve 

def polylineToSpeckle(poly: Union[QgsLineString, QgsCircularString], feature: QgsFeature, layer: QgsVectorLayer):
    """Converts a QgsLineString to Speckle"""
    try: closed = poly.isClosed()
    except: closed = False

    polyline = polylineFromVerticesToSpeckle(poly.vertices(), closed, feature, layer)
    # colors already set in the previous function 
    #col = featureColorfromNativeRenderer(QgsFeature(), QgsVectorLayer())
    #polyline['displayStyle'] = {}
    #polyline['displayStyle']['color'] = col
    return polyline

def arcToSpeckle(poly: QgsCircularString, feature: QgsFeature, layer: QgsVectorLayer):
    """Converts a QgsCircularString to Speckle"""
    #print("____Arc to Speckle ___")
    arc = Arc()
    vert_list = [pt for pt in poly.vertices()] 
    arc.startPoint = pointToSpeckle(vert_list[0], feature, layer)
    arc.midPoint = pointToSpeckle(vert_list[1], feature, layer)
    arc.endPoint = pointToSpeckle(vert_list[2], feature, layer)
    center, radius = getArcCenter(arc.startPoint, arc.midPoint, arc.endPoint)
    arc.plane = Plane()#.from_list(Point(), Vector(Point(0, 0, 1)), Vector(Point(0,1,0)), Vector(Point(-1,0,0)))
    arc.plane.origin = Point.from_list(center)
    #arc.plane.xdir=Vector.from_list([1,0,0])
    #arc.plane.ydir=Vector.from_list([0,1,0])
    arc.plane.normal = getArcNormal(arc, arc.midPoint)
    arc.plane.origin.units = "m" 
    arc.radius = radius
    arc.angleRadians, startAngle, endAngle = getArcRadianAngle(arc)
    if arc.angleRadians == 0: return None
    col = featureColorfromNativeRenderer(feature, layer)
    arc['displayStyle'] = {}
    arc['displayStyle']['color'] = col
    return arc
    
def getArcCenter(p1: Point, p2: Point, p3: Point) -> Tuple[Point, float]:
    p1 = np.array(p1.to_list())
    p2 = np.array(p2.to_list())
    p3 = np.array(p3.to_list())
    a = np.linalg.norm(p3 - p2)
    b = np.linalg.norm(p3 - p1)
    c = np.linalg.norm(p2 - p1)
    s = (a + b + c) / 2
    radius = a*b*c / 4 / np.sqrt(s * (s - a) * (s - b) * (s - c))
    b1 = a*a * (b*b + c*c - a*a)
    b2 = b*b * (a*a + c*c - b*b)
    b3 = c*c * (a*a + b*b - c*c)
    center = np.column_stack((p1, p2, p3)).dot(np.hstack((b1, b2, b3)))
    center /= b1 + b2 + b3
    center = center.tolist()
    return center, radius

def lineToNative(line: Line) -> QgsLineString:
    """Converts a Speckle Line to QgsLineString"""
    line = QgsLineString(pointToNative(line.start), pointToNative(line.end))
    return line

def polylineToNative(poly: Polyline) -> QgsLineString:
    """Converts a Speckle Polyline to QgsLineString"""
    # this function can be called from Multipolyline, hence extra check if the type of segment in not Polyline
    if isinstance(poly, Polycurve): 
        return polycurveToNative(poly)
    if isinstance(poly, Arc) or isinstance(poly, Circle): 
        return circleToNative(poly)

    if poly.closed is False: 
        polyline = QgsLineString([pointToNative(pt) for pt in poly.as_points()])
        #return polyline
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
    circle = QgsCircle(pointToNative(poly.plane.origin), poly.radius * scaleFactor)
    circle = circle.toLineString() # QgsCircle is not supported to be added as a feature, workaround (not working): https://gis.stackexchange.com/questions/411892/typeerror-qgsgeometry-frompolygonxy-argument-1-has-unexpected-type-qgspolyg 
    return circle

def polycurveToNative(poly: Polycurve) -> QgsLineString:
    points = []
    curve = QgsLineString()
    singleSegm = 0
    try:
        if len(poly.segments) == 0: return None
        elif len(poly.segments) == 1: singleSegm = 1

        for segm in poly.segments: # Line, Polyline, Curve, Arc, Circle
            if isinstance(segm,Line):  
                converted = lineToNative(segm) # QgsLineString
                if singleSegm == 1: return converted
            elif isinstance(segm,Polyline):  
                converted = polylineToNative(segm) # QgsLineString
                if singleSegm == 1: return converted
            elif isinstance(segm,Curve):  
                converted = curveToNative(segm) # QgsLineString
                if singleSegm == 1: return converted
            elif isinstance(segm,Circle):  
                pts = [pointToNative(pt) for pt in speckleArcCircleToPoints(segm)]
                converted = QgsLineString(pts) # QgsLineString
                if singleSegm == 1: return circleToNative(segm)
                #converted = circleToNative(segm) # QgsLineString
            elif isinstance(segm,Arc):  
                pts = [pointToNative(pt) for pt in speckleArcCircleToPoints(segm)]
                converted =  QgsLineString(pts) # QgsLineString
                if singleSegm == 1: return arcToNative(segm)
            else: # either return a part of the curve, of skip this segment and try next
                logger.logToUser(f"Part of the polycurve cannot be converted", Qgis.Warning)
                curve = QgsLineString(points)
                return curve
            if converted is not None: 
                for pt in converted.vertices():
                    if len(points)>0 and pt.x()== points[len(points)-1].x() and pt.y()== points[len(points)-1].y() and pt.z()== points[len(points)-1].z(): pass
                    else: points.append(pt)
            else:
                logger.logToUser(f"Part of the polycurve cannot be converted", Qgis.Warning)
                curve = QgsLineString(points)
                return curve
    except: curve = None

    curve = QgsLineString(points)
    return curve

r'''
def arcToQgisPoints(poly: Arc):
    points = []
    angle1 = atan( abs ((poly.startPoint.y - poly.plane.origin.y) / (poly.startPoint.x - poly.plane.origin.x) )) # between 0 and pi/2
    if poly.plane.origin.x < poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = 2*math.pi - angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = math.pi + angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y < poly.startPoint.y: angle1 = math.pi - angle1

    angle2 = atan( abs ((poly.endPoint.y - poly.plane.origin.y) / (poly.endPoint.x - poly.plane.origin.x) )) # between 0 and pi/2
    if poly.plane.origin.x < poly.endPoint.x and poly.plane.origin.y > poly.endPoint.y: angle2 = 2*math.pi - angle2
    if poly.plane.origin.x > poly.endPoint.x and poly.plane.origin.y > poly.endPoint.y: angle2 = math.pi + angle2
    if poly.plane.origin.x > poly.endPoint.x and poly.plane.origin.y < poly.endPoint.y: angle2 = math.pi - angle2

    try: interval = (poly.endAngle - poly.startAngle)
    except: interval = (angle2-angle1)
    try: 
        pointsNum = math.floor( abs(interval)) * 12
        if pointsNum <4: pointsNum = 4
        points.append(pointToNative(poly.startPoint))

        for i in range(1, pointsNum + 1): 
            k = i/pointsNum # to reset values from 1/10 to 1
            if poly.plane.normal.z == 0: normal = 1
            else: normal = poly.plane.normal.z
            angle = angle1 + k * interval * normal
            pt = Point( x = poly.plane.origin.x + poly.radius * cos(angle), y = poly.plane.origin.y + poly.radius * sin(angle), z = 0) 
            pt.units = poly.startPoint.units 
            points.append(pointToNative(pt))
        points.append(pointToNative(poly.endPoint))

        curve = QgsLineString(points)
        return curve
    except: return None
'''


def specklePolycurveToPoints(poly: Polycurve) -> List[Point]:
    #print("_____Speckle Polycurve to points____")
    points = []
    for segm in poly.segments:
        #print(segm)
        if isinstance(segm, Arc) or isinstance(segm, Circle): # or isinstance(segm, Curve):
            #print("Arc or Curve")
            pts: List[Point] = speckleArcCircleToPoints(segm) 
        elif isinstance(segm, Line): 
            #print("Line")
            pts: List[Point] = [segm.start, segm.end]
        elif isinstance(segm, Polyline): 
            #print("Polyline")
            pts: List[Point] = segm.as_points()

        points.extend(pts)
    return points


def speckleArcCircleToPoints(poly: Union[Arc, Circle]) -> List[Point]: 
    #print("__Arc or Circle to Points___")
    points = []
    #print(poly.plane) 
    #print(poly.plane.normal) 
    if poly.plane is None or poly.plane.normal.z == 0: normal = 1 
    else: normal = poly.plane.normal.z 

    if isinstance(poly, Circle):
        interval = 2*math.pi
        range_start = 0
        angle1 = 0

    else: # if Arc
        points.append(poly.startPoint)
        range_start = 0 

        #angle1, angle2 = getArcAngles(poly)
        interval, angle1, angle2 = getArcRadianAngle(poly)

        if (angle1 > angle2 and normal == -1) or (angle2 > angle1 and normal == 1): pass
        if angle1 > angle2 and normal == 1: interval = abs( (2*math.pi-angle1) + angle2)
        if angle2 > angle1 and normal == -1: interval = abs( (2*math.pi-angle2) + angle1)

    pointsNum = math.floor( abs(interval)) * 12
    if pointsNum <4: pointsNum = 4

    for i in range(range_start, pointsNum + 1): 
        k = i/pointsNum # to reset values from 1/10 to 1
        angle = angle1 + k * interval * normal

        pt = Point( x = poly.plane.origin.x + poly.radius * cos(angle), y = poly.plane.origin.y + poly.radius * sin(angle), z = 0) 
        
        pt.units = poly.plane.origin.units 
        points.append(pt)

    if isinstance(poly, Arc): points.append(poly.endPoint)
    return points

def getArcRadianAngle(arc: Arc) -> List[float]:

    interval = None
    normal = arc.plane.normal.z 
    angle1, angle2 = getArcAngles(arc)
    if angle1 is None or angle2 is  None: return None
    interval = abs(angle2 - angle1)

    if (angle1 > angle2 and normal == -1) or (angle2 > angle1 and normal == 1): pass
    if angle1 > angle2 and normal == 1: interval = abs( (2*math.pi-angle1) + angle2)
    if angle2 > angle1 and normal == -1: interval = abs( (2*math.pi-angle2) + angle1)
    return interval, angle1, angle2

def getArcAngles(poly: Arc) -> Tuple[float]: 
    
    if poly.startPoint.x == poly.plane.origin.x: angle1 = math.pi/2
    else: angle1 = atan( abs ((poly.startPoint.y - poly.plane.origin.y) / (poly.startPoint.x - poly.plane.origin.x) )) # between 0 and pi/2
    
    if poly.plane.origin.x < poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = 2*math.pi - angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = math.pi + angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y < poly.startPoint.y: angle1 = math.pi - angle1

    if poly.endPoint.x == poly.plane.origin.x: angle2 = math.pi/2
    else: angle2 = atan( abs ((poly.endPoint.y - poly.plane.origin.y) / (poly.endPoint.x - poly.plane.origin.x) )) # between 0 and pi/2

    if poly.plane.origin.x < poly.endPoint.x and poly.plane.origin.y > poly.endPoint.y: angle2 = 2*math.pi - angle2
    if poly.plane.origin.x > poly.endPoint.x and poly.plane.origin.y > poly.endPoint.y: angle2 = math.pi + angle2
    if poly.plane.origin.x > poly.endPoint.x and poly.plane.origin.y < poly.endPoint.y: angle2 = math.pi - angle2

    return angle1, angle2 


def getArcNormal(poly: Arc, midPt: Point): 
    #print("____getArcNormal___")
    angle1, angle2 = getArcAngles(poly)

    if midPt.x == poly.plane.origin.x: angle = math.pi/2
    else: angle = atan( abs ((midPt.y - poly.plane.origin.y) / (midPt.x - poly.plane.origin.x) )) # between 0 and pi/2
    
    if poly.plane.origin.x < midPt.x and poly.plane.origin.y > midPt.y: angle = 2*math.pi - angle
    if poly.plane.origin.x > midPt.x and poly.plane.origin.y > midPt.y: angle = math.pi + angle
    if poly.plane.origin.x > midPt.x and poly.plane.origin.y < midPt.y: angle = math.pi - angle

    normal = Vector()
    normal.x = normal.y = 0

    if angle1 > angle > angle2: normal.z = -1  
    if angle1 > angle2 > angle: normal.z = 1  

    if angle2 > angle1 > angle: normal.z = -1  
    if angle > angle1 > angle2: normal.z = 1  

    if angle2 > angle > angle1: normal.z = 1  
    if angle > angle2 > angle1: normal.z = -1  
    
    #print(angle1)
    #print(angle)
    #print(angle2)
    #print(normal)

    return normal

