""" This module contains all geometry conversion functionality To and From Speckle."""

from qgis.core import (
    Qgis, QgsGeometry, QgsPolygon, QgsPointXY, QgsPoint, QgsFeature, QgsVectorLayer
)
from typing import Sequence

from specklepy.objects.geometry import Point, Line, Polyline, Circle, Arc, Polycurve
from specklepy.objects import Base
from specklepy.objects.geometry import Point

from speckle.converter.geometry.mesh import rasterToMesh
from speckle.converter.geometry.point import pointToNative
from speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    polylineToNative,
    speckleArcCircleToPoints,
    specklePolycurveToPoints,
    unknownLineToSpeckle
)
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.logging import logger
import math

from panda3d.core import Triangulator

from PyQt5.QtGui import QColor


def polygonToSpeckle(geom: QgsGeometry, feature: QgsFeature, layer: QgsVectorLayer):
    """Converts a QgsPolygon to Speckle"""
    try: 
        polygon = Base(units = "m")
        pointList = []
        pt_iterator = []
        extRing = None
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
        for pt in pt_iterator: pointList.append(pt) 
        if extRing is not None: 
            boundary = unknownLineToSpeckle(extRing, True, feature, layer)
        else: return None
        #boundary = polylineFromVerticesToSpeckle(pointList, True, feature, layer) 
        voids = []
        try:
            for i in range(geom.numInteriorRings()):
                intRing = unknownLineToSpeckle(geom.interiorRing(i), True, feature, layer)
                #intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True, feature, layer)
                voids.append(intRing)
        except: 
            try:
                geom = geom.constGet()
                for i in range(geom.numInteriorRings()):
                    intRing = unknownLineToSpeckle(geom.interiorRing(i), True, feature, layer)
                    #intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True, feature, layer)
                    voids.append(intRing)
            except: pass

        polygon.boundary = boundary
        polygon.voids = voids
        polygon.displayValue = [ boundary ] + voids

        vertices = []
        total_vertices = 0

        # add boundary points
        polyBorder = []
        if isinstance(boundary, Circle) or isinstance(boundary, Arc): 
            polyBorder = speckleArcCircleToPoints(boundary) 
        elif isinstance(boundary, Polycurve): 
            polyBorder = specklePolycurveToPoints(boundary) 
        elif isinstance(boundary, Line): pass
        else: 
            try: polyBorder = boundary.as_points()
            except: pass # if Line
        #polyBorder = boundary.as_points()

        coef = 1
        maxPoints = 5000
        if len(polyBorder) >= maxPoints: coef = int(len(polyBorder)/maxPoints)
            
        if len(voids) == 0: # only if there is a mesh with no voids and large amount of points
            for k, ptt in enumerate(polyBorder): #pointList:
                pt = polyBorder[k*coef]
                if k < maxPoints:
                    if isinstance(pt, QgsPointXY):
                        pt = QgsPoint(pt)
                    if isinstance(pt,Point):
                        pt = pointToNative(pt)
                    x = pt.x()
                    y = pt.y()
                    z = 0 if math.isnan(pt.z()) else pt.z()
                    vertices.extend([x, y, z])
                    total_vertices += 1
                else: break

            ran = range(0, total_vertices)
            faces = [total_vertices]
            faces.extend([i for i in ran])
            # else: https://docs.panda3d.org/1.10/python/reference/panda3d.core.Triangulator
        else: # if there are voids 
            # if its a large polygon with voids to be triangualted, lower the coef even more:
            maxPoints = 100
            if len(polyBorder) >= maxPoints: coef = int(len(polyBorder)/maxPoints)

            trianglator = Triangulator()
            faces = []

            pt_count = 0
            # add extra middle point for border
            for k, ptt in enumerate(polyBorder): #pointList:
                pt = polyBorder[k*coef]
                if k < maxPoints:
                    if pt_count < len(polyBorder)-1 and k < (maxPoints-1): 
                        pt2 = polyBorder[(k+1)*coef]
                    else: pt2 = polyBorder[0]
                            
                    trianglator.addPolygonVertex(trianglator.addVertex(pt.x, pt.y))
                    vertices.extend([pt.x, pt.y, pt.z])
                    trianglator.addPolygonVertex(trianglator.addVertex((pt.x+pt2.x)/2, (pt.y+pt2.y)/2))
                    vertices.extend([(pt.x+pt2.x)/2, (pt.y+pt2.y)/2, (pt.z+pt2.z)/2])
                    total_vertices += 2
                    pt_count += 1
                else: break

            #add void points
            for i in range(len(voids)):
                trianglator.beginHole()

                pts = []
                if isinstance(voids[i], Circle) or isinstance(voids[i], Arc): 
                    pts = speckleArcCircleToPoints(voids[i]) 
                elif isinstance(voids[i], Polycurve): 
                    pts = specklePolycurveToPoints(voids[i]) 
                elif isinstance(voids[i], Line): pass
                else: 
                    try: pts = voids[i].as_points()
                    except: pass # if Line

                #pts = voids[i].as_points()
                coefVoid = 1
                if len(pts) >= maxPoints: coefVoid = int(len(pts)/maxPoints)
                for k, ptt in enumerate(pts):
                    pt = pts[k*coefVoid]
                    if k < maxPoints:
                        trianglator.addHoleVertex(trianglator.addVertex(pt.x, pt.y))
                        vertices.extend([pt.x, pt.y, pt.z])
                        total_vertices += 1
                    else: break
            
            trianglator.triangulate()
            i = 0
            #print(trianglator.getNumTriangles())
            while i < trianglator.getNumTriangles():
                tr = [trianglator.getTriangleV0(i),trianglator.getTriangleV1(i),trianglator.getTriangleV2(i)]
                faces.extend([3, tr[0], tr[1], tr[2]])
                i+=1
            ran = range(0, total_vertices)

        col = featureColorfromNativeRenderer(feature, layer)
        colors = [col for i in ran] # apply same color for all vertices
        mesh = rasterToMesh(vertices, faces, colors)
        polygon.displayValue = [ mesh ] 

        return polygon
    except: 
        logger.logToUser("Some polygons might be invalid", Qgis.Warning)
        pass


def polygonToNative(poly: Base) -> QgsPolygon:
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""
    #print(polylineToNative(poly["boundary"]))
    
    polygon = QgsPolygon()
    try: # if it's indeed a polygon with QGIS properties
        polygon.setExteriorRing(polylineToNative(poly["boundary"]))
    except: return
    try:
        for void in poly["voids"]: 
            #print(polylineToNative(void))
            polygon.addInteriorRing(polylineToNative(void))
    except:pass
    #print(polygon)
    #print()

    #polygon = QgsPolygon(
    #    polylineToNative(poly["boundary"]),
    #    [polylineToNative(void) for void in poly["voids"]],
    #)
    return polygon
