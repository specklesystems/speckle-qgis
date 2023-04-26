

import inspect
import random
from specklepy.objects.geometry import Point, Line, Polyline, Circle, Arc, Polycurve
from specklepy.objects import Base
from typing import List, Union, Dict 

from speckle.converter.geometry.polyline import speckleArcCircleToPoints, specklePolycurveToPoints
from ui.logger import logToUser

from qgis.core import (Qgis, QgsProject, QgsLayerTreeLayer, QgsFeature,
                       QgsRasterLayer, QgsVectorLayer, QgsPoint )

import triangle as tr


def cross_product(pt1, pt2):
    return [ (pt1[1] * pt2[2]) - (pt1[2] * pt2[1]),
             (pt1[2] * pt2[0]) - (pt1[0] * pt2[2]),
             (pt1[0] * pt2[1]) - (pt1[1] * pt2[0]) ]

def dot(pt1: List, pt2: List):
    return (pt1[0] * pt2[0]) + (pt1[1] * pt2[1]) + (pt1[2] * pt2[2])

def normalize(pt: List, tolerance= 1e-10):
    magnitude = dot(pt, pt) ** 0.5
    if abs(magnitude - 1) < tolerance:
        return pt

    if magnitude !=0: scale = 1.0 / magnitude
    else: scale = 1.0
    normalized_vector = [coordinate * scale for coordinate in pt]
    return normalized_vector 

def createPlane(pt1: List, pt2: List, pt3: List):
    vector1to2 = [ pt2[0]-pt1[0], pt2[1]-pt1[1], pt2[2]-pt1[2] ]
    vector1to3 = [ pt3[0]-pt1[0], pt3[1]-pt1[1], pt3[2]-pt1[2] ]

    u_direction = normalize(vector1to2)
    normal = cross_product( u_direction, vector1to3 )
    return {'origin': pt1, 'normal': normal}

def project_to_plane_on_z(point: List, plane: Dict):
    d = dot(plane["normal"], plane["origin"])
    z_value_on_plane = (d - (plane["normal"][0] * point[0]) - (plane["normal"][1] * point[1])) / plane["normal"][2] 
    return z_value_on_plane

def projectToPolygon(point: List, polygonPts: List):
    if len(polygonPts)<3: return 0
    pt1 = polygonPts[0]
    pt2 = polygonPts[1]
    pt3 = polygonPts[2]
    plane = createPlane(pt1, pt2, pt3)
    z = project_to_plane_on_z(point, plane)
    return z 


def triangulatePolygon(geom): 
    try:
        vertices = []
        segments = []
        holes = []
        vertices, vertices3d, segments, holes = getPolyPtsSegments(geom)

        r'''
        # add layer with hole points (for debugging) 
        proj = QgsProject.instance()
        crs = proj.crs()
        vl = QgsVectorLayer("PointZ"+ "?crs=" + crs.authid(), "Points", "memory") # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        pr = vl.dataProvider()
        vl.startEditing()
        fets = []
        for pt in holes:
            feat = QgsFeature()
            feat.setGeometry(QgsPoint(pt[0], pt[1], 0))
            fets.append(feat)
        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()
        proj.addMapLayer(vl, True)
        '''

        if len(holes)>0: 
            dict_shape= {'vertices': vertices, 'segments': segments ,'holes': holes}
        else: 
            dict_shape= {'vertices': vertices, 'segments': segments }
        t = tr.triangulate(dict_shape, 'p')
        return t, vertices3d 
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])


def getPolyPtsSegments(geom):
    vertices = []
    vertices3d = []
    segmList = []
    holes = []
    try: 
        extRing = geom.exteriorRing()
        pt_iterator = extRing.vertices()
    except: 
        try:  
            extRing = geom.constGet().exteriorRing()
            pt_iterator = geom.vertices()
        except: 
            extRing = geom
            pt_iterator = geom.vertices()
    
    pointListLocal = []
    startLen = len(vertices)
    for i, pt in enumerate(pt_iterator): 
        if len(pointListLocal)>0 and pt.x()==pointListLocal[0].x() and pt.y()==pointListLocal[0].y(): #don't repeat 1st point
            pass
        else: 
            pointListLocal.append(pt)
    for i,pt in enumerate(pointListLocal):
        #print(pt)
        vertices.append([pt.x(),pt.y()])
        try: vertices3d.append([pt.x(),pt.y(),pt.z()])
        except: vertices3d.append([pt.x(),pt.y(), 0]) # project boundary to 0
        if i>0: 
            segmList.append([startLen+i-1, startLen+i])
        if i == len(pointListLocal)-1: #also add a cap
            segmList.append([startLen+i, startLen])
    
    ########### get voids 
    try:
        geom = geom.constGet()
    except: pass
    try:
        intRingsNum = geom.numInteriorRings()
        for i in range(intRingsNum):
            intRing = geom.interiorRing(i)
            pt_iterator = intRing.vertices()

            pointListLocal = []
            startLen = len(vertices)
            for i, pt in enumerate(pt_iterator): 
                if len(pointListLocal)>0 and pt.x()==pointListLocal[0].x() and pt.y()==pointListLocal[0].y(): #don't repeat 1st point
                    pass
                else: 
                    pointListLocal.append(pt) 
            holes.append(getHolePt(pointListLocal))

            for i,pt in enumerate(pointListLocal):
                vertices.append([pt.x(),pt.y()])
                try: vertices3d.append([pt.x(),pt.y(), pt.z()])
                except: vertices3d.append([pt.x(),pt.y(), None]) # leave voids Z as None, fill later
                if i>0: 
                    segmList.append([startLen+i-1, startLen+i])
                if i == len(pointListLocal)-1: #also add a cap
                    segmList.append([startLen+i, startLen])
    except Exception as e: 
        logToUser(e, level = 1, func = inspect.stack()[0][3])
    return vertices, vertices3d, segmList, holes

def fix_orientation(polyBorder, positive = True, coef = 1): 
    #polyBorder = [QgsPoint(-1.42681236722918436,0.25275926575812246), QgsPoint(-1.42314917758289616,0.78756097253123281), QgsPoint(-0.83703883417681257,0.77290957257654203), QgsPoint(-0.85169159276196471,0.24176979917208921), QgsPoint(-1.42681236722918436,0.25275926575812246)]
    sum_orientation = 0 
    for k, ptt in enumerate(polyBorder): #pointList:
        index = k+1
        if k == len(polyBorder)-1: index = 0
        pt = polyBorder[k*coef]
        pt2 = polyBorder[index*coef]
        #print(pt)
        try: sum_orientation += (pt2.x - pt.x) * (pt2.y + pt.y) # if Speckle Points
        except: sum_orientation += (pt2.x() - pt.x()) * (pt2.y() + pt.y()) # if QGIS Points
    if positive is True: 
        if sum_orientation < 0:
            polyBorder.reverse()
    else: 
        if sum_orientation > 0:
            polyBorder.reverse()
    return polyBorder
 
def getHolePt(pointListLocal):
    pointListLocal = fix_orientation(pointListLocal, True, 1)
    minXpt = pointListLocal[0]
    index = 0
    index2 = 1
    for i, pt in enumerate(pointListLocal):
        if pt.x() < minXpt.x(): 
            minXpt = pt
            index = i
            if i == len(pointListLocal)-1: index2 = 0
            else: index2 = index+1
    x_range = pointListLocal[index2].x() - minXpt.x()
    y_range = pointListLocal[index2].y() - minXpt.y()
    if y_range > 0:
        sidePt = [ minXpt.x() + abs(x_range/2) + 0.001, minXpt.y() + y_range/2 ]
    else:
        sidePt = [ minXpt.x() + abs(x_range/2) - 0.001, minXpt.y() + y_range/2 ]
    return sidePt
   
def getPolygonFeatureHeight(feature, layer, dataStorage):
    
    height = None
    ignore = False
    if dataStorage.savedTransforms is not None:
        for item in dataStorage.savedTransforms:
            layer_name = item.split("  ->  ")[0]
            transform_name = item.split("  ->  ")[1]
            if layer_name == layer.name():
                if "ignore" in transform_name: ignore = True
                
                print("Apply transform: " + transform_name)
                if "extrude polygons" in transform_name.lower():

                    # additional check: 
                    try:
                        if dataStorage.project.crs().isGeographic():
                            logToUser("Extrusion can only be applied when project CRS is using metric units", level = 1, func = inspect.stack()[0][3])
                            return None
                    except: return None
                    
                    try:
                        existing_height = feature["height"]
                        if existing_height is None or str(existing_height) == "NULL": # if attribute value invalid
                            if ignore is True:
                                return None
                            else: # find approximate value
                                all_existing_vals = [f["height"] for f in layer.getFeatures() if (f["height"] is not None and (isinstance(f["height"], float) or isinstance(f["height"], int) ) ) ]
                                try: 
                                    if len(all_existing_vals) > 5:
                                        height_average = all_existing_vals[int(len(all_existing_vals)/2)]
                                        height = random.randint(height_average-5, height_average+5)
                                    else:
                                        height = random.randint(10, 20)
                                except: 
                                    height = random.randint(10, 20)
                        else: # reading from existing attribute 
                            height = existing_height

                    except: # if no Height attribute
                        if ignore is True:
                            height = None
                        else:
                            height = random.randint(10, 20)
        
    return height


def speckleBoundaryToSpecklePts(boundary: Union[None, Polyline, Arc, Line, Polycurve]) -> List[Point]:
    # add boundary points
    try:
        polyBorder = []
        if isinstance(boundary, Circle) or isinstance(boundary, Arc): 
            polyBorder = speckleArcCircleToPoints(boundary) 
        elif isinstance(boundary, Polycurve): 
            polyBorder = specklePolycurveToPoints(boundary) 
        elif isinstance(boundary, Line): pass
        else: 
            try: polyBorder = boundary.as_points()
            except: pass # if Line or None
        return polyBorder
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    