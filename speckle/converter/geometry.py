from qgis.core import (QgsGeometry, QgsLineString, QgsMultiLineString,
                       QgsMultiPoint, QgsMultiPolygon, QgsPoint, QgsPointXY, QgsPolygon,
                       QgsWkbTypes)
from specklepy.objects.geometry import Point, Polyline

from .logging import log
import math

def extractGeometry(feature):
    geom = feature.geometry()
    geomSingleType = QgsWkbTypes.isSingleType(geom.wkbType())
    geom_type = geom.type()

    if geom_type == QgsWkbTypes.PointGeometry:
        # the geometry type can be of single or multi type
        if geomSingleType:
            log("Point")
            return pointToSpeckle(geom.constGet())
        else:
            log("Multipoint")
            return [pointToSpeckle(pt) for pt in geom.parts()]
    elif geom_type == QgsWkbTypes.LineGeometry:
        if geomSingleType:
            log("Converting polyline")
            return pointToSpeckle(geom.parts()[0])
        else:
            log("Converting multipolyline")
            return [polylineToSpeckle(poly) for poly in geom.parts()]
    elif geom_type == QgsWkbTypes.PolygonGeometry:
        if geomSingleType:
            log("Polygon")
            return polygonToSpeckle(geom.parts()[0])
        else:
            log("Multipolygon")
            return [polygonToSpeckle(p) for p in geom.parts()]
    else:
        print("Unknown or invalid geometry")
    return None

def pointToSpeckle(pt: QgsPoint or QgsPointXY):
    if isinstance(pt,QgsPointXY):
        pt = QgsPoint(pt)
    # when unset, z() returns "nan"
    z = 0 if math.isnan(pt.z()) else pt.z()
    return Point(pt.x(),pt.y(),z )

def polylineFromVertices(vertices, closed):
    specklePts = [pointToSpeckle(pt) for pt in vertices]
    #TODO: Replace with `from_points` function when fix is pushed.
    polyline = Polyline()
    polyline.value = []
    polyline.closed = closed
    polyline.units = specklePts[0].units
    for point in specklePts:
        polyline.value.extend([point.x, point.y, point.z])
    return polyline

def polylineToSpeckle(poly: QgsLineString):
    return polylineFromVertices(poly.vertices(),False)


def polygonToSpeckle(geom: QgsPolygon):
    return polylineFromVertices(geom.vertices(),True)
