""" This module contains all geometry conversion functionality To and From Speckle."""

import inspect
import random
from qgis.core import Qgis, QgsGeometry, QgsPolygon, QgsPointXY, QgsPoint, QgsFeature, QgsVectorLayer, QgsCoordinateReferenceSystem

from typing import List, Sequence

from specklepy.objects.geometry import Point, Line, Polyline, Circle, Arc, Polycurve, Mesh 
from specklepy.objects import Base
from specklepy.objects.GIS.geometry import GisPolygonGeometry

from speckle.converter.geometry.mesh import meshPartsFromPolygon, constructMesh
from speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    polylineToNative,
    unknownLineToSpeckle
)
from speckle.converter.geometry.utils import *
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.converter.layers.utils import get_raster_stats, getArrayIndicesFromXY, getElevationLayer, getRasterArrays, isAppliedLayerTransformByKeywords, moveVertically, reprojectPt
from speckle.utils.panel_logging import logger
import math
from osgeo import gdal 
import numpy as np 

#from panda3d.core import Triangulator

from PyQt5.QtGui import QColor

from speckle.utils.panel_logging import logToUser

def polygonToSpeckleMesh(geom: QgsGeometry, feature: QgsFeature, layer: QgsVectorLayer, dataStorage):

    polygon = GisPolygonGeometry(units = "m")
    #print(dataStorage)
    try: 

        vertices = []
        faces = [] 
        colors = []
        existing_vert = 0
        for p in geom.parts():
            boundary, voidsNative = getPolyBoundaryVoids(p, feature, layer, dataStorage)
            polyBorder = speckleBoundaryToSpecklePts(boundary, dataStorage)
            voids = []
            voidsAsPts = []
            
            for v in voidsNative:
                pts_fixed = []
                v_speckle = unknownLineToSpeckle(v, True, feature, layer, dataStorage)
                pts = speckleBoundaryToSpecklePts(v_speckle, dataStorage)
                
                plane_pts = [ [polyBorder[0].x, polyBorder[0].y, polyBorder[0].z],
                                [polyBorder[1].x, polyBorder[1].y, polyBorder[1].z],
                                [polyBorder[2].x, polyBorder[2].y, polyBorder[2].z] ]
                for pt in pts:
                    z_val = pt.z
                    #print(str(z_val))
                    # project the pts on the plane
                    point = [pt.x, pt.y, 0]
                    z_val = projectToPolygon( point , plane_pts)
                    pts_fixed.append(Point(units = "m", x = pt.x, y = pt.y, z = z_val))

                voids.append(polylineFromVerticesToSpeckle(pts_fixed, True, feature, layer, dataStorage))
                voidsAsPts.append(pts_fixed) 

            total_vert, vertices_x, faces_x, colors_x = meshPartsFromPolygon(polyBorder, voidsAsPts, existing_vert, feature, geom, layer, None, dataStorage)
            
            if total_vert is None:
                return None 
            existing_vert += total_vert
            vertices.extend(vertices_x)
            faces.extend(faces_x)
            colors.extend(colors_x)

        mesh = constructMesh(vertices, faces, colors, dataStorage)
        if mesh is not None: 
            polygon.displayValue = [ mesh ] 
            polygon.boundary = None
            polygon.voids = None 
        else: 
            polygon.boundary = boundary
            polygon.voids = voids 
            logToUser("Mesh creation from Polygon failed. Boundaries will be used as displayValue", level = 1, func = inspect.stack()[0][3])
        return polygon 
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def getZaxisTranslation(layer, boundaryPts, dataStorage): 
    #### check if elevation is applied and layer exists: 
    elevationLayer = getElevationLayer(dataStorage) 
    polygonWkt = dataStorage.project.crs().toWkt() 
    polygonProj = QgsCoordinateReferenceSystem.fromWkt(polygonWkt).toProj().replace(" +type=crs","")
    
    translationValue = None 
    if elevationLayer is not None: 
        all_arrays, all_mins, all_maxs, all_na = getRasterArrays(elevationLayer)
        settings_elevation_layer = get_raster_stats(elevationLayer)
        xres, yres, originX, originY, sizeX, sizeY, rasterWkt, rasterProj = settings_elevation_layer

        allElevations = []
        for pt in boundaryPts: 
            posX, posY = reprojectPt(pt.x(), pt.y(), polygonWkt, polygonProj, rasterWkt, rasterProj)
            index1, index2, remainder1, remainder2 = getArrayIndicesFromXY( settings_elevation_layer, posX, posY )
            #print("___finding elevation__")
            #print(posX)
            #print(index1)

            if index1 is None:  continue 
            else: 
                h = all_arrays[0][index1][index2] 
                allElevations.append(h) 

        if len(allElevations) == 0:
            translationValue = None 
        else:
            if np.isnan(boundaryPts[0].z()) : # for flat polygons with z=0
                translationValue = min(allElevations)
            else:     
                translationValue = min(allElevations) - boundaryPts[0].z()  
    
    return translationValue

def isFlat(ptList):
    flat = True
    universal_z_value = ptList[0].z()
    for i, pt in enumerate(ptList):
        if isinstance(pt, QgsPointXY):
            break 
        elif np.isnan(pt.z()): 
            break 
        elif pt.z() != universal_z_value:
            flat = False
            break
    return flat 

def polygonToSpeckle(geom: QgsGeometry, feature: QgsFeature, layer: QgsVectorLayer, height, projectZval, dataStorage):
    """Converts a QgsPolygon to Speckle"""
    #print("Polygon To Speckle")
    #print(dataStorage)
    polygon = GisPolygonGeometry(units = "m")
    try:
        boundary, voidsNative = getPolyBoundaryVoids(geom, feature, layer, dataStorage)

        if projectZval is not None: 
            boundary = moveVertically(boundary, projectZval)
        
        polyBorder = speckleBoundaryToSpecklePts(boundary, dataStorage)
        voids = []
        voidsAsPts = []

        for v in voidsNative:
            pts_fixed = []
            v_speckle = unknownLineToSpeckle(v, True, feature, layer, dataStorage)
            pts = speckleBoundaryToSpecklePts(v_speckle, dataStorage)
            
            plane_pts = [ [polyBorder[0].x, polyBorder[0].y, polyBorder[0].z],
                            [polyBorder[1].x, polyBorder[1].y, polyBorder[1].z],
                            [polyBorder[2].x, polyBorder[2].y, polyBorder[2].z] ]
            for pt in pts:
                z_val = pt.z
                #print(str(z_val))
                # project the pts on the plane
                point = [pt.x, pt.y, 0]
                z_val = projectToPolygon( point , plane_pts)
                pts_fixed.append(Point(units = "m", x = pt.x, y = pt.y, z = z_val))

            voids.append(polylineFromVerticesToSpeckle(pts_fixed, True, feature, layer, dataStorage))
            voidsAsPts.append(pts_fixed) 

        polygon.boundary = boundary
        polygon.voids = voids
        total_vert, vertices, faces, colors = meshPartsFromPolygon(polyBorder, voidsAsPts, 0, feature, geom, layer, height, dataStorage)

        mesh = constructMesh(vertices, faces, colors, dataStorage)
        if mesh is not None: 
            polygon.displayValue = [ mesh ] 
            #polygon["baseGeometry"] = mesh 
            # https://latest.speckle.dev/streams/85bc4f61c6/commits/2a5d23a277
            # https://speckle.community/t/revit-add-new-parameters/5170/2 
        else: 
            #polygon.boundary = boundary
            #polygon.voids = voids
            logToUser("Mesh creation from Polygon failed. Boundaries will be used as displayValue", level = 1, func = inspect.stack()[0][3])
        
        return polygon
    
    except Exception as e:
        logToUser("Some polygons might be invalid: " + str(e), level = 1, func = inspect.stack()[0][3])
        return None
    


def polygonToNative(poly: Base, dataStorage) -> QgsPolygon:
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""
    #print(polylineToNative(poly["boundary"]))
    
    polygon = QgsPolygon()
    try:
        try: # if it's indeed a polygon with QGIS properties
            boundary = poly.boundary
            polygon.setExteriorRing(polylineToNative(boundary, dataStorage ))
        except: 
            try:
                boundary = poly["boundary"]
                polygon.setExteriorRing(polylineToNative(boundary, dataStorage ))
            except: return
        try:
            voids = poly.voids
            for void in voids: 
                #print(polylineToNative(void))
                polygon.addInteriorRing(polylineToNative(void, dataStorage ))
        except:
            try:
                voids = poly["voids"]
                for void in voids: 
                    #print(polylineToNative(void))
                    polygon.addInteriorRing(polylineToNative(void, dataStorage ))
            except: pass
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

def getPolyBoundaryVoids(geom: QgsGeometry, feature: QgsFeature, layer: QgsVectorLayer, dataStorage):
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
            boundary = unknownLineToSpeckle(extRing, True, feature, layer, dataStorage)
        else: return boundary, voids

        try:
            geom = geom.constGet()
        except: pass
        for i in range(geom.numInteriorRings()):
            intRing = unknownLineToSpeckle(geom.interiorRing(i), True, feature, layer, dataStorage)
            #intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True, feature, layer)
            voids.append(geom.interiorRing(i))   

        return boundary, voids
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None, None 
    
