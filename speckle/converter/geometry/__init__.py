""" This module contains all geometry conversion functionality To and From Speckle."""

from speckle.logging import logger
from typing import List, Union

from qgis.core import QgsGeometry, QgsWkbTypes
from speckle.converter.geometry.mesh import meshToNative
from speckle.converter.geometry.point import pointToNative, pointToSpeckle
from speckle.converter.geometry.polygon import *
from speckle.converter.geometry.polyline import (
    lineToNative,
    polylineToNative,
    polylineToSpeckle,
)
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline


def convertToSpeckle(feature) -> Union[Base, List[Base], None]:
    """Converts the provided layer feature to Speckle objects"""

    geom: QgsGeometry = feature.geometry()
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
        logger.log("Unsupported or invalid geometry")
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
