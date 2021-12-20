""" This module contains all geometry conversion functionality To and From Speckle."""

import math
from typing import List, Union

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsLineString,
    QgsPoint,
    QgsPointXY,
    QgsPolygon,
    QgsProject,  QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsWkbTypes,
)
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline


def convertToSpeckle(feature) -> Union[Base, List[Base], None]:
    try:
        geom = feature.geometry()
    except AttributeError:
        geom = feature
    geomSingleType = QgsWkbTypes.isSingleType(geom.wkbType())
    geomType = geom.type()

    if geomType == QgsWkbTypes.PointGeometry:
        # the geometry type can be of single or multi type
        if geomSingleType:
            return pointToSpeckle(geom.constGet())
        else:
            return [pointToSpeckle(pt) for pt in geom.parts()]
    elif geomType == QgsWkbTypes.LineGeometry:
        if geomSingleType:
            return polylineToSpeckle(geom)
        else:
            return [polylineToSpeckle(poly) for poly in geom.parts()]
    elif geomType == QgsWkbTypes.PolygonGeometry:
        if geomSingleType:
            return polygonToSpeckle(geom)
        else:
            return [polygonToSpeckle(p) for p in geom.parts()]
    else:
        print("Unsupported or invalid geometry")
    return None


def convertToNative(base: Base) -> Union[QgsGeometry, None]:
    """Converts any given base object to QgsGeometry."""
    converted = None
    conversions = [
        (Point, pointToNative),
        (Line, lineToNative),
        (Polyline, polylineToNative),
        (Mesh, meshToNative),
    ]

    for conversion in conversions:
        if isinstance(base, conversion[0]):
            converted = conversion[1](base)
            break

    return converted


def pointToSpeckle(pt: QgsPoint or QgsPointXY):
    """Converts a QgsPoint to Speckle"""
    if isinstance(pt, QgsPointXY):
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


def pointToNative(pt: Point) -> QgsPoint:
    """Converts a Speckle Point to QgsPoint"""
    return QgsPoint(pt.x, pt.y, pt.z)


def lineToNative(line: Line) -> QgsLineString:
    """Converts a Speckle Line to QgsLineString"""

    return QgsLineString(pointToNative(line.start), pointToNative(line.end))


def polylineToNative(poly: Polyline) -> QgsLineString:
    """Converts a Speckle Polyline to QgsLineString"""

    return QgsLineString([pointToNative(pt) for pt in poly.as_points()])


def polygonToNative(poly: Base) -> QgsPolygon:
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""

    return QgsPolygon(
        polylineToNative(poly["boundary"]),
        [polylineToNative(void) for void in poly["voids"]],
    )


def meshToNative(mesh: Mesh):
    """Converts a Speckle Mesh to QgsGeometry. Currently UNSUPPORTED"""
    return None


def polylineFromVerticesToSpeckle(vertices, closed):
    """Returns a Speckle Polyline given a list of QgsPoint instances and a boolean indicating if it's closed or not."""
    specklePts = [pointToSpeckle(pt) for pt in vertices]
    # TODO: Replace with `from_points` function when fix is pushed.
    polyline = Polyline()
    polyline.value = []
    polyline.closed = closed
    polyline.units = specklePts[0].units
    for i, point in enumerate(specklePts):
        if closed and i == len(specklePts) - 1:
            continue
        polyline.value.extend([point.x, point.y, point.z])
    return polyline


def polylineToSpeckle(poly: QgsLineString):
    """Converts a QgsLineString to Speckle"""
    return polylineFromVerticesToSpeckle(poly.vertices(), False)


def polygonToSpeckle(geom: QgsPolygon):
    """Converts a QgsPolygon to Speckle"""
    polygon = Base()
    polygon.boundary = polylineFromVerticesToSpeckle(
        geom.exteriorRing().vertices(), True
    )
    voids = []
    for i in range(geom.numInteriorRings()):
        intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True)
        voids.append(intRing)
    polygon.voids = voids
    return polygon


def transform(
    src: QgsPointXY,
    crsSrc: QgsCoordinateReferenceSystem,
    crsDest: QgsCoordinateReferenceSystem,
):
    """Transforms a QgsPointXY from the source CRS to the destination."""

    transformContext = QgsProject.instance().transformContext()
    xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

    # forward transformation: src -> dest
    dest = xform.transform(src)
    return dest


def reverseTransform(
    dest: QgsPointXY,
    crsSrc: QgsCoordinateReferenceSystem,
    crsDest: QgsCoordinateReferenceSystem,
):
    """Transforms a QgsPointXY from the destination CRS to the source."""

    transformContext = QgsProject.instance().transformContext()
    xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

    # inverse transformation: dest -> src
    src = xform.transform(dest, QgsCoordinateTransform.ReverseTransform)
    return src

def rasterToMesh(vertices, faces, colors):
    mesh = Mesh()
    mesh.vertices = vertices
    mesh.faces = faces
    mesh.colors = colors
    return mesh