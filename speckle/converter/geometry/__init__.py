""" This module contains all geometry conversion functionality To and From Speckle."""

from numpy import isin
from specklepy.objects.GIS.geometry import GisLineElement, GisPointElement, GisPolygonElement
#from speckle.utils.panel_logging import logger
from typing import List, Union

from qgis.core import (QgsGeometry, QgsWkbTypes, QgsMultiPoint, 
    QgsAbstractGeometry, QgsMultiLineString, QgsMultiPolygon,
    QgsCircularString, QgsLineString, QgsRasterLayer,QgsVectorLayer, QgsFeature,
    QgsUnitTypes)
from speckle.converter.geometry.GisGeometryClasses import RevitDirectShape

from speckle.converter.geometry.utils import getPolygonFeatureHeight
from speckle.converter.geometry.mesh import meshToNative
from speckle.converter.geometry.point import pointToNative, pointToSpeckle
from speckle.converter.geometry.polygon import *
from speckle.converter.geometry.polyline import *
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline, Curve, Arc, Circle, Ellipse, Polycurve


def convertToSpeckle(feature: QgsFeature, layer: QgsVectorLayer or QgsRasterLayer, dataStorage) -> Union[Base, Sequence[Base], None]:
    """Converts the provided layer feature to Speckle objects"""
    try: 
        #print("convertToSpeckle")
        #print(dataStorage)
        try:
            geom: QgsGeometry = feature.geometry()
        except:
            geom: QgsGeometry = feature
        geomSingleType = QgsWkbTypes.isSingleType(geom.wkbType())
        geomType = geom.type()
        type = geom.wkbType()
        units = dataStorage.currentUnits #QgsUnitTypes.encodeUnit(dataStorage.project.crs().mapUnits())

        if geomType == QgsWkbTypes.PointGeometry:
            # the geometry type can be of single or multi type
            if geomSingleType:
                result = pointToSpeckle(geom.constGet(), feature, layer, dataStorage)
                result.units = units
                result = [result]
                #return result
            else:
                result = [pointToSpeckle(pt, feature, layer, dataStorage) for pt in geom.parts()]
                for r in result: r.units = units 
                #return result
            
            element = GisPointElement(units = units, geometry = result)
            return element
        
        elif geomType == QgsWkbTypes.LineGeometry: # 1
            if geomSingleType:
                result = anyLineToSpeckle(geom, feature, layer, dataStorage)
                result = addCorrectUnits(result, dataStorage)
                result = [result]
                #return result
            else: 
                result = [anyLineToSpeckle(poly, feature, layer, dataStorage) for poly in geom.parts()]
                for r in result: r = addCorrectUnits(r, dataStorage)
                #if len(result) == 1: result = result[0] 
                #return result
            
            element = GisLineElement(units = units, geometry = result)
            return element

            if type == QgsWkbTypes.CircularString or type == QgsWkbTypes.CircularStringZ or type == QgsWkbTypes.CircularStringM or type == QgsWkbTypes.CircularStringZM: #Type (not GeometryType)
                if geomSingleType:
                    result = arcToSpeckle(geom, feature, layer, dataStorage)
                    result.units = units
                    return result
                else: 
                    result = [arcToSpeckle(poly, feature, layer, dataStorage) for poly in geom.parts()]
                    for r in result: r.units = units 
                    return result
            elif type == QgsWkbTypes.CompoundCurve or type == QgsWkbTypes.CompoundCurveZ or type == QgsWkbTypes.CompoundCurveM or type == QgsWkbTypes.CompoundCurveZM: # 9, 1009, 2009, 3009
                if "CircularString" in str(geom): 
                    all_pts = [pt for pt in geom.vertices()]
                    if len(all_pts) == 3: 
                        result = arcToSpeckle(geom, feature, layer, dataStorage)
                        result.units = units
                        try: result.plane.origin.units = units 
                        except: pass
                        return result
                    else: 
                        result = compoudCurveToSpeckle(geom, feature, layer, dataStorage)
                        result.units = units
                        return result
                else: return None
            elif geomSingleType: # type = 2
                result = polylineToSpeckle(geom, feature, layer, dataStorage)
                result.units = units
                return result
            else: 
                result = [polylineToSpeckle(poly, feature, layer, dataStorage) for poly in geom.parts()]
                for r in result: r.units = units 
                return result
        
        elif geomType == QgsWkbTypes.PolygonGeometry and not geomSingleType and layer.name().endswith("_Mesh") and "Speckle_ID" in layer.fields().names():
            result = polygonToSpeckleMesh(geom, feature, layer, dataStorage)
            if result is None: return 
            result.units = units
            for v in result.displayValue: 
                if v is not None: 
                    v.units = units
            
            if not isinstance(result, List):
                result = [result]
            element = GisPolygonElement(units = units, geometry = result)
            return element
        elif geomType == QgsWkbTypes.PolygonGeometry: # 2

            height = getPolygonFeatureHeight(feature, layer, dataStorage)
            elevationLayer = getElevationLayer(dataStorage) 
            translationZaxis = None 

            if geomSingleType:

                try: boundaryPts = [ v[1] for v in enumerate(geom.exteriorRing().vertices())] 
                except: boundaryPts = [ v[1] for v in enumerate(geom.constGet().exteriorRing().vertices())] 
                if height is not None:
                    if isFlat(boundaryPts) is False:
                        logToUser("Extrusion can only be applied to flat polygons", level = 1, func = inspect.stack()[0][3])
                        height = None 
                if elevationLayer is not None and isAppliedLayerTransformByKeywords(layer, ["extrude", "polygon", "project", "elevation"], [], dataStorage) is True:
                    if isFlat(boundaryPts) is False:
                        logToUser("Geometry projections can only be applied to flat polygons", level = 1, func = inspect.stack()[0][3])
                    else:
                        translationZaxis = getZaxisTranslation(layer, boundaryPts, dataStorage)
                        if translationZaxis is None: 
                            logToUser("Some polygons are outside the elevation layer extent or extrusion value is Null", level = 1, func = inspect.stack()[0][3])
                            return 

                result = polygonToSpeckle(geom, feature, layer, height, translationZaxis, dataStorage)
                if result is None: return 
                result.units = units
                if result.boundary is not None:
                    result.boundary.units = units
                for v in result.voids: 
                    if v is not None:
                        v.units = units
                try: # if mesh creation failed, displayValue stays None
                    for v in result.displayValue: 
                        if v is not None:
                            v.units = units
                except: pass 
                
                if not isinstance(result, List):
                    result = [result]
                element = GisPolygonElement(units = units, geometry = result)
                
            
            else: 
                result = []
                for poly in geom.parts():
                    
                    try: boundaryPts = [ v[1] for v in enumerate(poly.exteriorRing().vertices())] 
                    except: boundaryPts = [ v[1] for v in enumerate(poly.constGet().exteriorRing().vertices())] 
                    if height is not None:
                        if isFlat(boundaryPts) is False:
                            logToUser("Extrusion can only be applied to flat polygons", level = 1, func = inspect.stack()[0][3])
                            height = None 
                    if elevationLayer is not None and isAppliedLayerTransformByKeywords(layer, ["extrude", "polygon", "project", "elevation"], [], dataStorage) is True: 
                        if isFlat(boundaryPts) is False:
                            logToUser("Geometry projections can only be applied to flat polygons", level = 1, func = inspect.stack()[0][3])
                        else:
                            translationZaxis = getZaxisTranslation(layer, boundaryPts, dataStorage)
                            if translationZaxis is None: 
                                logToUser("Some polygons are outside the elevation layer extent or extrusion value is Null", level = 1, func = inspect.stack()[0][3])
                                continue 
                            
                    result.append(polygonToSpeckle(poly, feature, layer, height, translationZaxis, dataStorage) )
                for r in result: 
                    if r is None: continue 
                    r.units = units 
                    r.boundary.units = units
                    for v in r.voids: 
                        if v is not None:
                            v.units = units 
                    for v in r.displayValue: 
                        if v is not None:
                            v.units = units
                
                element = GisPolygonElement(units = units, geometry = result)

            base_geoms = [] 
            for r in result:
                base_geoms.extend(r.displayValue)
            #element = RevitDirectShape(units = units, baseGeometries = base_geoms)
            #element.parameters = Base()
            #element.geometry = base_geoms
            r'''
            element.baseGeometries = base_geoms
            element.parameters = Base()

            element.name = ""
            element.type = ""
            element.category: int = 49
            element.elementId = ""
            element.isRevitLinkedModel = False 
            element.revitLinkedModelPath = ""
            element.phaseCreated = "New Construction"
            '''

            return element
        else:
            logToUser("Unsupported or invalid geometry", level = 1, func = inspect.stack()[0][3])
        return None
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None


def convertToNative(base: Base, dataStorage) -> Union[QgsGeometry, None]:
    """Converts any given base object to QgsGeometry."""
    try:
        #print("convertToNative")
        converted = None
        conversions = [
            (Point, pointToNative),
            (Line, lineToNative),
            (Polyline, polylineToNative),
            (Curve, curveToNative),
            (Arc, arcToNative),
            (Ellipse, ellipseToNative),
            (Circle, circleToNative),
            (Mesh, meshToNative),
            (Polycurve, polycurveToNative),
            (Base, polygonToNative), # temporary solution for polygons (Speckle has no type Polygon yet)
        ]

        for conversion in conversions:
            # distinguish normal QGIS polygons and the ones sent as Mesh only
            try: 
                if isinstance(base, GisPolygonGeometry):
                    if base.boundary is None:
                        try:
                            converted: QgsMultiPolygon = meshToNative(base.displayValue, dataStorage )
                        except:
                            converted: QgsMultiPolygon = meshToNative(base['@displayValue'], dataStorage )
                        break 
                    elif isinstance(base, conversion[0]):
                        converted = conversion[1](base, dataStorage)
                        break 
                else:
                    # for older commits 
                    boundary = base.boundary # will throw exception if not polygon 
                    if boundary is None:
                        try:
                            converted: QgsMultiPolygon = meshToNative(base.displayValue, dataStorage )
                        except:
                            converted: QgsMultiPolygon = meshToNative(base['@displayValue'], dataStorage )
                        break 
                    elif boundary is not None and isinstance(base, conversion[0]):
                        converted = conversion[1](base, dataStorage)
                        break

            except: # if no "boundary" found (either old Mesh from QGIS or other object) 

                try: # check for a QGIS Mesh 
                    try:
                        # if sent as Mesh 
                        colors = base.displayValue[0].colors # will throw exception
                        if isinstance(base.displayValue[0], Mesh):
                            converted: QgsMultiPolygon = meshToNative(base.displayValue, dataStorage ) # only called for Meshes created in QGIS before
                    except:
                        # if sent as Mesh 
                        colors = base['@displayValue'][0].colors # will throw exception
                        if isinstance(base['@displayValue'][0], Mesh):
                            converted: QgsMultiPolygon = meshToNative(base['@displayValue'], dataStorage ) # only called for Meshes created in QGIS before
                
                except: # any other object
                    if isinstance(base, conversion[0]):
                        converted = conversion[1](base, dataStorage)
                        break

        return converted
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def multiPointToNative(items: List[Point], dataStorage) -> QgsMultiPoint:
    try:
        pts = QgsMultiPoint()
        for item in items:
            g = pointToNative(item, dataStorage)
            if g is not None:
                pts.addGeometry(g)
        return pts
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def multiPolylineToNative(items: List[Polyline], dataStorage) -> QgsMultiLineString:
    try:
        polys = QgsMultiLineString()
        for item in items:
            g = polylineToNative(item, dataStorage)
            if g is not None:
                polys.addGeometry(g)
        return polys
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def multiPolygonToNative(items: List[Base], dataStorage) -> QgsMultiPolygon:
    try:
        polygons = QgsMultiPolygon()
        for item in items:
            g = polygonToNative(item, dataStorage)
            if g is not None:
                polygons.addGeometry(g)
        return polygons
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def convertToNativeMulti(items: List[Base], dataStorage):
    try:
        first = items[0]
        if isinstance(first, Point):
            return multiPointToNative(items, dataStorage)
        elif isinstance(first, Line) or isinstance(first, Polyline):
            return multiPolylineToNative(items, dataStorage)
        #elif isinstance(first, Arc) or isinstance(first, Polycurve) or isinstance(first, Ellipse) or isinstance(first, Circle) or isinstance(first, Curve): 
        #    return [convertToNative(it, dataStorage) for it in items]
        elif isinstance(first, Base): 
            try:
                if first["boundary"] is not None and first["voids"] is not None:
                    return multiPolygonToNative(items, dataStorage)
            except: return None 
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None