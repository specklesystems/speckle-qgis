from qgis.core import (QgsGeometry, QgsLineString, QgsMultiLineString,
                       QgsMultiPoint, QgsMultiPolygon, QgsPoint, QgsPointXY, QgsPolygon,
                       QgsWkbTypes)
from specklepy.objects.geometry import Point, Polyline
import math
from specklepy.objects import Base

def extractGeometry(feature):
    geom = feature.geometry()
    geomSingleType = QgsWkbTypes.isSingleType(geom.wkbType())
    geom_type = geom.type()

    if geom_type == QgsWkbTypes.PointGeometry:
        # the geometry type can be of single or multi type
        if geomSingleType:
            return pointToSpeckle(geom.constGet())
        else:
            return [pointToSpeckle(pt) for pt in geom.parts()]
    elif geom_type == QgsWkbTypes.LineGeometry:
        if geomSingleType:
            return polylineToSpeckle(geom)
        else:
            return [polylineToSpeckle(poly) for poly in geom.parts()]
    elif geom_type == QgsWkbTypes.PolygonGeometry:
        if geomSingleType:
            return polygonToSpeckle(geom)
        else:
            return [polygonToSpeckle(p) for p in geom.parts()]
    else:
        print("Unsupported or invalid geometry")
    return None

def pointToSpeckle(pt: QgsPoint or QgsPointXY):
    if isinstance(pt,QgsPointXY):
        pt = QgsPoint(pt)
    # when unset, z() returns "nan"
    x = pt.x()
    y = pt.y()
    z = 0 if math.isnan(pt.z()) else pt.z()
    specklePoint = Point()
    specklePoint.x = x
    specklePoint.y = y
    specklePoint.z = z
    return specklePoint
    
def polylineFromVertices(vertices, closed):
    specklePts = [pointToSpeckle(pt) for pt in vertices]
    #TODO: Replace with `from_points` function when fix is pushed.
    polyline = Polyline()
    polyline.value = []
    polyline.closed = closed
    polyline.units = specklePts[0].units
    for i in range(len(specklePts)):
        if closed and i == len(specklePts) - 1:
            continue
        point = specklePts[i]
        polyline.value.extend([point.x, point.y, point.z])
    return polyline

def polylineToSpeckle(poly: QgsLineString):
    return polylineFromVertices(poly.vertices(),False)


def polygonToSpeckle(geom: QgsPolygon):
    spklPolygon = Base()
    spklPolygon.boundary = polylineFromVertices(geom.exteriorRing().vertices(),True)
    voids = []
    for i in range(geom.numInteriorRings()):
        intRing = polylineFromVertices(geom.interiorRing(i).vertices(),True)
        voids.append(intRing)
    spklPolygon.voids = voids
    return spklPolygon
