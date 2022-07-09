""" This module contains all geometry conversion functionality To and From Speckle."""

from qgis.core import (
    Qgis, QgsWkbTypes, QgsPolygon, QgsPointXY, QgsPoint, QgsFeature, QgsVectorLayer
)
from typing import Sequence

from specklepy.objects import Base

from speckle.converter.geometry.mesh import rasterToMesh
from speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    polylineToNative,
)
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.logging import logger
import math
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

        #if len(voids) == 0: # if there is a mesh with no voids 
        vertices = []
        total_vertices = 0
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
    polygon.setExteriorRing(polylineToNative(poly["boundary"]))
    try:
      for void in poly["voids"]: 
        #print(polylineToNative(void))
        polygon.addInteriorRing(polylineToNative(void))
    except:
      pass
    #print(polygon)
    #print()

    #polygon = QgsPolygon(
    #    polylineToNative(poly["boundary"]),
    #    [polylineToNative(void) for void in poly["voids"]],
    #)
    return polygon
