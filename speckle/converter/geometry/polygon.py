""" This module contains all geometry conversion functionality To and From Speckle."""

from qgis.core import (
    QgsPolygon,
)
from typing import Sequence

from specklepy.objects import Base

from speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    polylineToNative,
)


def polygonToSpeckle(geom: QgsPolygon):
    """Converts a QgsPolygon to Speckle"""
    polygon = Base()
    boundary = polylineFromVerticesToSpeckle(
        geom.exteriorRing().vertices(), True
    )
    voids = []
    for i in range(geom.numInteriorRings()):
        intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True)
        voids.append(intRing)
    polygon.boundary = boundary
    polygon.voids = voids
    polygon.displayValue = [ boundary ] + voids
    return polygon


def polygonToNative(poly: Base) -> QgsPolygon:
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""

    return QgsPolygon(
        polylineToNative(poly["boundary"]),
        [polylineToNative(void) for void in poly["voids"]],
    )
