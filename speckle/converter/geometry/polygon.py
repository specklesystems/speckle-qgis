""" This module contains all geometry conversion functionality To and From Speckle."""

import inspect
import random
from qgis.core import Qgis, QgsGeometry, QgsPolygon, QgsPointXY, QgsPoint, QgsFeature, QgsVectorLayer

from typing import List, Sequence

from specklepy.objects.geometry import Point, Line, Polyline, Circle, Arc, Polycurve, Mesh 
from specklepy.objects import Base
from specklepy.objects.geometry import Point

from speckle.converter.geometry.mesh import meshPartsFromPolygon, constructMesh
from speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    polylineToNative,
    unknownLineToSpeckle
)
from speckle.converter.geometry.utils import *
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.logging import logger
import math

#from panda3d.core import Triangulator

from PyQt5.QtGui import QColor

from ui.logger import logToUser

def polygonToSpeckleMesh(geom: QgsGeometry, feature: QgsFeature, layer: QgsVectorLayer):

    polygon = Base(units = "m")
    try: 

        vertices = []
        faces = [] 
        colors = []
        existing_vert = 0
        for p in geom.parts():
            boundary, voidsNative = getPolyBoundaryVoids(p, feature, layer)
            polyBorder = speckleBoundaryToSpecklePts(boundary)
            voids = []
            voidsAsPts = []
            
            for v in voidsNative:
                pts_fixed = []
                v_speckle = unknownLineToSpeckle(v, True, feature, layer)
                pts = speckleBoundaryToSpecklePts(v_speckle)
                
                plane_pts = [ [polyBorder[0].x, polyBorder[0].y, polyBorder[0].z],
                                [polyBorder[1].x, polyBorder[1].y, polyBorder[1].z],
                                [polyBorder[2].x, polyBorder[2].y, polyBorder[2].z] ]
                for pt in pts:
                    z_val = pt.z
                    print(str(z_val))
                    # project the pts on the plane
                    point = [pt.x, pt.y, 0]
                    z_val = projectToPolygon( point , plane_pts)
                    pts_fixed.append(Point(units = "m", x = pt.x, y = pt.y, z = z_val))

                voids.append(polylineFromVerticesToSpeckle(pts_fixed, True, feature, layer))
                voidsAsPts.append(pts_fixed) 

            total_vert, vertices_x, faces_x, colors_x = meshPartsFromPolygon(polyBorder, voidsAsPts, existing_vert, feature, geom, layer, None)
            
            if total_vert is None:
                return None 
            existing_vert += total_vert
            vertices.extend(vertices_x)
            faces.extend(faces_x)
            colors.extend(colors_x)

        mesh = constructMesh(vertices, faces, colors)
        if mesh is not None: 
            polygon.displayValue = [ mesh ] 
        else: 
            logToUser("Mesh creation from Polygon failed. Boundaries will be used as displayValue", level = 1, func = inspect.stack()[0][3])
        return polygon 
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None
    
def polygonToSpeckle(geom: QgsGeometry, feature: QgsFeature, layer: QgsVectorLayer, dataStorage = None, height = None):
    """Converts a QgsPolygon to Speckle"""
    polygon = Base(units = "m")
    try:
        boundary, voidsNative = getPolyBoundaryVoids(geom, feature, layer)
        polyBorder = speckleBoundaryToSpecklePts(boundary)
        voids = []
        voidsAsPts = []

        for v in voidsNative:
            pts_fixed = []
            v_speckle = unknownLineToSpeckle(v, True, feature, layer)
            pts = speckleBoundaryToSpecklePts(v_speckle)
            
            plane_pts = [ [polyBorder[0].x, polyBorder[0].y, polyBorder[0].z],
                            [polyBorder[1].x, polyBorder[1].y, polyBorder[1].z],
                            [polyBorder[2].x, polyBorder[2].y, polyBorder[2].z] ]
            for pt in pts:
                z_val = pt.z
                print(str(z_val))
                # project the pts on the plane
                point = [pt.x, pt.y, 0]
                z_val = projectToPolygon( point , plane_pts)
                pts_fixed.append(Point(units = "m", x = pt.x, y = pt.y, z = z_val))

            voids.append(polylineFromVerticesToSpeckle(pts_fixed, True, feature, layer))
            voidsAsPts.append(pts_fixed) 

        polygon.boundary = boundary
        polygon.voids = voids
        #polygon.displayValue = [ boundary ] + voids
        
        
        # check before extrusion
        if height is not None:
            universal_z_value = polyBorder[0].z
            for i, pt in enumerate(polyBorder):
                ########## check for non-flat polygons 
                if pt.z != universal_z_value:
                    logToUser("Extrusion can only be applied to flat polygons", level = 1, func = inspect.stack()[0][3])
                    height = None
        
        total_vert, vertices, faces, colors = meshPartsFromPolygon(polyBorder, voidsAsPts, 0, feature, geom, layer, height)

        mesh = constructMesh(vertices, faces, colors)
        if mesh is not None: 
            #polygon.displayValue = [ mesh ] 
            polygon["baseGeometry"] = mesh 
            # https://latest.speckle.dev/streams/85bc4f61c6/commits/2a5d23a277
            # https://speckle.community/t/revit-add-new-parameters/5170/2 
        else: 
            logToUser("Mesh creation from Polygon failed. Boundaries will be used as displayValue", level = 1, func = inspect.stack()[0][3])
        
        return polygon
    
    except Exception as e:
        logToUser("Some polygons might be invalid" + str(e), level = 1, func = inspect.stack()[0][3])
        return None
    


def polygonToNative(poly: Base) -> QgsPolygon:
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""
    #print(polylineToNative(poly["boundary"]))
    
    polygon = QgsPolygon()
    try:
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
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return polygon 

def getPolyBoundaryVoids(geom: QgsGeometry, feature: QgsFeature, layer: QgsVectorLayer):
    boundary = None
    voids: List[Union[None, Polyline, Arc, Line, Polycurve]] = []
    try: 
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
        else: return boundary, voids

        try:
            geom = geom.constGet()
        except: pass
        for i in range(geom.numInteriorRings()):
            intRing = unknownLineToSpeckle(geom.interiorRing(i), True, feature, layer)
            #intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True, feature, layer)
            voids.append(geom.interiorRing(i))   

        return boundary, voids
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None, None 
    
