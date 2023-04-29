import inspect
from math import asin, cos, sin, atan
import math
import numpy as np
from specklepy.objects.geometry import Point, Line, Polyline, Curve, Arc, Circle, Ellipse, Polycurve, Plane, Vector
from speckle.converter.geometry.point import pointToNative, pointToSpeckle

from qgis.core import (
    QgsLineString, QgsPointXY, QgsCompoundCurve, QgsCurve, 
    QgsCircularString, QgsPoint,
    QgsCircle, QgsFeature, QgsVectorLayer,
    QgsCompoundCurve, QgsVertexIterator, QgsGeometry, QgsCurvePolygon, QgsEllipse,
    QgsWkbTypes
)

from qgis._core import Qgis
from speckle.converter.geometry.utils import addCorrectUnits, getArcNormal, getArcRadianAngle, speckleArcCircleToPoints

from speckle.logging import logger
from speckle.converter.layers.utils import get_scale_factor, get_scale_factor_to_meter
from typing import List, Tuple, Union
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from ui.logger import logToUser
#from PyQt5.QtGui import QColor


def polylineFromVerticesToSpeckle(vertices: Union[List[Point], QgsVertexIterator], closed: bool, feature: QgsFeature, layer: QgsVectorLayer, dataStorage = None):
    """Returns a Speckle Polyline given a list of QgsPoint instances and a boolean indicating if it's closed or not."""
    try:
        if isinstance(vertices, list): 
            if len(vertices) > 0 and isinstance(vertices[0], Point):
                specklePts = vertices
            else: specklePts = [pointToSpeckle(pt, feature, layer) for pt in vertices] #breaks unexplainably
        elif isinstance(vertices, QgsVertexIterator):
            specklePts: list[Point] = [pointToSpeckle(pt, feature, layer) for pt in vertices]
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
            if closed and i == len(specklePts)-1 and specklePts[0].x==specklePts[len(specklePts)-1].x and specklePts[0].y==specklePts[len(specklePts)-1].y and specklePts[0].z==specklePts[len(specklePts)-1].z:
                continue
            polyline.value.extend([point.x, point.y, point.z])
        
        col = featureColorfromNativeRenderer(feature, layer)
        polyline['displayStyle'] = {}
        polyline['displayStyle']['color'] = col
        return polyline
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

def unknownLineToSpeckle(poly: QgsCompoundCurve, closed: bool, feature: QgsFeature, layer: QgsVectorLayer, dataStorage = None) -> Union[Polyline, Arc, Line, Polycurve, None]:
    try:
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

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
def compoudCurveToSpeckle(poly: QgsCompoundCurve, feature: QgsFeature, layer: QgsVectorLayer, dataStorage = None):
    try:
        try: poly = poly.constGet()
        except: pass
        #poly = poly.curveToLine()
        #return polylineToSpeckle(poly, feature, layer)

        polycurve = Polycurve(units = "m")
        polycurve.segments = []
        polycurve.closed = False
        
        parts = str(poly).split("),")
        pts = []
        pt_len = 0
        closed_segm = False
        segments_added = 0

        for p in parts:
            if "CircularString" in p:

                all_pts = []
                #[pt for pt in p.vertices()]
                for k in range( len(p.split(',')) ): 
                    all_pts.append( poly.childPoint(pt_len - segments_added + k) ) 

                num_curve_segm = (len(all_pts) - 1) / 2
                startPt = all_pts[0]
                if num_curve_segm.is_integer(): # make sure the logic is [startPt, mid-end, mid-end etc]
                    for i in range(int(num_curve_segm)):
                        # TODO: check if arc 
                        segm = QgsCircularString(startPt, all_pts[1:][i*2], all_pts[1:][i*2 + 1] )
                        newArc = arcToSpeckle(segm, feature, layer)
                        if newArc is not None: 
                            polycurve.segments.append(newArc)
                        #vert.extend(speckleArcCircleToPoints(newArc))
                        startPt = all_pts[1:][i*2 + 1]
                        pt_len += 3 
                        segments_added += 1
                #pt1 = poly.childPoint(pt_len)
                #pt2 = poly.childPoint(pt_len+1)
                #pt3 = poly.childPoint(pt_len+2)
                #circString = QgsCircularString(QgsPoint(pt1.x(), pt1.y(), pt1.z()), QgsPoint(pt2.x(), pt2.y(), pt2.z()), QgsPoint(pt3.x(), pt3.y(), pt3.z()))
                #p = arcToSpeckle(circString, feature, layer)
                #if p is not None: pts.extend([poly.childPoint(pt_len), poly.childPoint(pt_len+1), poly.childPoint(pt_len+2)]) 
                #t_len += 3 # outdated: because the 3rd point will be reused as n-point of the curve
            else: 
                segment_pts = p.replace(" ","").replace("(","").replace(")","").split(",")
                len_segment_pts = len(segment_pts)
                if len_segment_pts == 2: 
                    st = pointToSpeckle(poly.childPoint(pt_len - segments_added ), feature, layer)
                    en = pointToSpeckle(poly.childPoint(pt_len - segments_added + 1), feature, layer)
                    #print(poly.childPoint(pt_len+1))
                    #print(type(poly.childPoint(pt_len+1).x()))
                    if "EMPTY" in str(poly.childPoint(pt_len - segments_added + 1)): 
                        en = pointToSpeckle(poly.childPoint(0), feature, layer)
                    newLine = Line(units = "m", start = st, end = en)
                    polycurve.segments.append(newLine)
                    #print(p)
                    pt_len += 2 # because the end point will be reused as n-point of the curve
                    segments_added += 1
                else: #polyline
                    actual_segment_pts = []
                    for k in range(len(segment_pts)):
                        ptt = poly.childPoint(pt_len - segments_added + k)
                        actual_segment_pts.append(pointToSpeckle(ptt, feature, layer))

                    if actual_segment_pts[0].x == actual_segment_pts[len(actual_segment_pts)-1].x and actual_segment_pts[0].y == actual_segment_pts[len(actual_segment_pts)-1].y and actual_segment_pts[0].z == actual_segment_pts[len(actual_segment_pts)-1].z : 
                        closed_segm = True # last point will not be included (if closed) when Polyline is created 
                        newPolyline = polylineFromVerticesToSpeckle(actual_segment_pts, closed_segm, feature, layer)
                        polycurve.segments.append(newPolyline)
                        break
                    
                    newPolyline = polylineFromVerticesToSpeckle(actual_segment_pts, closed_segm, feature, layer)
                    polycurve.segments.append(newPolyline)
                    pt_len += len(actual_segment_pts)
                    segments_added += 1

            #polycurve.segments.append(p)

        #if closed_segm: polycurve = p # take the last segment only
        
        col = featureColorfromNativeRenderer(feature, layer)
        polycurve['displayStyle'] = {}
        polycurve['displayStyle']['color'] = col

        return polycurve
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

    #if "CircularString" in str(poly): 
    #polycurve = polylineFromVerticesToSpeckle(vert, False, feature, layer)
    

    return polycurve 

def anyLineToSpeckle(geom, feature, layer, dataStorage):
    
    #geomSingleType = QgsWkbTypes.isSingleType(geom.wkbType())
    #geomType = geom.type()
    type = geom.wkbType()
    #units = dataStorage.currentUnits

    if type == QgsWkbTypes.CircularString or type == QgsWkbTypes.CircularStringZ or type == QgsWkbTypes.CircularStringM or type == QgsWkbTypes.CircularStringZM: #Type (not GeometryType)
        result = arcToSpeckle(geom, feature, layer, dataStorage)
        result = addCorrectUnits(result, dataStorage)
        return result
    
    elif type == QgsWkbTypes.CompoundCurve or type == QgsWkbTypes.CompoundCurveZ or type == QgsWkbTypes.CompoundCurveM or type == QgsWkbTypes.CompoundCurveZM: # 9, 1009, 2009, 3009
        if "CircularString" in str(geom): 
            all_pts = [pt for pt in geom.vertices()]
            if len(all_pts) == 3: 
                result = arcToSpeckle(geom, feature, layer, dataStorage)
                return result
            else: 
                result = compoudCurveToSpeckle(geom, feature, layer, dataStorage)
                return result
        else: return None
    else: 
        result = polylineToSpeckle(geom, feature, layer, dataStorage)
        return result

def polylineToSpeckle(poly: Union[QgsLineString, QgsCircularString], feature: QgsFeature, layer: QgsVectorLayer, dataStorage = None):
    """Converts a QgsLineString to Speckle"""
    try:
        try: closed = poly.isClosed()
        except: closed = False

        polyline = polylineFromVerticesToSpeckle(poly.vertices(), closed, feature, layer)
        # colors already set in the previous function 
        #col = featureColorfromNativeRenderer(QgsFeature(), QgsVectorLayer())
        #polyline['displayStyle'] = {}
        #polyline['displayStyle']['color'] = col
        return polyline
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

def arcToSpeckle(poly: QgsCircularString, feature: QgsFeature, layer: QgsVectorLayer, dataStorage = None):
    """Converts a QgsCircularString to Speckle"""
    try:
        #print("____Arc to Speckle ___")
        arc = Arc()
        vert_list = [pt for pt in poly.vertices()] 
        arc.startPoint = pointToSpeckle(vert_list[0], feature, layer)
        arc.midPoint = pointToSpeckle(vert_list[1], feature, layer)
        arc.endPoint = pointToSpeckle(vert_list[2], feature, layer)
        center, radius = getArcCenter(arc.startPoint, arc.midPoint, arc.endPoint)
        arc.plane = Plane()#.from_list(Point(), Vector(Point(0, 0, 1)), Vector(Point(0,1,0)), Vector(Point(-1,0,0)))
        arc.plane.origin = Point.from_list(center)
        arc.units = "m"
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
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
    
def getArcCenter(p1: Point, p2: Point, p3: Point, dataStorage = None) -> Tuple[Point, float]:
    try:
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
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None, None 
    

def lineToNative(line: Line, dataStorage = None) -> QgsLineString:
    """Converts a Speckle Line to QgsLineString"""
    try:
        line = QgsLineString(pointToNative(line.start, dataStorage), pointToNative(line.end, dataStorage))
        return line
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

def polylineToNative(poly: Polyline, dataStorage = None) -> QgsLineString:
    """Converts a Speckle Polyline to QgsLineString"""
    try: 
        # this function can be called from Multipolyline, hence extra check if the type of segment in not Polyline
        if isinstance(poly, Polycurve): 
            return polycurveToNative(poly)
        if isinstance(poly, Arc): 
            return arcToNative(poly)
        if isinstance(poly, Circle): 
            return circleToNative(poly)
        if isinstance(poly, Ellipse): 
            return ellipseToNative(poly)

        if poly.closed is False: 
            polyline = QgsLineString([pointToNative(pt, dataStorage ) for pt in poly.as_points()])
            #return polyline
        else:
            ptList = poly.as_points()
            ptList.append(ptList[0])
            polyline = QgsLineString([pointToNative(pt, dataStorage ) for pt in ptList])
        return polyline
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

def ellipseToNative(poly: Ellipse, dataStorage = None)-> QgsLineString:
    """Converts a Speckle Ellipse to QgsLineString"""
    try: 
        try: angle = atan( poly.plane.xdir.y / poly.plane.xdir.x ) 
        except: angle = math.pi / 2

        ellipse = QgsEllipse(pointToNative(poly.plane.origin, dataStorage ), poly.firstRadius, poly.secondRadius, angle)
        ellipse = ellipse.toLineString()
        return ellipse
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

def curveToNative(poly: Curve, dataStorage = None) -> QgsLineString:
    """Converts a Speckle Curve to QgsLineString"""
    try: 
        display = poly.displayValue
        curve = polylineToNative(display, dataStorage ) 
        return curve
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

def arcToNative(poly: Arc, dataStorage = None) -> QgsCircularString:
    """Converts a Speckle Arc to QgsCircularString"""
    try:
        arc = QgsCircularString(pointToNative(poly.startPoint, dataStorage ), pointToNative(poly.midPoint, dataStorage ), pointToNative(poly.endPoint, dataStorage ))
        return arc
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

def circleToNative(poly: Circle, dataStorage = None) -> QgsLineString:
    """Converts a Speckle Circle to QgsLineString"""
    try: 
        scaleFactor = get_scale_factor(poly.units, dataStorage )
        circle = QgsCircle(pointToNative(poly.plane.origin, dataStorage ), poly.radius * scaleFactor)
        circle = circle.toLineString() # QgsCircle is not supported to be added as a feature, workaround (not working): https://gis.stackexchange.com/questions/411892/typeerror-qgsgeometry-frompolygonxy-argument-1-has-unexpected-type-qgspolyg 
        return circle
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

def polycurveToNative(poly: Polycurve, dataStorage = None) -> QgsLineString:

    try: 
        curve = QgsCompoundCurve()
        pts_comp = []

        points = []
        #curve = QgsLineString()
        singleSegm = 0
        try:
            if len(poly.segments) == 0: return None
            elif len(poly.segments) == 1: singleSegm = 1

            for segm in poly.segments: # Line, Polyline, Curve, Arc, Circle
                if isinstance(segm,Line):  
                    converted = lineToNative(segm) # QgsLineString
                    if singleSegm == 1: return converted
                    
                    #if len(points) == 0: 
                    #    pts_comp.append(converted.startPoint())
                    #    curve.addVertex(converted.startPoint())
                    #pts_comp.append(converted.endPoint())
                    #curve.addVertex(converted.endPoint())

                elif isinstance(segm,Polyline):  
                    converted = polylineToNative(segm) # QgsLineString
                    if singleSegm == 1: return converted

                    #for k in range(converted.childCount()-1):
                    #    pts_comp.append(converted.childPoint(k))
                    #    curve.addVertex(converted.childPoint(k))
                    
                elif isinstance(segm,Curve):  
                    converted = curveToNative(segm) # QgsLineString
                    if singleSegm == 1: return converted

                    #for k in range(converted.childCount()):
                    #    pts_comp.append(converted.childPoint(k))
                    #    curve.addVertex(converted.childPoint(k))
                        
                elif isinstance(segm,Circle):  
                    pts = [pointToNative(pt, dataStorage ) for pt in speckleArcCircleToPoints(segm)]
                    converted = QgsLineString(pts) # QgsLineString
                    if singleSegm == 1: return circleToNative(segm)
                    else: return None
                    #converted = circleToNative(segm) # QgsLineString
                elif isinstance(segm,Arc):  
                    #pts = [pointToNative(pt, dataStorage ) for pt in speckleArcCircleToPoints(segm)]
                    #converted = QgsLineString(pts) # arcToNative(segm) # QgsLineString
                    converted = arcToNative(segm, dataStorage)
                    
                    #curve.addCurve(converted.childPoint(0),converted.childPoint(1),converted.childPoint(2))

                    if singleSegm == 1: return arcToNative(segm)
                elif isinstance(segm, Ellipse):  
                    pts = [pointToNative(pt, dataStorage ) for pt in speckleEllipseToPoints(segm)]
                    converted =  QgsLineString(pts) # QgsLineString
                    if singleSegm == 1: return arcToNative(segm)
                    else: return None
                else: # return a part of the curve 
                    logToUser(f"Part of the polycurve cannot be converted", level = 1, func = inspect.stack()[0][3])
                    curve = QgsLineString(points)
                    return curve
                
                # add converted segment 
                if converted is not None: 
                    curve.addCurve(converted, extendPrevious = True)
                    #for pt in converted.vertices():
                    #    if len(points)>0 and pt.x()== points[len(points)-1].x() and pt.y()== points[len(points)-1].y() and pt.z()== points[len(points)-1].z(): pass
                    #    else: points.append(pt)
                else:
                    logToUser(f"Part of the polycurve cannot be converted", level = 1, func = inspect.stack()[0][3])
                    curve = QgsLineString(points)
                    return curve
        except: curve = None

        #new_curve = QgsLineString(points)
        return curve
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

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


def speckleEllipseToPoints(poly: Ellipse, dataStorage = None) -> List[Point]:
    try:
        qgsLineStr = ellipseToNative(poly)
        points = qgsLineStr.vertices()

        specklePts = [pointToSpeckle(pt, None, None) for pt in points]
        return specklePts
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    

