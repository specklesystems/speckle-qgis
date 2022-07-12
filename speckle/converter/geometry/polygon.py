""" This module contains all geometry conversion functionality To and From Speckle."""

from qgis.core import (
    Qgis, QgsWkbTypes, QgsPolygon, QgsPointXY, QgsPoint, QgsFeature, QgsVectorLayer
)
from typing import Sequence

from specklepy.objects import Base
from specklepy.objects.geometry import Point

from speckle.converter.geometry.mesh import rasterToMesh
from speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    polylineToNative,
)
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.logging import logger
import math

from panda3d.core import Triangulator

from PyQt5.QtGui import QColor


def polygonToSpeckle(geom, feature: QgsFeature, layer: QgsVectorLayer):
    """Converts a QgsPolygon to Speckle"""
    try: 
        polygon = Base()
        pointList = []
        pt_iterator = []
        try: 
            pt_iterator = geom.exteriorRing().vertices()
        except: 
            pt_iterator = geom.vertices()
        for pt in pt_iterator: pointList.append(pt) 
        boundary = polylineFromVerticesToSpeckle(pointList, True, feature, layer) 
        voids = []
        try:
            for i in range(geom.numInteriorRings()):
                intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True, feature, layer)
                voids.append(intRing)
        except:
            pass
        polygon.boundary = boundary
        polygon.voids = voids
        polygon.displayValue = [ boundary ] + voids

        vertices = []
        total_vertices = 0

        if len(voids) == 0: # if there is a mesh with no voids
            for pt in pointList:
                if isinstance(pt, QgsPointXY):
                    pt = QgsPoint(pt)
                x = pt.x()
                y = pt.y()
                z = 0 if math.isnan(pt.z()) else pt.z()
                vertices.extend([x, y, z])
                total_vertices += 1

            ran = range(0, total_vertices)
            faces = [total_vertices]
            faces.extend([i for i in ran])
            # else: https://docs.panda3d.org/1.10/python/reference/panda3d.core.Triangulator
        else:
            trianglator = Triangulator()
            faces = []

            # add boundary points
            polyBorder = boundary.as_points()
            pt_count = 0
            # add extra middle point for border
            for pt in polyBorder:
              if pt_count < len(polyBorder)-1: 
                  pt2 = polyBorder[pt_count+1]
              else: pt2 = polyBorder[0]
              
              trianglator.addPolygonVertex(trianglator.addVertex(pt.x, pt.y))
              vertices.extend([pt.x, pt.y, pt.z])
              trianglator.addPolygonVertex(trianglator.addVertex((pt.x+pt2.x)/2, (pt.y+pt2.y)/2))
              vertices.extend([(pt.x+pt2.x)/2, (pt.y+pt2.y)/2, (pt.z+pt2.z)/2])
              total_vertices += 2
              pt_count += 1

            #add void points
            for i in range(len(voids)):
              trianglator.beginHole()
              pts = voids[i].as_points()
              for pt in pts:
                trianglator.addHoleVertex(trianglator.addVertex(pt.x, pt.y))
                vertices.extend([pt.x, pt.y, pt.z])
                total_vertices += 1

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
        polygon.displayValue = mesh 

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
