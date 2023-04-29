""" This module contains all geometry conversion functionality To and From Speckle."""

from numpy import isin
from speckle.logging import logger
from typing import List, Union

from qgis.core import (QgsGeometry, QgsWkbTypes, QgsMultiPoint, 
    QgsAbstractGeometry, QgsMultiLineString, QgsMultiPolygon,
    QgsCircularString, QgsLineString, QgsRasterLayer,QgsVectorLayer, QgsFeature,
    QgsUnitTypes)
from speckle.converter.geometry.utils import getPolygonFeatureHeight
from speckle.converter.geometry.mesh import meshToNative, writeMeshToShp
from speckle.converter.geometry.point import pointToNative, pointToSpeckle
from speckle.converter.geometry.polygon import *
from speckle.converter.geometry.polyline import *
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline, Curve, Arc, Circle, Ellipse, Polycurve


def convertToSpeckle(feature: QgsFeature, layer: QgsVectorLayer or QgsRasterLayer, dataStorage = None) -> Union[Base, Sequence[Base], None]:
    """Converts the provided layer feature to Speckle objects"""
    try: 
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
                return result
            else:
                result = [pointToSpeckle(pt, feature, layer, dataStorage) for pt in geom.parts()]
                for r in result: r.units = units 
                return result
        
        elif geomType == QgsWkbTypes.LineGeometry: # 1
            if geomSingleType:
                result = anyLineToSpeckle(geom, feature, layer, dataStorage)
                result = addCorrectUnits(result, dataStorage)
                return result
            else: 
                result = [anyLineToSpeckle(poly, feature, layer, dataStorage) for poly in geom.parts()]
                for r in result: r = addCorrectUnits(r, dataStorage)
                if len(result) == 1: result = result[0] 
                return result

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
            result.units = units
            for v in result['displayValue']: v.units = units
            return result
        elif geomType == QgsWkbTypes.PolygonGeometry: # 2
            height = getPolygonFeatureHeight(feature, layer, dataStorage)
            if geomSingleType:
                result = polygonToSpeckle(geom, feature, layer, height, dataStorage)
                result.units = units
                result.boundary.units = units
                for v in result.voids: v.units = units
                for v in result['displayValue']: v.units = units
                return result
            else:
                result = [polygonToSpeckle(poly, feature, layer, height, dataStorage) for poly in geom.parts()]
                for r in result: 
                    r.units = units 
                    r.boundary.units = units
                    for v in r.voids: v.units = units 
                    for v in r['displayValue']: v.units = units
                return result
        else:
            logToUser("Unsupported or invalid geometry", level = 1, func = inspect.stack()[0][3])
        return None
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None


def convertToNative(base: Base, dataStorage = None) -> Union[QgsGeometry, None]:
    """Converts any given base object to QgsGeometry."""
    try:
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
                # if normal polygon
                boundary = base.boundary # will throw exception
                if boundary is not None and isinstance(base, conversion[0]):
                    converted = conversion[1](base, dataStorage)
                    break
            except:
                try:
                    # if sent as Mesh 
                    colors = base.displayValue[0].colors # will throw exception
                    if isinstance(base.displayValue[0], Mesh):
                        converted: QgsMultiPolygon = meshToNative(base.displayValue, dataStorage ) # only called for Meshes created in QGIS before
                except:
                    # if other geometry 
                    if isinstance(base, conversion[0]):
                        #print(conversion[0])
                        converted = conversion[1](base, dataStorage)
                        break

        return converted
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def multiPointToNative(items: List[Point], dataStorage = None) -> QgsMultiPoint:
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

def multiPolylineToNative(items: List[Polyline], dataStorage = None) -> QgsMultiLineString:
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

def multiPolygonToNative(items: List[Base], dataStorage = None) -> QgsMultiPolygon:
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

def convertToNativeMulti(items: List[Base], dataStorage = None):
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