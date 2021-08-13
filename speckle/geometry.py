from qgis.core import QgsPointXY, QgsMultiPolygon, QgsWkbTypes, QgsMultiPoint, QgsPolygon, QgsLineString, QgsMultiLineString, QgsGeometry

from specklepy.objects.geometry import Point, Polyline
from .logging import log

def extractGeometry(feature):
    geom = feature.geometry()
    geomSingleType = QgsWkbTypes.isSingleType(geom.wkbType())
    geom_type = geom.type()

    if geom_type == QgsWkbTypes.PointGeometry:
        # the geometry type can be of single or multi type
        if geomSingleType:
            log("Point")
            return pointToSpeckle(geom.asPoint())
        else:
            log("Multipoint")
            return [pointToSpeckle(pt) for pt in geom.asMultiPoint()]
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

def pointToSpeckle(pt: QgsPointXY):
    return Point(pt.x(),pt.y())

def polylineToSpeckle(poly: QgsLineString):
    specklePts = [pointToSpeckle(pt) for pt in poly.vertices()]
    #TODO: Replace with `from_points` function when fix is pushed.
    polyline = Polyline()
    polyline.value = []
    polyline.closed = False
    polyline.units = specklePts[0].units
    for point in specklePts:
        polyline.value.extend([point.x, point.y, point.z])
    return polyline

def polygonToSpeckle(geom: QgsPolygon):
    vertices = geom.vertices()
    poly = polylineToSpeckle(vertices)
    poly.closed = True
    return poly