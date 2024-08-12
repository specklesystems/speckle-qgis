from speckle.converter.geometry.mesh import (
    meshPartsFromPolygon,
    meshToNative,
)
from typing import Tuple
import pathlib

import shapefile
from specklepy.objects.geometry import Mesh

try:
    from qgis.core import (
        QgsFeature,
        QgsVectorLayer,
        QgsMultiPolygon,
    )
except ModuleNotFoundError:
    pass


def test_meshPartsFromPolygon(polygon, data_storage):
    polyBorder = polygon.boundary.as_points()
    voidsAsPts = []
    existing_vert = 0
    feature = QgsFeature()

    geomType = "Polygon"
    layer = QgsVectorLayer(geomType + "?crs=" + "WGS84", "", "memory")
    height = None
    result = meshPartsFromPolygon(
        polyBorder,
        voidsAsPts,
        existing_vert,
        feature,
        polygon,
        layer,
        height,
        data_storage,
    )
    assert isinstance(result, Tuple)
    assert len(result) == 5
    assert isinstance(result[0], int)
    assert isinstance(result[1], list)
    assert isinstance(result[2], list)
    assert isinstance(result[3], list)
    assert isinstance(result[4], int)


def test_meshToNative(mesh, data_storage):
    result = meshToNative([mesh], data_storage)
    assert isinstance(result, QgsMultiPolygon)
